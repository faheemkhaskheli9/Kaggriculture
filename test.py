"""Local paired benchmark for Kaggriculture agents.

Examples:
    python test.py --games 20
    python test.py --games 100 --candidate main.py --incumbent main_v1.py
    python test.py --games 20 --opponents starter random main_v1.py --save-worst 5
    python test.py --games 40 --seed 7           # reproducible; paired seat-swap on one map
    python test.py --games 40 --seed -1          # fresh random env seed per game
    python test.py --competition --games 10      # all agents, ladder-like matches
"""
import argparse
import ast
import gzip
import json
import math
import random
import statistics
from pathlib import Path

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
COMPETITION_CONFIG = {
    "episodeSteps": 720,
    "actTimeout": 1,
    "runTimeout": 1200,
    "startingMoney": 3000,
    "turnsPerDay": 24,
    "maxMarketOrdersPerTurn": 10,
}


def discover_agents(candidate="main.py"):
    """Find runnable repository agents without maintaining another stale list."""
    candidate_path = (ROOT / candidate).resolve()
    found = []
    for path in sorted(ROOT.rglob("*.py")):
        relative = path.relative_to(ROOT)
        if (path.name.startswith("_") or path.resolve() == candidate_path or
                any(part.startswith(".") for part in relative.parts)):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(path))
            if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
                       node.name == "agent" for node in tree.body):
                continue
        except (OSError, SyntaxError):
            continue
        found.append(relative.as_posix())
    # Built-ins are useful controls and are part of the actual environment.
    return found + ["starter", "random", "pass"]


def money_from_final(final):
    values = []
    for i, state in enumerate(final):
        try:
            values.append(float(state.observation.farms[i].money))
        except Exception:
            values.append(float(state.reward or 0))
    return values


_MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def _unit_actions(action):
    if not isinstance(action, dict):
        return []
    out = []
    fa = action.get("farmer")
    if isinstance(fa, list) and fa:
        out.append(fa[0])
    for h in action.get("hands", []) or []:
        if isinstance(h, list) and h:
            out.append(h[0])
    return out


