"""Local-competition result / replay / log analysis pipeline.

Consumes the `compete_runs/<stamp>/` archives written by `compete.py`
(`manifest.json` + one `*.replay.json.gz` + one `*.logs.json` per game) and
produces the same shape of report `tools/ladder_analyze.py` gives for real
ladder episodes: overall W/T/L + score-rate, per-opponent and per-archetype
breakdowns, movement / plant / weed / animal / sell diagnostics, surfaced agent
exceptions, and a worst-games loss diagnosis with the day the coin lead flips.

Low-memory: one replay is opened, reduced to scalars, and freed before the next.

Usage
-----
    python tools/analyze_runs.py                     # newest compete_runs/ dir
    python tools/analyze_runs.py 20260904-045341-475450
    python tools/analyze_runs.py --last 3            # merge the 3 newest runs
    python tools/analyze_runs.py path/to/run --json summary.json
    python tools/analyze_runs.py --last 2 --worst 20 --full
    python tools/analyze_runs.py --compare A B       # per-opponent W/T/L diff

The archetype classifier is shared with `ladder_analyze` semantics so a local
`bot_animalfactory_v2` game and a real `animal_factory` ladder game land in the
same bucket.
"""
import argparse
import collections
import csv
import gzip
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "compete_runs"
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
DAY_MARKS = (5, 10, 15, 20, 25, 29)


# --------------------------------------------------------------------------- #
# replay reduction  (kept behaviourally identical to tools/ladder_analyze.py)
# --------------------------------------------------------------------------- #
def farm(steps, i, seat):
    try:
        return steps[i][0]["observation"]["farms"][seat]
    except Exception:
        return None


def traj(steps, seat):
    out = {}
    for d in range(30):
        i = min(d * 24, len(steps) - 1)
        fm = farm(steps, i, seat)
        if not fm:
            continue
        plants = collections.Counter()
        weeds = animals = 0
        for rr in fm.get("tiles", []):
            for t in rr:
                if isinstance(t, dict):
                    k = t.get("kind")
                    if k == "PLANT":
                        plants[t.get("crop")] += 1
                    elif k == "WEED":
                        weeds += 1
                    if t.get("animal"):
                        animals += 1
        out[d] = dict(money=fm.get("money", 0), plants=sum(plants.values()),
                      weeds=weeds, animals=animals,
                      quads=len(fm.get("unlocked_quadrants", [])),
                      mix=dict(plants))
    return out


def tally(steps, seat):
    mv = nonpass = hires = 0
    sells = collections.Counter()
    acts = collections.Counter()
    for per in steps:
        if seat >= len(per):
            continue
        a = per[seat].get("action") or {}
        units = []
        fa = a.get("farmer")
        if isinstance(fa, list) and fa:
            units.append(fa[0])
        for h in a.get("hands") or []:
            if isinstance(h, list) and h:
                units.append(h[0])
        for u in units:
            if u == "PASS":
                continue
            nonpass += 1
            acts[u] += 1
            if u in MOVES:
                mv += 1
        for o in a.get("market") or []:
            if isinstance(o, list) and o:
                if o[0] == "SELL" and len(o) >= 3:
                    try:
                        sells[o[1]] += int(o[2])
                    except Exception:
                        pass
                if o[0] == "HIRE":
                    hires += 1
    return dict(move_pct=(mv / nonpass if nonpass else 0.0), sells=dict(sells),
                acts=dict(acts.most_common(6)), nonpass=nonpass, hires=hires)


def classify_opp(ot, oa):
    amax = max((ot.get(d, {}).get("animals", 0) for d in range(30)), default=0)
    pmax = max((ot.get(d, {}).get("plants", 0) for d in range(30)), default=0)
    s = oa["sells"]
    tot = sum(s.values()) or 1
    wheat_f = s.get("WHEAT", 0) / tot
    mix29 = ot.get(29, {}).get("mix", {})
    if amax >= 4 and (s.get("FERTILIZER", 0) + s.get("MILK", 0)
                      + s.get("WOOL", 0)) / tot > 0.3:
        return "animal_factory"
    if wheat_f > 0.6 and pmax > 25:
        return "wheat_flood"
    if mix29.get("MELON", 0) >= 8:
        return "melon_mono"
    if (mix29.get("STRAWBERRY", 0) + mix29.get("TOMATO", 0)) >= 8 \
            and pmax < 25 and oa["nonpass"] < 3000:
        return "premium"
    if pmax <= 5 and amax == 0:
        return "passive"
    if oa["nonpass"] < 500:
        return "passive"
    return "other"


