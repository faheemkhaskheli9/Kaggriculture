"""Round-robin tournament for Kaggriculture agents (PLAN_CONTENDERS.md section 5).

Plays every agent against every other, both seats, `--games` games per pair, and
prints:
  * a SCORE-RATE matrix (row's score vs column),
  * a MEAN OWN COINS matrix,
  * a PER-AGENT summary whose key column is `worst` -- the lowest score-rate the
    agent has against any single opponent. A contender with a hard counter
    (worst < ~0.40) is not submittable.

This is a *filter*, not proof -- the local pool is not the ladder. Use it to kill
dominated agents and hard counters, then trust ladder replays for strategy.

    python tournament.py                       # default pool, 10 games/pair
    python tournament.py --games 20
    python tournament.py --agents main.py contenders/c_wheatflood.py starter
"""
import argparse
import csv
import datetime as _dt
import itertools
import statistics
from pathlib import Path

from test import run_game, percentile

ROOT = Path(__file__).resolve().parent


def _dir_size_mb(path):
    total = 0
    for p in Path(path).rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total / 1e6

DEFAULT_AGENTS = [
    "main.py",
    "main_ml.py",
    "contenders/c_wheatflood.py",
    "contenders/c_animalfactory.py",
    "contenders/c_premium.py",
    "bots/bot_wheatflood.py",
    "bots/bot_animalfarm.py",
    "starter"
]

_AGENTS_DIR = ROOT / "agents"
if _AGENTS_DIR.is_dir():
    CUSTOM_AGENTS = sorted(
        f"agents/{p.name}"
        for p in _AGENTS_DIR.iterdir()
        if p.is_file() and p.suffix == ".py" and not p.name.startswith("_")
    )
    DEFAULT_AGENTS += CUSTOM_AGENTS

def _name(p):
    return p if not p.endswith(".py") else Path(p).stem


def _score_rate(rows):
    if not rows:
        return None
    w = sum(r[0] > 0 for r in rows)
    t = sum(r[0] == 0 for r in rows)
    return (w + 0.5 * t) / len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=6,
                    help="games per pair (>=2, seats alternate)")
    ap.add_argument("--agents", nargs="+", default=DEFAULT_AGENTS)
    ap.add_argument("--seed", type=int, default=100_000_000,
                    help="base episode seed; negative => fresh random per game")
    ap.add_argument("--replay-dir", default="tournament_replays",
                    help="parent dir for stored replays/logs; each run gets a "
                         "timestamped subfolder with a manifest.csv")
    ap.add_argument("--no-store", action="store_true",
                    help="do not persist replays/logs (default: store every game)")
    args = ap.parse_args()
    if args.games < 2:
        ap.error("--games must be >= 2 so both seats are tested")

    run_dir = manifest_fh = manifest = None
    if not args.no_store:
        run_dir = Path(args.replay_dir) / _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_fh = open(run_dir / "manifest.csv", "w", newline="", encoding="utf-8")
        manifest = csv.writer(manifest_fh)
        manifest.writerow([
            "tag", "row_agent", "col_agent", "game", "row_seat", "seed",
            "result_row", "coins_row", "coins_col", "errored", "statuses",
            "replay_file", "logs_file",
        ])
        print(f"storing replays + logs under {run_dir}/")

    agents, names = [], []
    for a in args.agents:
        if a.endswith(".py") and not (ROOT / a).exists():
            print(f"skip (not found): {a}")
            continue
        agents.append(str(ROOT / a) if a.endswith(".py") else a)
        names.append(_name(a))
    n = len(agents)
    if n < 2:
        ap.error("need at least 2 resolvable agents")

    # cell[(i, j)] = list of (result_for_i, coins_i, coins_j, errored)
    cell = {(i, j): [] for i in range(n) for j in range(n) if i != j}
    move = {i: [] for i in range(n)}

    total_pairs = n * (n - 1) // 2
    for k, (i, j) in enumerate(itertools.combinations(range(n), 2), 1):
        for g in range(args.games):
            seat = g % 2
            seed = None if args.seed < 0 else args.seed + g // 2
            tag = f"{names[i]}__vs__{names[j]}__g{g}_seat{seat}" if run_dir else None
            r = run_game(agents[i], agents[j], seat, seed=seed,
                         save_dir=run_dir, save_tag=tag)
            err = any(s != "DONE" for s in r["statuses"])
            cell[(i, j)].append((r["result"], r["candidate_money"], r["opponent_money"], err))
            cell[(j, i)].append((-r["result"], r["opponent_money"], r["candidate_money"], err))
            d = r.get("diag") or {}
            if "move_share" in d:
                move[i].append(d["move_share"])
            if manifest is not None:
                manifest.writerow([
                    tag, names[i], names[j], g, seat, r.get("seed"),
                    r["result"], r["candidate_money"], r["opponent_money"],
                    int(err), "|".join(r["statuses"]),
                    Path(r["replay_path"]).name if r.get("replay_path") else "",
                    Path(r["logs_path"]).name if r.get("logs_path") else "",
                ])
                manifest_fh.flush()
        print(f"  pair {k}/{total_pairs}: {names[i]} vs {names[j]}      ", end="\r")
    print(" " * 78, end="\r")
    if manifest_fh is not None:
        manifest_fh.close()
        print(f"stored {sum(len(v) for v in cell.values()) // 2} games "
              f"({_dir_size_mb(run_dir):.1f} MB) under {run_dir}/")

    col = max(13, max(len(x) for x in names) + 1)
    head = " " * col + "".join(f"{x[:8]:>9}" for x in names)

    print("\nSCORE-RATE  (row's score vs column)")
    print(head)
    for i in range(n):
        line = f"{names[i]:<{col}}"
        for j in range(n):
            line += f"{'--':>9}" if i == j else f"{_score_rate(cell[(i, j)]):>9.2f}"
        print(line)

    print("\nMEAN OWN COINS  (row vs column)")
    print(head)
    for i in range(n):
        line = f"{names[i]:<{col}}"
        for j in range(n):
            if i == j:
                line += f"{'--':>9}"
            else:
                line += f"{statistics.fmean(r[1] for r in cell[(i, j)]):>9.0f}"
        print(line)

    print("\nPER-AGENT  (overall = score vs the whole field)")
    print(f"{'agent':<{col}}{'overall':>9}{'worst':>9}{'worst_vs':>16}"
          f"{'meanC':>9}{'p10C':>9}{'move%':>7}{'err':>5}")
    ranking = []
    for i in range(n):
        allrows = [r for j in range(n) if j != i for r in cell[(i, j)]]
        worst_sr, worst_j = 2.0, None
        for j in range(n):
            if j == i:
                continue
            s = _score_rate(cell[(i, j)])
            if s is not None and s < worst_sr:
                worst_sr, worst_j = s, j
        coins = [r[1] for r in allrows]
        errs = sum(r[3] for r in allrows)
        mv = statistics.fmean(move[i]) if move[i] else 0.0
        overall = _score_rate(allrows)
        ranking.append((overall, i))
        print(f"{names[i]:<{col}}{overall:>9.2f}{worst_sr:>9.2f}"
              f"{names[worst_j][:15]:>16}{statistics.fmean(coins):>9.0f}"
              f"{percentile(coins, 0.10):>9.0f}{mv:>7.0%}{errs:>5}")

    print("\nrank:", " > ".join(names[i] for _, i in sorted(ranking, reverse=True)))


if __name__ == "__main__":
    main()
