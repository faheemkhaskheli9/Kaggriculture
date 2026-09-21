"""Low-noise paired A/B runner (scratch, not repo tooling).

Every arm plays the identical (opponent, seed, seat) tuple. The stock engine draws
the town shop from the same per-day RNG stream it uses for weed spawning, so any
policy change that alters empty-tile counts also changes the shop sequence and the
"pair" is not a pair. Here the shop draw gets its own per-day RNG (same uniform
distribution), so both arms see the same shops.

usage: python experiments/paired_lownoise.py OUT.csv N_PAIRS PICK_SEED WORKERS LEAGUE.json BASELINE ARM [ARM...]
"""
import sys, os, io, json, random, time, contextlib, csv, statistics as st
import multiprocessing as mp

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = r"E:\Competitions\Kaggriculture"
CONFIG = {"episodeSteps": 720, "actTimeout": 1, "runTimeout": 1200, "startingMoney": 3000,
          "turnsPerDay": 24, "maxMarketOrdersPerTurn": 10}
_make = None


def _init():
    global _make
    os.chdir(ROOT)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        import kaggle_environments.envs.kaggriculture.kaggriculture as km
    import random as _r

    def _end_of_day(state, env, day):
        obs0 = state[0].observation
        cfg = env.configuration
        board_size = int(km.get(cfg, "boardSize", 10))
        tpd = max(1, int(km.get(cfg, "turnsPerDay", 24)))
        weed_chance = float(km.get(cfg, "weedSpawnChance", 0.005))
        shed_cap = int(km.get(cfg, "shedCapacity", 100))
        shop_interval = max(1, int(km.get(cfg, "townShopUnlockInterval", 3)))
        seed = env.info.get("seed", 0)
        rng = _r.Random((seed * 1_000_003) ^ day)
        shop_rng = _r.Random(((seed * 1_000_003) ^ day) + 0x5A17C0DE)
        for player_id, farm in enumerate(obs0.farms):
            private = state[player_id].observation.private
            km._daily_refresh_plants(farm, day, tpd)
            km._daily_refresh_animals(farm, day)
            km._spawn_weeds(farm, board_size, weed_chance, rng)
            km._drop_inventories_to_shed(private, shed_cap)
            farm["farmer"] = list(km._default_spawn(board_size))
            farm["hands"] = []
            farm["hires_today"] = 0
            private["inventories"] = [{}]
        next_day = day + 1
        town = obs0.town
        if next_day > 0 and next_day % shop_interval == 0:
            if len(town["unlocked_shops"]) < km.MAX_SHOP_INSTANCES:
                town["unlocked_shops"].append(shop_rng.choice(sorted(km.SHOPS)))

    km._end_of_day = _end_of_day
    _make = make


def _play(job):
    arm, opp, seed, seat, pair_id = job
    line = [None, None]
    line[seat] = arm
    line[1 - seat] = opp
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            env = _make("kaggriculture", configuration=dict(CONFIG, seed=seed), debug=False)
            env.run(line)
        final = env.steps[-1]
        money = [float(final[i].observation.farms[i].money) if hasattr(final[i].observation, "farms")
                 else float(final[0].observation.farms[i].money) for i in (0, 1)]
        bad = int(any(str(s.status) != "DONE" for s in final))
        tb = 0
        for step_logs in (env.logs or []):
            for k, lg in enumerate(step_logs or []):
                if k == seat and isinstance(lg, dict) and "Traceback" in (lg.get("stderr") or ""):
                    tb += 1
        return (pair_id, arm, opp, seed, seat, money[seat], money[1 - seat], bad, tb, time.time() - t0)
    except Exception as exc:  # harness crash
        return (pair_id, arm, opp, seed, seat, float("nan"), float("nan"), 1, -1, time.time() - t0)