def lead_flip_day(mt, ot):
    """First day mark at which our money stops being >= opp money (else None)."""
    ahead = None
    for d in range(30):
        me = mt.get(d, {}).get("money")
        op = ot.get(d, {}).get("money")
        if me is None or op is None:
            continue
        if me >= op:
            ahead = d
        elif ahead is not None:
            return d
    return None


def scan_logs(path):
    """Return (n_steps_with_stderr, first_stderr_snippet)."""
    try:
        lg = json.load(open(path, encoding="utf-8"))
    except Exception:
        return 0, ""
    n, first = 0, ""
    for entry in lg or []:
        if not entry:
            continue
        for side in entry:
            err = (side or {}).get("stderr") if isinstance(side, dict) else None
            if err and err.strip():
                n += 1
                if not first:
                    first = err.strip().replace("\n", " ")[:240]
    return n, first


# --------------------------------------------------------------------------- #
# run loading
# --------------------------------------------------------------------------- #
def resolve_run(token):
    p = Path(token)
    if p.is_dir():
        return p
    cand = RUNS_DIR / token
    if cand.is_dir():
        return cand
    sys.exit(f"run dir not found: {token}")


def newest_runs(n):
    if not RUNS_DIR.is_dir():
        sys.exit(f"no {RUNS_DIR}")
    dirs = sorted((d for d in RUNS_DIR.iterdir()
                   if d.is_dir() and (d / "manifest.json").exists()),
                  key=lambda d: d.name)
    if not dirs:
        sys.exit(f"no runs with manifest.json under {RUNS_DIR}")
    return dirs[-n:]


def load_games(run_dir):
    manifest = json.load(open(run_dir / "manifest.json", encoding="utf-8"))
    out = []
    for g in manifest["games"]:
        rp = g.get("replay")
        if rp and not Path(rp).exists():  # archive moved: fall back to basename
            rp = str(run_dir / Path(rp).name)
        lp = g.get("logs")
        if lp and not Path(lp).exists():
            lp = str(run_dir / Path(lp).name)
        rec = dict(run=run_dir.name, agent=manifest.get("agent"),
                   opponent=g["opponent"], seed=g["seed"], seat=g["our_seat"],
                   result=g["result"], margin=g["margin"],
                   our_money=g["our_money"], opp_money=g["opp_money"],
                   errored=g.get("errored", False), seconds=g.get("seconds"))
        if rp and Path(rp).exists():
            try:
                opener = gzip.open if rp.endswith(".gz") else open
                r = json.load(opener(rp, "rt", encoding="utf-8"))
                steps = r["steps"]
                me, opp = g["our_seat"], 1 - g["our_seat"]
                mt, ot = traj(steps, me), traj(steps, opp)
                ma, oa = tally(steps, me), tally(steps, opp)
                rec.update(
                    arch=classify_opp(ot, oa),
                    move_pct=ma["move_pct"], hires=ma["hires"],
                    nonpass=ma["nonpass"], my_sells=ma["sells"],
                    opp_sells=oa["sells"],
                    my_money_d=[int(mt.get(x, {}).get("money", 0)) for x in DAY_MARKS],
                    op_money_d=[int(ot.get(x, {}).get("money", 0)) for x in DAY_MARKS],
                    my_plants_d=[mt.get(x, {}).get("plants", 0) for x in DAY_MARKS],
                    weeds29=mt.get(29, {}).get("weeds", 0),
                    my_anim=max((mt.get(x, {}).get("animals", 0) for x in range(30)), default=0),
                    op_anim=max((ot.get(x, {}).get("animals", 0) for x in range(30)), default=0),
                    quads29=mt.get(29, {}).get("quads", 0),
                    mix29=mt.get(29, {}).get("mix", {}),
                    flip_day=lead_flip_day(mt, ot),
                )
                del r, steps
            except Exception as e:
                rec["replay_error"] = str(e)
        if lp and Path(lp).exists():
            n_err, snippet = scan_logs(lp)
            if n_err:
                rec["stderr_steps"] = n_err
                rec["stderr_first"] = snippet
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def _wtl(rows):
    w = sum(r["result"] == "WIN" for r in rows)
    t = sum(r["result"] == "TIE" for r in rows)
    loss = sum(r["result"] == "LOSS" for r in rows)
    return w, t, loss


