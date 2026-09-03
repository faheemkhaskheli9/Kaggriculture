"""Single competitive match: a randomly picked opponent vs. our agent.

Models one real-ladder game as closely as `kaggle-environments` allows:

* opponent is drawn at random from a pool (the `bots/` archetypes + `starter`
  by default) -- these reproduce strategies that beat us on the ladder,
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
    python compete.py --include-lineage     # also allow main_v1..v5 in the pool
    python compete.py --save-replay         # dump replay JSON per match
    python compete.py --debug               # env debug traces (NOT ladder-like)
"""
import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

from kaggle_environments import make

ROOT = Path(__file__).resolve().parent
SEED_LO, SEED_HI = 100_000_000, 999_999_999  # inclusive 9-digit range

# Opponent models that beat our agent on the real ladder (see PLAN_3000_v4.md
# + PLAN_LADDER_ECON.md s2: animal_factory is 56% of ladder games and our worst
# matchup, so bot_animalfactory_v2 -- the strong proxy -- carries extra weight).
DEFAULT_POOL = [
    "bots/bot_animalfactory_v2.py",
    "bots/bot_wheatflood.py",
    "bots/bot_animalfarm.py",
    "bots/bot_melonmono.py",
    "bots/bot_premium.py",
    "starter",
]
LINEAGE = [
    "agents/main_v1.py",
    "agents/main_v2.py",
    "agents/main_v3.py",
    "agents/main_v4.py",
    "agents/main_v5.py",
    "agents/main_v6.py",
    "agents/main_v7.py",
    "agents/main_p2.py",
    "agents/main_p3.py"
    ]

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


def money_from_final(final):
    out = []
    for i, state in enumerate(final):
        try:
            out.append(float(state.observation.farms[i].money))
        except Exception:
            out.append(float(state.reward or 0))
    return out


def play_match(agent_path, opponent, seed, rng, save_replay=False, debug=False):
    our_seat = rng.randint(0, 1)
    line = [None, None]
    line[our_seat] = agent_path
    line[1 - our_seat] = opponent

    config = dict(COMPETITION_CONFIG, seed=seed)
    env = make("kaggriculture", configuration=config, debug=debug)

    t0 = time.time()
    env.run(line)
    elapsed = time.time() - t0

    final = env.steps[-1]
    statuses = [str(s.status) for s in final]
    money = money_from_final(final)
    ours, theirs = money[our_seat], money[1 - our_seat]
    result = "WIN" if ours > theirs else ("LOSS" if ours < theirs else "TIE")
    # kaggle-environments scrubs configuration["seed"] onto env.info
    used_seed = env.info.get("seed", seed) if isinstance(env.info, dict) else seed
    errored = any(s != "DONE" for s in statuses)

    row = {
        "opponent": Path(opponent).stem if opponent.endswith(".py") else opponent,
        "seed": used_seed,
        "our_seat": our_seat,
        "our_money": ours,
        "opp_money": theirs,
        "margin": ours - theirs,
        "result": result,
        "statuses": statuses,
        "errored": errored,
        "seconds": elapsed,
    }
    if save_replay:
        out_dir = ROOT / "compete_replays"
        out_dir.mkdir(exist_ok=True)
        tag = f"{row['opponent']}_seed{used_seed}_{result}.json"
        (out_dir / tag).write_text(json.dumps(env.toJSON()), encoding="utf-8")
        row["replay"] = str(out_dir / tag)
    return row


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
    if row.get("replay"):
        print(f"       replay -> {row['replay']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default="main.py", help="our entry (default main.py)")
    ap.add_argument("--opponent", help="force a specific opponent (skip random pick)")
    ap.add_argument("--pool", nargs="+", default=DEFAULT_POOL,
                    help="opponent pool to draw from")
    ap.add_argument("--include-lineage", action="store_true",
                    help="add main_v1..v5 to the pool")
    ap.add_argument("--games", type=int, default=1, help="number of matches")
    ap.add_argument("--seed", type=int,
                    help="pin the 9-digit episode seed (else random per match)")
    ap.add_argument("--pick-seed", type=int,
                    help="RNG seed for opponent/seat/episode-seed selection "
                         "(makes the whole run reproducible)")
    ap.add_argument("--save-replay", action="store_true")
    ap.add_argument("--debug", action="store_true",
                    help="env debug traces; NOT how the ladder runs")
    args = ap.parse_args()

    agent_path = str((ROOT / args.agent).resolve())
    if not Path(agent_path).exists():
        sys.exit(f"agent not found: {args.agent}")

    if args.seed is not None and not (SEED_LO <= args.seed <= SEED_HI):
        sys.exit(f"--seed must be a 9-digit integer in [{SEED_LO}, {SEED_HI}]")

    pool = list(args.pool) + (LINEAGE if args.include_lineage else [])
    pool = resolve_pool(pool)
    forced_opp = resolve_pool([args.opponent])[0] if args.opponent else None

    rng = random.Random(args.pick_seed)

    print(f"agent   : {args.agent}")
    print(f"pool    : {', '.join(Path(p).stem if p.endswith('.py') else p for p in pool)}")
    print(f"config  : episodeSteps={COMPETITION_CONFIG['episodeSteps']} "
          f"startingMoney={COMPETITION_CONFIG['startingMoney']} "
          f"actTimeout={COMPETITION_CONFIG['actTimeout']}s debug={args.debug}")
    print("-" * 100)

    rows = []
    for i in range(1, args.games + 1):
        opponent = forced_opp or rng.choice(pool)
        seed = args.seed if args.seed is not None else rng.randint(SEED_LO, SEED_HI)
        row = play_match(agent_path, opponent, seed, rng,
                         save_replay=args.save_replay, debug=args.debug)
        rows.append(row)
        print_row(i, row)

    if args.games > 1:
        print("-" * 100)
        wins = sum(r["result"] == "WIN" for r in rows)
        ties = sum(r["result"] == "TIE" for r in rows)
        losses = sum(r["result"] == "LOSS" for r in rows)
        errs = sum(r["errored"] for r in rows)
        coins = [r["our_money"] for r in rows]
        margins = [r["margin"] for r in rows]
        print(f"W/T/L = {wins}/{ties}/{losses}   score={(wins + 0.5 * ties) / len(rows):.1%}   "
              f"errors={errs}")
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
            print(f"  vs {opp:<14} {w}/{t}/{l}  margin mean={statistics.fmean(x['margin'] for x in rs):+.0f}")


if __name__ == "__main__":
    main()
