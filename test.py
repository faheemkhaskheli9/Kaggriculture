"""Local paired benchmark for Kaggriculture agents.

Examples:
    python test.py --games 20
    python test.py --games 100 --candidate main.py --incumbent main_v1.py
    python test.py --games 20 --opponents starter random main_v1.py --save-worst 5
"""
import argparse
import json
import math
import statistics
from pathlib import Path

from kaggle_environments import make


def money_from_final(final):
    values = []
    for i, state in enumerate(final):
        try:
            values.append(float(state.observation.farms[i].money))
        except Exception:
            values.append(float(state.reward or 0))
    return values


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def run_game(candidate, opponent, candidate_seat):
    agents = [candidate, opponent] if candidate_seat == 0 else [opponent, candidate]
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run(agents)
    final = env.steps[-1]
    statuses = [str(s.status) for s in final]
    money = money_from_final(final)
    c_money = money[candidate_seat]
    o_money = money[1 - candidate_seat]
    result = 1 if c_money > o_money else (-1 if c_money < o_money else 0)
    return {
        "result": result,
        "candidate_money": c_money,
        "opponent_money": o_money,
        "difference": c_money - o_money,
        "statuses": statuses,
        "replay": env.toJSON(),
    }


def summarize(rows):
    wins = sum(r["result"] > 0 for r in rows)
    ties = sum(r["result"] == 0 for r in rows)
    losses = sum(r["result"] < 0 for r in rows)
    coins = [r["candidate_money"] for r in rows]
    diffs = [r["difference"] for r in rows]
    errors = sum(any(status != "DONE" for status in r["statuses"]) for r in rows)
    return {
        "games": len(rows),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "win_rate": wins / len(rows) if rows else 0,
        "score_rate": (wins + 0.5 * ties) / len(rows) if rows else 0,
        "mean_coins": statistics.fmean(coins) if coins else 0,
        "median_coins": statistics.median(coins) if coins else 0,
        "p10_coins": percentile(coins, 0.10),
        "mean_difference": statistics.fmean(diffs) if diffs else 0,
        "errors": errors,
    }


def print_summary(opponent, summary):
    print(
        f"{opponent:16} games={summary['games']:4d} "
        f"W/T/L={summary['wins']}/{summary['ties']}/{summary['losses']} "
        f"score={summary['score_rate']:.1%} "
        f"coins mean/median/p10={summary['mean_coins']:.0f}/"
        f"{summary['median_coins']:.0f}/{summary['p10_coins']:.0f} "
        f"diff={summary['mean_difference']:+.0f} errors={summary['errors']}"
    )


def save_worst(rows, opponent, count, output_dir):
    if count <= 0:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(opponent).stem.replace(" ", "_")
    for rank, row in enumerate(sorted(rows, key=lambda r: r["difference"])[:count], 1):
        target = output_dir / f"{safe_name}_worst_{rank}.json"
        with target.open("w", encoding="utf-8") as handle:
            json.dump(row["replay"], handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="main.py")
    parser.add_argument("--incumbent", default="main_v1.py")
    parser.add_argument("--opponents", nargs="+")
    parser.add_argument("--games", type=int, default=20,
                        help="Total games per opponent; seats alternate.")
    parser.add_argument("--save-worst", type=int, default=0)
    parser.add_argument("--replay-dir", default="benchmark_replays")
    args = parser.parse_args()

    opponents = args.opponents or ["starter", "random", args.incumbent]
    if args.games < 2:
        parser.error("--games must be at least 2 so both seats are tested")

    all_rows = []
    print(f"Candidate: {args.candidate} | games/opponent: {args.games}")
    for opponent in opponents:
        rows = []
        for game_index in range(args.games):
            seat = game_index % 2
            row = run_game(args.candidate, opponent, seat)
            rows.append(row)
            if (game_index + 1) % max(1, args.games // 10) == 0:
                print(f"  {opponent}: {game_index + 1}/{args.games}", end="\r")
        print(" " * 70, end="\r")
        summary = summarize(rows)
        print_summary(opponent, summary)
        save_worst(rows, opponent, args.save_worst, Path(args.replay_dir))
        all_rows.extend(rows)

    print("-" * 100)
    print_summary("OVERALL", summarize(all_rows))


if __name__ == "__main__":
    main()