def _rate(rows):
    w, t, _ = _wtl(rows)
    return (w + 0.5 * t) / len(rows) if rows else 0.0


def _pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = max(0, min(len(xs) - 1, int(q * (len(xs) - 1))))
    return xs[k]


def summary(games):
    have_replay = [g for g in games if "move_pct" in g]
    overall = dict(
        n=len(games), **dict(zip(("W", "T", "L"), _wtl(games))),
        score_rate=_rate(games),
        errors=sum(g.get("errored") or bool(g.get("stderr_steps")) for g in games),
        our_coins_mean=statistics.fmean(g["our_money"] for g in games) if games else 0,
        our_coins_median=statistics.median(g["our_money"] for g in games) if games else 0,
        our_coins_p10=_pct([g["our_money"] for g in games], 0.10),
        our_coins_min=min((g["our_money"] for g in games), default=0),
        margin_mean=statistics.fmean(g["margin"] for g in games) if games else 0,
        margin_median=statistics.median(g["margin"] for g in games) if games else 0,
        margin_min=min((g["margin"] for g in games), default=0),
    )
    by_opp = {}
    for opp in sorted({g["opponent"] for g in games}):
        rs = [g for g in games if g["opponent"] == opp]
        w, t, loss = _wtl(rs)
        by_opp[opp] = dict(
            W=w, T=t, L=loss, n=len(rs), score_rate=_rate(rs),
            margin_mean=statistics.fmean(r["margin"] for r in rs),
            our_coins_mean=statistics.fmean(r["our_money"] for r in rs),
            move_pct=statistics.fmean(r["move_pct"] for r in rs
                                      if "move_pct" in r) if any("move_pct" in r for r in rs) else None,
        )
    by_arch = {}
    for arch in sorted({g.get("arch", "?") for g in have_replay}):
        rs = [g for g in have_replay if g.get("arch") == arch]
        w, t, loss = _wtl(rs)
        by_arch[arch] = dict(
            W=w, T=t, L=loss, n=len(rs), score_rate=_rate(rs),
            margin_mean=statistics.fmean(r["margin"] for r in rs),
            median_flip_day=statistics.median(
                [r["flip_day"] for r in rs if r.get("flip_day") is not None] or [-1]),
        )
    diag = {}
    if have_replay:
        diag = dict(
            move_pct=statistics.fmean(g["move_pct"] for g in have_replay),
            plants_d10=statistics.fmean(g["my_plants_d"][1] for g in have_replay),
            plants_d20=statistics.fmean(g["my_plants_d"][3] for g in have_replay),
            plants_d29=statistics.fmean(g["my_plants_d"][5] for g in have_replay),
            weeds29=statistics.fmean(g["weeds29"] for g in have_replay),
            animals=statistics.fmean(g["my_anim"] for g in have_replay),
            quads29=statistics.fmean(g["quads29"] for g in have_replay),
            hires=statistics.fmean(g["hires"] for g in have_replay),
            nonpass=statistics.fmean(g["nonpass"] for g in have_replay),
        )
    sells = collections.Counter()
    for g in have_replay:
        sells.update(g.get("my_sells", {}))
    return overall, by_opp, by_arch, diag, dict(sells.most_common())