def analyze_replay(replay, seat):
    """Per-game diagnostics for the PLAN_300K multipliers: money trajectory,
    sell cadence, movement share, terminal unsold inventory."""
    steps = replay.get("steps", []) if isinstance(replay, dict) else []
    if not steps:
        return {}
    turns_per_day = 24
    moves = non_pass = 0
    sell_units = 0
    empty_slot_turns = 0
    money_by_day = {}
    for i, per in enumerate(steps):
        if seat >= len(per):
            continue
        st = per[seat]
        act = st.get("action", {}) if isinstance(st, dict) else {}
        for a in _unit_actions(act):
            if a == "PASS":
                continue
            non_pass += 1
            if a in _MOVES:
                moves += 1
        mkt = act.get("market", []) if isinstance(act, dict) else []
        turn_sell = 0
        for order in mkt or []:
            if isinstance(order, list) and order and order[0] == "SELL" and len(order) >= 3:
                try:
                    turn_sell += int(order[2])
                except (TypeError, ValueError):
                    pass
        sell_units += turn_sell
        # a turn from mid-game on with produce presumably available but < 10 orders
        day = i // turns_per_day
        if 8 <= day < 29 and len(mkt or []) < 10:
            empty_slot_turns += 1
        farms = (steps[i][0].get("observation", {}) or {}).get("farms")
        if farms and seat < len(farms):
            money_by_day[day] = float(farms[seat].get("money", 0))
    # terminal unsold: shed + unit inventories at the reward-lock step
    lock = steps[min(len(steps) - 1, 718)]
    unsold = 0
    if seat < len(lock):
        priv = (lock[seat].get("observation", {}) or {}).get("private", {}) or {}
        for v in (priv.get("shed", {}) or {}).values():
            try:
                unsold += max(0, int(v))
            except (TypeError, ValueError):
                pass
        for inv in priv.get("inventories", []) or []:
            for v in (inv or {}).values():
                try:
                    unsold += max(0, int(v))
                except (TypeError, ValueError):
                    pass
    return {
        "move_share": moves / non_pass if non_pass else 0.0,
        "sell_per_day": sell_units / 30.0,
        "empty_slot_turns": empty_slot_turns,
        "terminal_unsold": unsold,
        "coins_d10": money_by_day.get(10, 0.0),
        "coins_d20": money_by_day.get(20, 0.0),
        "coins_d29": money_by_day.get(29, money_by_day.get(max(money_by_day) if money_by_day else 0, 0.0)),
    }


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def run_game(candidate, opponent, candidate_seat, seed=None, keep_replay=False,
             save_dir=None, save_tag=None, realistic=False):
    """Play one game. If ``save_dir`` is given, the full replay (gzipped) and the
    per-step per-agent stdout/stderr logs are written there before the env is
    dropped -- ``<tag>.replay.json.gz`` + ``<tag>.logs.json``. The replay is kept
    in RAM (``row["replay"]``) only when ``keep_replay`` is set."""
    agents = [candidate, opponent] if candidate_seat == 0 else [opponent, candidate]
    config = dict(COMPETITION_CONFIG) if realistic else {"episodeSteps": 720}
    if seed is not None:
        config["seed"] = seed
    # Kaggle swallows agent exceptions; realistic mode deliberately reproduces
    # that behaviour. The normal regression mode keeps debug traces visible.
    env = make("kaggriculture", configuration=config, debug=not realistic)
    env.run(agents)
    final = env.steps[-1]
    statuses = [str(s.status) for s in final]
    money = money_from_final(final)
    c_money = money[candidate_seat]
    o_money = money[1 - candidate_seat]
    result = 1 if c_money > o_money else (-1 if c_money < o_money else 0)
    replay = env.toJSON()
    # resolve_episode_seed scrubs configuration["seed"] and stows it on env.info
    used_seed = env.info.get("seed", seed) if isinstance(env.info, dict) else seed
    diag = analyze_replay(replay, candidate_seat)

    replay_path = logs_path = None
    if save_dir is not None:
        out = Path(save_dir)
        out.mkdir(parents=True, exist_ok=True)
        tag = save_tag or f"game_seed{used_seed}"
        replay_path = out / f"{tag}.replay.json.gz"
        with gzip.open(replay_path, "wt", encoding="utf-8") as fh:
            json.dump(replay, fh, separators=(",", ":"))
        # env.logs (debug=True) is a per-step list of [{duration,stdout,stderr}]
        # per seat -- the local analogue of the Kaggle agent-*-logs.json files.
        logs = getattr(env, "logs", None) or []
        logs_path = out / f"{tag}.logs.json"
        with open(logs_path, "w", encoding="utf-8") as fh:
            json.dump(logs, fh, separators=(",", ":"))

    row = {
        "result": result,
        "candidate_money": c_money,
        "opponent_money": o_money,
        "difference": c_money - o_money,
        "statuses": statuses,
        "seed": used_seed,
        # a full replay is ~10-30 MB; retaining one per game across every
        # opponent OOMs a 16 GB box on a 3-opponent run. Keep it only when
        # --save-worst asked for it.
        "replay": replay if keep_replay else None,
        "replay_path": str(replay_path) if replay_path else None,
        "logs_path": str(logs_path) if logs_path else None,
        "diag": diag,
    }
    del env, final, replay
    return row


def summarize(rows):
    wins = sum(r["result"] > 0 for r in rows)
    ties = sum(r["result"] == 0 for r in rows)
    losses = sum(r["result"] < 0 for r in rows)
    coins = [r["candidate_money"] for r in rows]
    diffs = [r["difference"] for r in rows]
    errors = sum(any(status != "DONE" for status in r["statuses"]) for r in rows)
    diags = [r.get("diag") or {} for r in rows]

    def dmean(key):
        vals = [d[key] for d in diags if key in d]
        return statistics.fmean(vals) if vals else 0.0

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
        "min_coins": min(coins) if coins else 0,
        "mean_difference": statistics.fmean(diffs) if diffs else 0,
        "errors": errors,
        "move_share": dmean("move_share"),
        "sell_per_day": dmean("sell_per_day"),
        "empty_slot_turns": dmean("empty_slot_turns"),
        "terminal_unsold": dmean("terminal_unsold"),
        "coins_d10": dmean("coins_d10"),
        "coins_d20": dmean("coins_d20"),
        "coins_d29": dmean("coins_d29"),
    }


def print_summary(opponent, summary):
    print(
        f"{opponent:16} games={summary['games']:4d} "
        f"W/T/L={summary['wins']}/{summary['ties']}/{summary['losses']} "
        f"score={summary['score_rate']:.1%} "
        f"coins mean/median/p10/min={summary['mean_coins']:.0f}/"
        f"{summary['median_coins']:.0f}/{summary['p10_coins']:.0f}/{summary['min_coins']:.0f} "
        f"diff={summary['mean_difference']:+.0f} errors={summary['errors']}"
    )
    print(
        f"{'':16} move%={summary['move_share']:.0%} "
        f"sell/day={summary['sell_per_day']:.0f} "
        f"emptyslots={summary['empty_slot_turns']:.0f} "
        f"unsold={summary['terminal_unsold']:.0f} "
        f"coins d10/d20/d29={summary['coins_d10']:.0f}/"
        f"{summary['coins_d20']:.0f}/{summary['coins_d29']:.0f}"
    )