def main():
    out, n_pairs, pick_seed, workers, league, baseline = sys.argv[1:7]
    arms = [baseline] + sys.argv[7:]
    n_pairs, pick_seed, workers = int(n_pairs), int(pick_seed), int(workers)
    lg = json.load(open(league, encoding="utf-8"))
    opps = [(os.path.join(ROOT, e["path"]), float(e.get("weight", 1))) for e in lg["opponents"]]
    rng = random.Random(pick_seed)
    jobs = []
    for pid in range(n_pairs):
        opp = rng.choices([o for o, _ in opps], weights=[w for _, w in opps])[0]
        seed = rng.randint(100000000, 999999999)
        seat = rng.randint(0, 1)
        for arm in arms:
            jobs.append((os.path.join(ROOT, arm), opp, seed, seat, pid))
    rows = []
    reuse = os.environ.get("REUSE")
    if reuse and os.path.exists(reuse):
        have = {}
        for r in csv.DictReader(open(reuse)):
            have[(r["arm"], int(r["pair"]), int(r["seed"]), int(r["seat"]), r["opp"])] = r
        keep = []
        for j in jobs:
            k = (os.path.basename(j[0]), j[4], j[2], j[3], os.path.basename(j[1]))
            if k in have:
                r = have[k]
                rows.append((j[4], j[0], j[1], j[2], j[3], float(r["ours"]), float(r["theirs"]), int(r["bad"]), int(r["tracebacks"]), 0.0))
            else:
                keep.append(j)
        print(f"  reused {len(jobs)-len(keep)} games from {os.path.basename(reuse)}", flush=True)
        jobs = keep
    t0 = time.time()
    with mp.Pool(workers, initializer=_init) as pool:
        for i, r in enumerate(pool.imap_unordered(_play, jobs), 1):
            rows.append(r)
            if i % 20 == 0:
                print(f"  {i}/{len(jobs)} games  {time.time()-t0:.0f}s", flush=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair", "arm", "opp", "seed", "seat", "ours", "theirs", "bad", "tracebacks", "secs"])
        for r in sorted(rows):
            w.writerow([r[0], os.path.basename(r[1]), os.path.basename(r[2])] + list(r[3:]))
    report(out, os.path.basename(baseline))


def report(path, baseline):
    rows = list(csv.DictReader(open(path)))
    by = {}
    for r in rows:
        by.setdefault(r["arm"], {})[int(r["pair"])] = r
    base = by[baseline]

    def ci(v):
        rr = random.Random(7)
        n = len(v)
        ms = sorted(st.mean(rr.choices(v, k=n)) for _ in range(3000))
        return ms[75], ms[2924]

    for arm, games in by.items():
        bad = sum(int(g["bad"]) for g in games.values())
        tb = sum(max(0, int(g["tracebacks"])) for g in games.values())
        wins = sum(float(g["ours"]) > float(g["theirs"]) for g in games.values())
        print(f"\n== {arm}: n={len(games)} mean_own={st.mean(float(g['ours']) for g in games.values()):.0f} "
              f"wins={wins} bad_status={bad} traceback_steps={tb}")
        if arm == baseline:
            continue
        d, per = [], {}
        for pid, g in games.items():
            if pid not in base:
                continue
            b = base[pid]
            dv = float(g["ours"]) - float(b["ours"])
            if dv != dv:
                continue
            d.append(dv)
            per.setdefault(g["opp"], []).append((dv, float(b["ours"]),
                                                 (float(g["ours"]) > float(g["theirs"])) - (float(b["ours"]) > float(b["theirs"]))))
        lo, hi = ci(d)
        print(f"   own-money delta vs {baseline}: mean={st.mean(d):+.0f} median={st.median(d):+.0f} "
              f"CI95[{lo:+.0f},{hi:+.0f}] up={sum(x > 0 for x in d)}/{len(d)} sd={st.pstdev(d):.0f}")
        for opp, v in sorted(per.items(), key=lambda kv: -len(kv[1])):
            print(f"     vs {opp:32} n={len(v):3} d_mean={st.mean(x[0] for x in v):+8.0f} "
                  f"d_med={st.median(x[0] for x in v):+8.0f} base_own={st.mean(x[1] for x in v):8.0f} "
                  f"win_delta={sum(x[2] for x in v):+d}")


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2], sys.argv[3])
    else:
        main()