def print_report(games, worst_n, full):
    overall, by_opp, by_arch, diag, sells = summary(games)
    runs = sorted({g["run"] for g in games})
    agents = sorted({g.get("agent") for g in games})
    print("=" * 100)
    print(f"runs   : {', '.join(runs)}")
    print(f"agent  : {', '.join(a for a in agents if a)}")
    o = overall
    print(f"games  : {o['n']}   W/T/L = {o['W']}/{o['T']}/{o['L']}   "
          f"score-rate {o['score_rate']:.1%}   errors {o['errors']}")
    print(f"our coins  mean/median/p10/min = {o['our_coins_mean']:.0f} / "
          f"{o['our_coins_median']:.0f} / {o['our_coins_p10']:.0f} / {o['our_coins_min']:.0f}")
    print(f"margin     mean/median/min     = {o['margin_mean']:+.0f} / "
          f"{o['margin_median']:+.0f} / {o['margin_min']:+.0f}")
    if diag:
        print(f"diag       move% {diag['move_pct']:.0%}  "
              f"plants d10/20/29 {diag['plants_d10']:.0f}/{diag['plants_d20']:.0f}/"
              f"{diag['plants_d29']:.0f}  weeds29 {diag['weeds29']:.0f}  "
              f"animals {diag['animals']:.1f}  quads29 {diag['quads29']:.1f}  "
              f"hires {diag['hires']:.0f}  nonpass {diag['nonpass']:.0f}")
    print(f"sells      {sells}")

    print("\n--- by opponent (score-rate asc) ---")
    for opp, s in sorted(by_opp.items(), key=lambda kv: kv[1]["score_rate"]):
        mv = f" move%={s['move_pct']:.0%}" if s["move_pct"] is not None else ""
        print(f"  {opp:<22} {s['W']:>2}/{s['T']}/{s['L']:<2} n={s['n']:<3} "
              f"rate={s['score_rate']:>5.0%}  margin_mean={s['margin_mean']:>+9.0f}  "
              f"coins_mean={s['our_coins_mean']:>8.0f}{mv}")

    print("\n--- by archetype (score-rate asc) ---")
    for arch, s in sorted(by_arch.items(), key=lambda kv: kv[1]["score_rate"]):
        fd = s["median_flip_day"]
        fd_s = f"  median lead-flip day={fd:.0f}" if fd and fd >= 0 else ""
        print(f"  {arch:<16} {s['W']:>2}/{s['T']}/{s['L']:<2} n={s['n']:<3} "
              f"rate={s['score_rate']:>5.0%}  margin_mean={s['margin_mean']:>+9.0f}{fd_s}")

    errs = [g for g in games if g.get("errored") or g.get("stderr_steps") or g.get("replay_error")]
    if errs:
        print(f"\n--- errors / exceptions ({len(errs)}) ---")
        for g in errs:
            tag = f"{g['opponent']} seed={g['seed']} seat=P{g['seat']}"
            if g.get("stderr_steps"):
                print(f"  {tag}: stderr on {g['stderr_steps']} steps :: {g.get('stderr_first','')}")
            if g.get("replay_error"):
                print(f"  {tag}: replay parse error :: {g['replay_error']}")
            if g.get("errored") and not g.get("stderr_steps"):
                print(f"  {tag}: non-DONE status")

    ranked = sorted((g for g in games if "move_pct" in g), key=lambda g: g["margin"])
    show = ranked if full else ranked[:worst_n]
    if show:
        print(f"\n--- {'all games' if full else f'worst {len(show)}'} (margin asc) ---")
        for g in show:
            print(f"  {g['result']:<4} [{g.get('arch','?'):14}] {g['opponent']:<20} "
                  f"seed={g['seed']} P{g['seat']}  me {g['our_money']:>9.0f} vs "
                  f"{g['opp_money']:>9.0f}  ({g['margin']:+.0f})")
            print(f"       money d5/10/15/20/25/29 me {g['my_money_d']} op {g['op_money_d']}"
                  f"  lead-flip day={g.get('flip_day')}")
            print(f"       plants {g['my_plants_d']} weeds29={g['weeds29']} "
                  f"anim={g['my_anim']}(opp {g['op_anim']}) quads29={g['quads29']} "
                  f"move%={g['move_pct']:.0%} hires={g['hires']} nonpass={g['nonpass']}")
            print(f"       me sells {dict(sorted(g['my_sells'].items(), key=lambda i:-i[1]))}")
            print(f"       op sells {dict(sorted(g['opp_sells'].items(), key=lambda i:-i[1]))} "
                  f"mix29={g['mix29']}")