def save_worst(rows, opponent, count, output_dir):
    if count <= 0:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(opponent).stem.replace(" ", "_")
    for rank, row in enumerate(sorted(rows, key=lambda r: r["difference"])[:count], 1):
        seed_tag = f"_seed{row['seed']}" if row.get("seed") is not None else ""
        target = output_dir / f"{safe_name}_worst_{rank}{seed_tag}.json"
        with target.open("w", encoding="utf-8") as handle:
            json.dump(row["replay"], handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="main.py")
    parser.add_argument("--incumbent", default="agents/main_v6.py")
    parser.add_argument("--opponents", nargs="+")
    parser.add_argument("--suite", action="store_true",
                        help="Benchmark against the archetype bots in bots/ "
                             "(wheatflood, animalfarm, animalfactory_v2, melonmono, "
                             "premium) + starter. These model the ladder strategies "
                             "that beat us; see PLAN_3000_v4.md.")
    parser.add_argument("--gate", action="store_true",
                        help="The PLAN_LADDER_ECON.md s4 promote gate: the strong "
                             "animal-factory proxy + animalfarm + main_v4 + main.py "
                             "+ wheatflood + premium + starter. Promote an economy "
                             "change only if score-rate >= 45%% vs BOTH animal "
                             "opponents and OVERALL mean/p10 are non-worse.")
    parser.add_argument("--all-agents", action="store_true",
                        help="Recursively discover every repository Python file "
                             "with agent(), plus the environment built-ins.")
    parser.add_argument("--realistic", action="store_true",
                        help="Use stock competition limits, Kaggle-style error "
                             "handling, random seats, and independent 9-digit seeds.")
    parser.add_argument("--competition", action="store_true",
                        help="Shortcut for --all-agents --realistic.")
    parser.add_argument("--games", type=int, default=20,
                        help="Games per opponent; regression mode alternates seats.")
    parser.add_argument("--seed", type=int, default=10000000,
                        help="Base episode seed. Each seat-swapped pair of games "
                             "shares one map seed so the candidate plays both "
                             "seats of an identical world; pass a negative value "
                             "to let the env roll a fresh random seed per game.")
    parser.add_argument("--pick-seed", type=int,
                        help="Make realistic seat/episode-seed draws reproducible.")
    parser.add_argument("--save-worst", type=int, default=0)
    parser.add_argument("--replay-dir", default="benchmark_replays")
    args = parser.parse_args()

    suite = [
        "bots/bot_wheatflood.py", "bots/bot_animalfarm.py",
        "bots/bot_animalfactory_v2.py", "bots/bot_melonmono.py",
        "bots/bot_premium.py", "starter",
    ]
    gate = [
        "bots/bot_animalfactory_v2.py", "bots/bot_animalfarm.py",
        "agents/main_v4.py", "agents/main_v6.py", "bots/bot_wheatflood.py",
        "bots/bot_premium.py", "starter",
    ]
    use_all = args.all_agents or args.competition
    realistic = args.realistic or args.competition
    opponents = args.opponents or (
        discover_agents(args.candidate) if use_all else
        gate if args.gate else
        suite if args.suite else
        ["starter", "random", args.incumbent])
    if args.games < (1 if realistic else 2):
        parser.error("--games must be >= 1 in competition mode, otherwise >= 2")

    all_rows = []
    rng = random.Random(args.pick_seed)
    seed_note = ("independent 9-digit seeds" if realistic else
                 "random/game" if args.seed < 0 else
                 f"base {args.seed} (shared per seat-pair)")
    mode = "competition" if realistic else "regression"
    print(f"Candidate: {args.candidate} | opponents: {len(opponents)} | "
          f"games/opponent: {args.games} | mode: {mode} | seed: {seed_note}")
    for opponent in opponents:
        rows = []
        for game_index in range(args.games):
            if realistic:
                seat = rng.randint(0, 1)
                game_seed = rng.randint(100_000_000, 999_999_999)
            else:
                seat = game_index % 2
                game_seed = None if args.seed < 0 else args.seed + game_index // 2
            row = run_game(args.candidate, opponent, seat, seed=game_seed,
                           keep_replay=args.save_worst > 0,
                           realistic=realistic)
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
