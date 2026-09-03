"""Lean paired head-to-head gate -- no env.toJSON()/deepcopy (that MemoryErrors
on this py3.14 + kaggle-environments setup after ~40 games). Mirrors compete.py's
lightweight final-money read. debug=False = ladder-like (exceptions -> all PASS).

    python scratchpad/gate.py --cands experiments/main_v8e.py main.py \
        --opps starter bots/bot_animalfarm.py bots/bot_wheatflood.py \
               agents/main_v4.py agents/main_v7.py --games 8
"""
import argparse, statistics, sys, time
from pathlib import Path
from kaggle_environments import make

ROOT = Path(__file__).resolve().parent.parent


def resolve(n):
    return str(ROOT / n) if n.endswith(".py") else n


def play(a, b, seed, seat):
    line = [a, b] if seat == 0 else [b, a]
    env = make("kaggriculture",
               configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run(line)
    f = env.steps[-1]
    try:
        m = [float(f[i].observation.farms[i].money) for i in range(2)]
    except Exception:
        m = [float(f[i].reward or 0) for i in range(2)]
    ok = all(str(s.status) == "DONE" for s in f)
    return m[seat], m[1 - seat], ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cands", nargs="+", required=True)
    ap.add_argument("--opps", nargs="+", required=True)
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=10_000_000)
    a = ap.parse_args()

    for cand in a.cands:
        cp = resolve(cand)
        print(f"\n=== {cand} ===", flush=True)
        for opp in a.opps:
            op = resolve(opp)
            rows, errs = [], 0
            t0 = time.time()
            for g in range(a.games):
                seat = g % 2
                seed = a.seed0 + g // 2
                ours, theirs, ok = play(cp, op, seed, seat)
                errs += not ok
                rows.append((ours, theirs))
            w = sum(o > t for o, t in rows)
            l = sum(o < t for o, t in rows)
            oc = [o for o, _ in rows]
            mg = [o - t for o, t in rows]
            print(f"  vs {Path(opp).stem if opp.endswith('.py') else opp:16} "
                  f"W-L {w}-{l}  ours mean/min {statistics.fmean(oc):8.0f}/{min(oc):8.0f}  "
                  f"margin mean {statistics.fmean(mg):+8.0f}  err {errs}  "
                  f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