def print_compare(a_games, b_games):
    a_runs = sorted({g["run"] for g in a_games})
    b_runs = sorted({g["run"] for g in b_games})
    ao, abopp, *_ = summary(a_games)
    bo, bbopp, *_ = summary(b_games)
    print("=" * 100)
    print(f"A: {', '.join(a_runs)}  ({', '.join(sorted({g.get('agent') for g in a_games if g.get('agent')}))})")
    print(f"B: {', '.join(b_runs)}  ({', '.join(sorted({g.get('agent') for g in b_games if g.get('agent')}))})")
    print(f"\noverall  A {ao['W']}/{ao['T']}/{ao['L']} rate {ao['score_rate']:.0%} "
          f"coins {ao['our_coins_mean']:.0f}   ->   "
          f"B {bo['W']}/{bo['T']}/{bo['L']} rate {bo['score_rate']:.0%} "
          f"coins {bo['our_coins_mean']:.0f}")
    print("\nper opponent  (A W/T/L  margin_mean   ->   B W/T/L  margin_mean)")
    for opp in sorted(set(abopp) | set(bbopp)):
        a = abopp.get(opp)
        b = bbopp.get(opp)
        a_s = f"{a['W']}/{a['T']}/{a['L']} {a['margin_mean']:+8.0f}" if a else "   --      "
        b_s = f"{b['W']}/{b['T']}/{b['L']} {b['margin_mean']:+8.0f}" if b else "   --      "
        flag = ""
        if a and b:
            da = (a["W"] + 0.5 * a["T"]) / a["n"]
            db = (b["W"] + 0.5 * b["T"]) / b["n"]
            flag = "  <<< B worse" if db < da - 1e-9 else ("  >>> B better" if db > da + 1e-9 else "")
        print(f"  {opp:<22} {a_s}   ->   {b_s}{flag}")


def dump_json(games, path):
    overall, by_opp, by_arch, diag, sells = summary(games)
    payload = dict(overall=overall, by_opponent=by_opp, by_archetype=by_arch,
                   diagnostics=diag, sells=sells,
                   games=[{k: v for k, v in g.items()
                           if k not in ("my_sells", "opp_sells", "mix29")}
                          for g in games])
    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\njson -> {path}")


def dump_csv(games, path):
    cols = ["run", "agent", "opponent", "arch", "seat", "seed", "result", "margin",
            "our_money", "opp_money", "move_pct", "weeds29", "my_anim", "op_anim",
            "quads29", "hires", "nonpass", "flip_day", "errored", "stderr_steps"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for g in games:
            w.writerow(g)
    print(f"csv  -> {path}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*",
                    help="compete_runs/ dir(s) or bare stamp(s); default = newest")
    ap.add_argument("--last", type=int, metavar="N",
                    help="merge the N most recent runs")
    ap.add_argument("--worst", type=int, default=12, help="worst-N game dump (default 12)")
    ap.add_argument("--full", action="store_true", help="dump every game, not just worst-N")
    ap.add_argument("--json", metavar="PATH", help="also write a machine-readable summary")
    ap.add_argument("--csv", metavar="PATH", help="also write a per-game CSV")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="two run dirs/stamps: print a per-opponent W/T/L diff")
    args = ap.parse_args()

    if args.compare:
        a = load_games(resolve_run(args.compare[0]))
        b = load_games(resolve_run(args.compare[1]))
        print_compare(a, b)
        return

    if args.last:
        run_dirs = newest_runs(args.last)
    elif args.paths:
        run_dirs = [resolve_run(t) for t in args.paths]
    else:
        run_dirs = newest_runs(1)

    games = []
    for d in run_dirs:
        games.extend(load_games(d))
    if not games:
        sys.exit("no games found")

    print_report(games, args.worst, args.full)
    if args.json:
        dump_json(games, args.json)
    if args.csv:
        dump_csv(games, args.csv)


if __name__ == "__main__":
    main()
