"""Single competitive match: a randomly picked opponent vs. our agent.

Models one real-ladder game as closely as `kaggle-environments` allows:

* opponent is drawn at random from a pool (the `bots/` archetypes, contenders,
  every `agents/*.py` version, and `starter` by default),
* the episode seed is a random 9-digit integer (100000000..999999999),
* seat assignment is random (the ladder does not fix seats),
* the environment uses the stock competition configuration
  (`episodeSteps=720`, `startingMoney=3000`, `actTimeout=1`, `runTimeout=1200`)
  and runs with `debug=False`, so a raised exception is silently swallowed to
  all-PASS exactly like on Kaggle.

Examples
--------
    python compete.py                       # one random match vs a random pool bot
    python compete.py --games 10            # ten matches, fresh opponent+seed each
    python compete.py --seed 123456789      # pin the 9-digit seed
    python compete.py --opponent bots/bot_premium.py
    python compete.py --pool bots/bot_wheatflood.py bots/bot_animalfarm.py starter
    python compete.py --exclude-lineage     # omit versioned agents from the pool
    python compete.py --no-store            # skip the default replay/log archive
    python compete.py --debug               # env debug traces (NOT ladder-like)
    python compete.py --games 300 --workers 6   # shard 300 independent games across 6 procs
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import random
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from kaggle_environments import make

ROOT = Path(__file__).resolve().parent
SEED_LO, SEED_HI = 100_000_000, 999_999_999  # inclusive 9-digit range

# Opponent models that beat our agent on the real ladder (see PLAN_3000_v4.md
# + PLAN_LADDER_ECON.md s2: animal_factory is 56% of ladder games and our worst
# matchup, so bot_animalfactory_v2 -- the strong proxy -- carries extra weight).
# P0.2 pipeline audit (2026-09-08): the pool was a hand-maintained list that
# silently omitted bots/bot_factory_v3.py (real-ladder-mined animal_factory, the
# documented worst matchup) and bots/bot_top10clone.py (2850-3010-rated clone) --
# exactly the two ladder-representative opponents the gate most needs. Glob
# bots/bot_*.py so a committed opponent can never again be excluded by omission.
DEFAULT_POOL = [
    *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "bots").glob("bot_*.py")),
    "contenders/c_animalfactory.py",
    "contenders/c_premium.py",
    "contenders/c_v5clone.py",
    "contenders/c_wheatflood.py",
    "starter",
]
# Regression guard (P0.2): every bot on disk must be in the pool.
_disk_bots = {p.relative_to(ROOT).as_posix() for p in (ROOT / "bots").glob("bot_*.py")}
assert _disk_bots <= set(DEFAULT_POOL), (
    "compete.py DEFAULT_POOL is missing bots on disk: "
    + ", ".join(sorted(_disk_bots - set(DEFAULT_POOL)))
)
# Discover versioned agents automatically so newly archived strategies are
# immediately represented in local competition runs.
LINEAGE = sorted(
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / "agents").glob("*.py")
    if not path.name.startswith("_")
)

# Stock competition configuration. Left unset -> kaggle-environments default,
# but pinned here so a local env upgrade cannot silently change the match.
COMPETITION_CONFIG = {
    "episodeSteps": 720,
    "actTimeout": 1,
    "runTimeout": 1200,
    "startingMoney": 3000,
    "turnsPerDay": 24,
    "maxMarketOrdersPerTurn": 10,
}
MOVEMENT_OPS = {"NORTH", "SOUTH", "EAST", "WEST"}
PRODUCTIVE_OPS = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
    "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE", "PICKUP",
    "PLACE", "DROP",
}
CHECKPOINT_DAYS = (5, 10, 15, 20, 25, 29)


def replay_diagnostics(replay, seat):
    """Extract compact causal metrics; never retain the full replay in a row."""
    actions = {}
    market_orders = {}
    movement = productive = nonpass = 0
    plant_to_weed = animal_escapes = 0
    checkpoints = {}
    previous_tiles = None

    for step in replay.get("steps", []):
        if seat >= len(step):
            continue
        state = step[seat]
        action = state.get("action") or {}
        unit_actions = []
        farmer = action.get("farmer")
        if isinstance(farmer, list) and farmer:
            unit_actions.append(farmer)
        unit_actions.extend(a for a in (action.get("hands") or [])
                            if isinstance(a, list) and a)
        for unit_action in unit_actions:
            op = unit_action[0]
            actions[op] = actions.get(op, 0) + 1
            if op != "PASS":
                nonpass += 1
            if op in MOVEMENT_OPS:
                movement += 1
            if op in PRODUCTIVE_OPS:
                productive += 1
        for order in action.get("market") or []:
            if isinstance(order, list) and order:
                market_orders[order[0]] = market_orders.get(order[0], 0) + 1

        obs = state.get("observation") or {}
        farms = obs.get("farms") or []
        if seat >= len(farms):
            continue
        farm = farms[seat]
        tiles = farm.get("tiles") or []
        if previous_tiles is not None:
            for y, row in enumerate(tiles):
                for x, tile in enumerate(row):
                    if y >= len(previous_tiles) or x >= len(previous_tiles[y]):
                        continue
                    old = previous_tiles[y][x]
                    if isinstance(old, dict) and isinstance(tile, dict):
                        if old.get("kind") == "PLANT" and tile.get("kind") == "WEED":
                            plant_to_weed += 1
                        if old.get("animal") and not tile.get("animal"):
                            animal_escapes += 1
        previous_tiles = tiles

        day = obs.get("day")
        if day in CHECKPOINT_DAYS and day not in checkpoints:
            plants = weeds = animals = 0
            for row in tiles:
                for tile in row:
                    if isinstance(tile, dict):
                        plants += tile.get("kind") == "PLANT"
                        weeds += tile.get("kind") == "WEED"
                        animals += bool(tile.get("animal"))
            private = obs.get("private") or {}
            shed = private.get("shed") or {}
            checkpoints[str(day)] = {
                "money": farm.get("money", 0), "plants": plants,
                "animals": animals, "weeds": weeds,
                "quadrants": len(farm.get("unlocked_quadrants") or []),
                "shed_items": sum(v for v in shed.values() if isinstance(v, (int, float))),
            }
    return {
        "movement_pct": movement / nonpass if nonpass else 0.0,
        "movement_actions": movement, "productive_actions": productive,
        "nonpass_actions": nonpass, "plant_to_weed": plant_to_weed,
        "animal_escapes": animal_escapes, "actions": actions,
        "market_orders": market_orders, "checkpoints": checkpoints,
    }


def parse_weights(specs, pool):
    """Parse repeated --weight NAME=N specs into {resolved_pool_entry: weight}."""
    weights = {}
    for spec in specs:
        if "=" not in spec:
            sys.exit(f"--weight must be NAME=WEIGHT (e.g. starter=3), got: {spec}")
        name, _, val = spec.rpartition("=")
        try:
            w = float(val)
        except ValueError:
            sys.exit(f"--weight WEIGHT must be numeric, got: {spec}")
        if w <= 0:
            sys.exit(f"--weight WEIGHT must be > 0, got: {spec}")
        resolved = resolve_pool([name])[0]
        if resolved not in pool:
            label = Path(resolved).stem if resolved.endswith(".py") else resolved
            sys.exit(f"--weight target not in pool: {label}")
        weights[resolved] = w
    return weights


def resolve_pool(names):
    """Validate pool entries; keep built-ins (no '.py') as-is, resolve files."""
    resolved = []
    for name in names:
        if name.endswith(".py"):
            path = (ROOT / name)
            if not path.exists():
                sys.exit(f"pool entry not found: {name}")
            resolved.append(str(path))
        else:
            resolved.append(name)
    return resolved


def load_league_manifest(path_spec):
    """Load a frozen opponent list and weights from a versioned JSON manifest."""
    path = (ROOT / path_spec).resolve()
    if not path.exists():
        sys.exit(f"league manifest not found: {path_spec}")
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("opponents") or []
    if not entries:
        sys.exit(f"league manifest contains no opponents: {path_spec}")
    names = [entry["path"] for entry in entries]
    pool = resolve_pool(names)
    weights = [float(entry.get("weight", 1.0)) for entry in entries]
    if any(weight <= 0 for weight in weights):
        sys.exit("league weights must all be positive")
    return data, pool, weights


def money_from_final(final):
    out = []
    for i, state in enumerate(final):
        try:
            out.append(float(state.observation.farms[i].money))
        except Exception:
            out.append(float(state.reward or 0))
    return out


def play_match(agent_path, opponent, seed, our_seat, save_dir=None, game_number=1,
               debug=False):
    opponent_name = Path(opponent).stem if opponent.endswith(".py") else opponent
    t0 = time.time()
    try:
        line = [None, None]
        line[our_seat] = agent_path
        line[1 - our_seat] = opponent

        config = dict(COMPETITION_CONFIG, seed=seed)
        env = make("kaggriculture", configuration=config, debug=debug)
        env.run(line)
        elapsed = time.time() - t0

        replay = env.toJSON()
        final = env.steps[-1]
        statuses = [str(s.status) for s in final]
        money = money_from_final(final)
        ours, theirs = money[our_seat], money[1 - our_seat]
        result = "WIN" if ours > theirs else ("LOSS" if ours < theirs else "TIE")
        # kaggle-environments scrubs configuration["seed"] onto env.info
        used_seed = env.info.get("seed", seed) if isinstance(env.info, dict) else seed
        errored = any(s != "DONE" for s in statuses)

        row = {
            "opponent": opponent_name,
            "seed": used_seed,
            "our_seat": our_seat,
            "our_money": ours,
            "opp_money": theirs,
            "margin": ours - theirs,
            "result": result,
            "statuses": statuses,
            "errored": errored,
            "seconds": elapsed,
            "diagnostics": replay_diagnostics(replay, our_seat),
        }
        if save_dir is not None:
            save_dir.mkdir(parents=True, exist_ok=True)
            tag = (f"game_{game_number:04d}_{row['opponent']}_seed{used_seed}_"
                   f"seat{our_seat}_{result}")
            replay_path = save_dir / f"{tag}.replay.json.gz"
            logs_path = save_dir / f"{tag}.logs.json"
            with gzip.open(replay_path, "wt", encoding="utf-8") as handle:
                json.dump(replay, handle, separators=(",", ":"))
            with logs_path.open("w", encoding="utf-8") as handle:
                json.dump(getattr(env, "logs", None) or [], handle,
                          separators=(",", ":"))
            row["replay"] = str(replay_path)
            row["logs"] = str(logs_path)
        return row
    except Exception as exc:  # noqa: BLE001 - a crash here must not sink the batch
        # This is distinct from an agent exception (already swallowed to
        # all-PASS by debug=False inside the env). This is a crash in the
        # harness/env plumbing itself (e.g. env.run, replay serialization) --
        # without this guard it propagates out of a worker process and
        # ProcessPoolExecutor.map aborts the *entire* --games batch, discarding
        # every row (and the manifest) collected so far even though replays
        # already written to disk survive.
        return {
            "opponent": opponent_name,
            "seed": seed,
            "our_seat": our_seat,
            "our_money": 0.0,
            "opp_money": 0.0,
            "margin": 0.0,
            "result": "CRASH",
            "statuses": [f"HARNESS_ERROR: {exc!r}"],
            "errored": True,
            "seconds": time.time() - t0,
        }


def _play_match_worker(payload):
    """Top-level so ProcessPoolExecutor (spawn, required on Windows) can pickle it."""
    return play_match(**payload)


def print_row(i, row):
    seat = f"P{row['our_seat']}"
    flag = "  !ERR" if row["errored"] else ""
    print(
        f"[{i:>3}] {row['opponent']:<14} seed={row['seed']:<9} seat={seat} "
        f"{row['result']:<4} ours={row['our_money']:>10.0f} "
        f"opp={row['opp_money']:>10.0f} margin={row['margin']:>+11.0f} "
        f"({row['seconds']:.1f}s){flag}"
    )
    if row["errored"]:
        print(f"       statuses={row['statuses']}")
    # if row.get("replay"):
    #     print(f"       replay -> {row['replay']}")
    #     print(f"       logs   -> {row['logs']}")


def print_summary(rows):
    wins = sum(r["result"] == "WIN" for r in rows)
    ties = sum(r["result"] == "TIE" for r in rows)
    losses = sum(r["result"] == "LOSS" for r in rows)
    crashes = sum(r["result"] == "CRASH" for r in rows)
    errs = sum(r["errored"] for r in rows)
    decided = [r for r in rows if r["result"] != "CRASH"]
    print("-" * 100)
    print(f"W/T/L = {wins}/{ties}/{losses}   "
          f"score={(wins + 0.5 * ties) / len(decided):.1%}   "
          f"crashes={crashes}   errors={errs}   (of {len(rows)} games)")
    if decided:
        coins = [r["our_money"] for r in decided]
        margins = [r["margin"] for r in decided]
        print(f"our coins  mean/median/min = {statistics.fmean(coins):.0f} / "
              f"{statistics.median(coins):.0f} / {min(coins):.0f}")
        print(f"margin     mean/median/min = {statistics.fmean(margins):+.0f} / "
              f"{statistics.median(margins):+.0f} / {min(margins):+.0f}")
    by_opp = {}
    for r in rows:
        by_opp.setdefault(r["opponent"], []).append(r)
    for opp, rs in sorted(by_opp.items()):
        w = sum(x["result"] == "WIN" for x in rs)
        t = sum(x["result"] == "TIE" for x in rs)
        l = sum(x["result"] == "LOSS" for x in rs)
        c = sum(x["result"] == "CRASH" for x in rs)
        decided_rs = [x for x in rs if x["result"] != "CRASH"]
        margin = (f"{statistics.fmean(x['margin'] for x in decided_rs):+.0f}"
                  if decided_rs else "n/a")
        crash_flag = f"  crashes={c}" if c else ""
        print(f"  vs {opp:<14} {w}/{t}/{l}  margin mean={margin}{crash_flag}")


def score_value(row):
    """Leaderboard value of one result; crashes are excluded by callers."""
    return 1.0 if row["result"] == "WIN" else (0.5 if row["result"] == "TIE" else 0.0)


def percentile(values, q):
    """Linear-interpolated percentile without a third-party dependency."""
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def paired_summary(candidate_rows, baseline_rows, bootstrap_samples=5000):
    """Return paired candidate-minus-baseline statistics for matching tuples."""
    pairs = []
    for candidate, baseline in zip(candidate_rows, baseline_rows):
        if any(candidate[k] != baseline[k] for k in ("opponent", "seed", "our_seat")):
            raise ValueError("candidate/baseline rows are not aligned")
        if candidate["result"] == "CRASH" or baseline["result"] == "CRASH":
            continue
        pairs.append({
            "opponent": candidate["opponent"], "seed": candidate["seed"],
            "our_seat": candidate["our_seat"],
            "candidate_result": candidate["result"],
            "baseline_result": baseline["result"],
            "score_delta": score_value(candidate) - score_value(baseline),
            "margin_delta": candidate["margin"] - baseline["margin"],
            "candidate_money": candidate["our_money"],
            "baseline_money": baseline["our_money"],
            "movement_pct_delta": (candidate["diagnostics"]["movement_pct"] -
                                   baseline["diagnostics"]["movement_pct"]),
            "productive_actions_delta": (candidate["diagnostics"]["productive_actions"] -
                                         baseline["diagnostics"]["productive_actions"]),
            "plant_to_weed_delta": (candidate["diagnostics"]["plant_to_weed"] -
                                    baseline["diagnostics"]["plant_to_weed"]),
            "animal_escapes_delta": (candidate["diagnostics"]["animal_escapes"] -
                                     baseline["diagnostics"]["animal_escapes"]),
            "day10_cash_delta": (
                candidate["diagnostics"]["checkpoints"].get("10", {}).get("money", 0) -
                baseline["diagnostics"]["checkpoints"].get("10", {}).get("money", 0)),
        })
    if not pairs:
        return {"pairs": [], "count": 0}
    deltas = [p["score_delta"] for p in pairs]
    rng = random.Random(20260905)
    boot = [statistics.fmean(rng.choice(deltas) for _ in deltas)
            for _ in range(bootstrap_samples)]
    grouped = {}
    for pair in pairs:
        grouped.setdefault(pair["opponent"], []).append(pair)
    by_opponent = {}
    for opponent, group in sorted(grouped.items()):
        by_opponent[opponent] = {
            "count": len(group),
            "score_delta": statistics.fmean(p["score_delta"] for p in group),
            "margin_delta": statistics.fmean(p["margin_delta"] for p in group),
            "improved": sum(p["score_delta"] > 0 for p in group),
            "same": sum(p["score_delta"] == 0 for p in group),
            "regressed": sum(p["score_delta"] < 0 for p in group),
        }
    return {
        "count": len(pairs), "score_delta": statistics.fmean(deltas),
        "ci90_low": percentile(boot, 0.05), "ci90_high": percentile(boot, 0.95),
        "margin_delta_mean": statistics.fmean(p["margin_delta"] for p in pairs),
        "movement_pct_delta": statistics.fmean(p["movement_pct_delta"] for p in pairs),
        "productive_actions_delta": statistics.fmean(
            p["productive_actions_delta"] for p in pairs),
        "day10_cash_delta": statistics.fmean(p["day10_cash_delta"] for p in pairs),
        "plant_to_weed_delta": statistics.fmean(p["plant_to_weed_delta"] for p in pairs),
        "animal_escapes_delta": statistics.fmean(p["animal_escapes_delta"] for p in pairs),
        "improved": sum(d > 0 for d in deltas), "same": sum(d == 0 for d in deltas),
        "regressed": sum(d < 0 for d in deltas), "by_opponent": by_opponent,
        "pairs": pairs,
    }


def print_paired_summary(summary):
    print("=" * 100)
    print("PAIRED CANDIDATE - BASELINE")
    if not summary["count"]:
        print("no valid pairs")
        return
    print(f"pairs={summary['count']}  score delta={summary['score_delta']:+.1%}  "
          f"90% bootstrap CI=[{summary['ci90_low']:+.1%}, {summary['ci90_high']:+.1%}]")
    print(f"improved/same/regressed={summary['improved']}/{summary['same']}/"
          f"{summary['regressed']}  margin delta mean={summary['margin_delta_mean']:+.0f}")
    print(f"movement={summary['movement_pct_delta']:+.1%}  "
          f"productive actions={summary['productive_actions_delta']:+.1f}  "
          f"day10 cash={summary['day10_cash_delta']:+.0f}  "
          f"plant->weed={summary['plant_to_weed_delta']:+.1f}  "
          f"escapes={summary['animal_escapes_delta']:+.1f}")
    for opponent, stats in summary["by_opponent"].items():
        print(f"  vs {opponent:<22} n={stats['count']:<3} "
              f"score delta={stats['score_delta']:+.1%} "
              f"I/S/R={stats['improved']}/{stats['same']}/{stats['regressed']} "
              f"margin delta={stats['margin_delta']:+.0f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default="main.py", help="our entry (default main.py)")
    ap.add_argument("--baseline",
                    help="enable paired A/B mode using this incumbent; both agents "
                         "play identical opponent/seed/seat tuples")
    ap.add_argument("--opponent", help="force a specific opponent (skip random pick)")
    ap.add_argument("--pool", nargs="+", default=DEFAULT_POOL,
                    help="opponent pool to draw from")
    ap.add_argument("--league",
                    help="frozen weighted league JSON; replaces --pool, --weight, "
                         "and automatic lineage")
    ap.add_argument("--weight", nargs="+", default=[], metavar="NAME=N",
                    help="over/under-sample a pool entry, e.g. "
                         "--weight bots/bot_animalfactory_v2.py=4 (repeatable; "
                         "everything else keeps weight 1; the real ladder is "
                         "~56%% animal_factory matchups per CLAUDE.md, far above "
                         "its ~1/21 uniform share once agents/*.py lineage is "
                         "included -- pass this to skew the local gate toward it). "
                         "Leaving this unset keeps a --pick-seed run's match "
                         "sequence identical to before this flag existed.")
    ap.add_argument("--include-lineage", action="store_true",
                    help=argparse.SUPPRESS)  # legacy: lineage is now included by default
    ap.add_argument("--exclude-lineage", action="store_true",
                    help="omit automatically discovered agents/*.py opponents")
    ap.add_argument("--games", type=int, default=100, help="number of matches")
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel worker processes for independent games (sharded); "
                         "opponent/seed/seat selection is drawn single-threaded first so "
                         "the match sequence for a given --pick-seed is unchanged by "
                         "--workers, only its wall-clock cost")
    ap.add_argument("--seed", type=int,
                    help="pin the 9-digit episode seed (else random per match)")
    ap.add_argument("--pick-seed", type=int,
                    help="RNG seed for opponent/seat/episode-seed selection "
                         "(makes the whole run reproducible)")
    ap.add_argument("--output-dir", default="compete_runs",
                    help="parent directory for timestamped replay/log runs")
    ap.add_argument("--no-store", action="store_true",
                    help="do not store replays, logs, or the run manifest")
    ap.add_argument("--save-replay", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--debug", action="store_true",
                    help="env debug traces; NOT how the ladder runs")
    args = ap.parse_args()

    agent_path = str((ROOT / args.agent).resolve())
    if not Path(agent_path).exists():
        sys.exit(f"agent not found: {args.agent}")
    baseline_path = str((ROOT / args.baseline).resolve()) if args.baseline else None
    if baseline_path and not Path(baseline_path).exists():
        sys.exit(f"baseline not found: {args.baseline}")

    if args.seed is not None and not (SEED_LO <= args.seed <= SEED_HI):
        sys.exit(f"--seed must be a 9-digit integer in [{SEED_LO}, {SEED_HI}]")
    if args.games < 1:
        sys.exit("--games must be >= 1")

    league_data = None
    if args.league:
        if args.opponent or args.weight:
            sys.exit("--league cannot be combined with --opponent or --weight")
        league_data, pool, weights = load_league_manifest(args.league)
    else:
        pool = list(args.pool) + ([] if args.exclude_lineage else LINEAGE)
        pool = resolve_pool(pool)
        weights = None
    forced_opp = resolve_pool([args.opponent])[0] if args.opponent else None
    weight_overrides = parse_weights(args.weight, pool) if not args.league else {}
    if weight_overrides:
        weights = [weight_overrides.get(p, 1.0) for p in pool]

    rng = random.Random(args.pick_seed)
    run_dir = None
    if not args.no_store:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        run_dir = ROOT / args.output_dir / stamp
        run_dir.mkdir(parents=True, exist_ok=False)

    def pool_label(p):
        name = Path(p).stem if p.endswith(".py") else p
        w = weight_overrides.get(p)
        return f"{name}*{w:g}" if w else name

    print(f"agent   : {args.agent}")
    if args.baseline:
        print(f"baseline: {args.baseline}  (paired A/B mode; {args.games * 2} total games)")
    if league_data:
        print(f"league  : {args.league} ({league_data.get('name', 'unnamed')})")
    print(f"pool    : {', '.join(pool_label(p) for p in pool)}")
    print(f"config  : episodeSteps={COMPETITION_CONFIG['episodeSteps']} "
          f"startingMoney={COMPETITION_CONFIG['startingMoney']} "
          f"actTimeout={COMPETITION_CONFIG['actTimeout']}s debug={args.debug}")
    print(f"archive : {run_dir if run_dir else 'disabled'}")
    print("-" * 100)

    # Draw opponent/seed/seat for every game single-threaded first, in the same
    # order as the original sequential loop, so a given --pick-seed produces
    # the identical match sequence regardless of --workers.
    payloads = []
    for i in range(1, args.games + 1):
        if forced_opp:
            opponent = forced_opp
        elif weights is not None:
            opponent = rng.choices(pool, weights=weights, k=1)[0]
        else:
            opponent = rng.choice(pool)
        seed = args.seed if args.seed is not None else rng.randint(SEED_LO, SEED_HI)
        our_seat = rng.randint(0, 1)
        candidate_dir = run_dir / "candidate" if run_dir and baseline_path else run_dir
        payloads.append(dict(agent_path=agent_path, opponent=opponent, seed=seed,
                             our_seat=our_seat, save_dir=candidate_dir, game_number=i,
                             debug=args.debug))

    baseline_payloads = []
    if baseline_path:
        baseline_dir = run_dir / "baseline" if run_dir else None
        baseline_payloads = [dict(payload, agent_path=baseline_path,
                                  save_dir=baseline_dir)
                             for payload in payloads]

    # HEARTBEAT_EVERY games, print a running score so a long unattended
    # --games 120+ run is not silent for minutes at a time.
    HEARTBEAT_EVERY = 20
    rows = []
    baseline_rows = []

    def maybe_heartbeat(i):
        if args.games >= HEARTBEAT_EVERY and i % HEARTBEAT_EVERY == 0 and i < args.games:
            wins = sum(r["result"] == "WIN" for r in rows)
            ties = sum(r["result"] == "TIE" for r in rows)
            score = (wins + 0.5 * ties) / len(rows)
            print(f"     ... {i}/{args.games} done, running score={score:.1%}")

    interrupted = False
    try:
        if args.workers <= 1:
            for i, payload in enumerate(payloads, start=1):
                row = play_match(**payload)
                rows.append(row)
                print_row(i, row)
                if baseline_path:
                    baseline_row = play_match(**baseline_payloads[i - 1])
                    baseline_rows.append(baseline_row)
                    print("       baseline:", end=" ")
                    print_row(i, baseline_row)
                maybe_heartbeat(i)
        else:
            # ProcessPoolExecutor.map yields results in submission order (it
            # still computes concurrently up to max_workers), so the printed
            # stream stays in game-number order exactly like the sequential
            # path.
            with ProcessPoolExecutor(max_workers=args.workers) as ex:
                try:
                    if baseline_path:
                        combined = payloads + baseline_payloads
                        completed = list(ex.map(_play_match_worker, combined))
                        rows = completed[:len(payloads)]
                        baseline_rows = completed[len(payloads):]
                        for i, (row, baseline_row) in enumerate(
                                zip(rows, baseline_rows), start=1):
                            print_row(i, row)
                            print("       baseline:", end=" ")
                            print_row(i, baseline_row)
                            maybe_heartbeat(i)
                    else:
                        for i, row in enumerate(ex.map(_play_match_worker, payloads), start=1):
                            rows.append(row)
                            print_row(i, row)
                            maybe_heartbeat(i)
                except KeyboardInterrupt:
                    # Don't let the executor's default __exit__ block waiting on
                    # in-flight workers (or raise its own teardown error, which
                    # would replace this KeyboardInterrupt and skip the summary/
                    # manifest below entirely) -- drop whatever hasn't finished
                    # and re-raise so the outer handler runs uniformly.
                    ex.shutdown(wait=False, cancel_futures=True)
                    raise
    except KeyboardInterrupt:
        interrupted = True
        print(f"\ninterrupted after {len(rows)}/{args.games} games -- "
              f"reporting partial results")
    finally:
        # Always report + archive whatever completed, even on Ctrl-C or (with
        # --workers<=1) a harness crash that play_match's own guard didn't
        # catch (e.g. a KeyboardInterrupt mid-game). Without this, a run that
        # dies late loses every already-played game's summary and manifest.
        if rows:
            print_summary(rows)
            pair_report = None
            if baseline_path and len(baseline_rows) == len(rows):
                pair_report = paired_summary(rows, baseline_rows)
                print_paired_summary(pair_report)
            if run_dir is not None:
                manifest = {
                    "agent": args.agent,
                    "baseline": args.baseline,
                    "created_at": dt.datetime.now().astimezone().isoformat(),
                    "configuration": COMPETITION_CONFIG,
                    "league": args.league,
                    "league_definition": league_data,
                    "pick_seed": args.pick_seed,
                    "games_requested": args.games,
                    "games_completed": len(rows),
                    "interrupted": interrupted,
                    "games": rows,
                }
                if baseline_path:
                    manifest["baseline_games"] = baseline_rows
                    manifest["paired"] = pair_report
                manifest_path = run_dir / "manifest.json"
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                print(f"manifest  -> {manifest_path}")
                if pair_report:
                    csv_path = run_dir / "paired.csv"
                    with csv_path.open("w", newline="", encoding="utf-8") as handle:
                        writer = csv.DictWriter(handle, fieldnames=list(pair_report["pairs"][0]))
                        writer.writeheader()
                        writer.writerows(pair_report["pairs"])
                    print(f"paired CSV -> {csv_path}")
    if interrupted:
        # A caller (e.g. tools/auto_improve.py) must be able to tell "ran to
        # completion" (exit 0, parseable summary) apart from "was cut off"
        # (no summary line, or a partial one) without sniffing stdout text --
        # an unhandled KeyboardInterrupt's exit code is unreliable across
        # platforms, so make it explicit.
        sys.exit(130)


if __name__ == "__main__":
    main()
