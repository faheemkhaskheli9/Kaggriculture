"""Build a compact strategic-policy dataset from downloaded top-player replays.

Only farms whose agent name appears in ``top10_ladder/manifest.csv`` are used;
ordinary opponents in those episodes are excluded. Output is JSONL so training
and analysis can stream it without loading the 700+ MB replay collection.

Usage:
    python tools/extract_top_policy.py
    python tools/extract_top_policy.py --output ml/artifacts/top_policy.jsonl
"""
import argparse
import csv
import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELD_OPS = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
    "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE", "PICKUP",
    "PLACE", "DROP", "NORTH", "SOUTH", "EAST", "WEST", "PASS",
}


def farm_counts(farm):
    crops, animals = Counter(), Counter()
    weeds = empty = structures = 0
    for row in farm.get("tiles") or []:
        for tile in row:
            if tile is None:
                empty += 1
            elif isinstance(tile, dict):
                if tile.get("kind") == "PLANT":
                    crops[tile.get("crop")] += 1
                elif tile.get("kind") == "WEED":
                    weeds += 1
                elif tile.get("kind") in ("COOP", "PASTURE"):
                    structures += 1
                    if tile.get("animal"):
                        animals[tile["animal"]] += 1
    return {
        "crops": dict(crops), "animals": dict(animals), "weeds": weeds,
        "empty": empty, "structures": structures,
    }


def compact_inventory(values):
    return {key: value for key, value in (values or {}).items() if value}


def action_labels(action):
    action = action or {}
    field = Counter()
    farmer = action.get("farmer")
    if isinstance(farmer, list) and farmer and farmer[0] in FIELD_OPS:
        field[farmer[0]] += 1
    for hand in action.get("hands") or []:
        if isinstance(hand, list) and hand and hand[0] in FIELD_OPS:
            field[hand[0]] += 1
    market = [order for order in (action.get("market") or [])
              if isinstance(order, list) and order]
    return {"field_ops": dict(field), "market_orders": market}


def history_snapshot(history, step_index):
    last_seen = history["last_seen"]
    return {
        "market_counts": dict(history["market_counts"]),
        "market_quantities": dict(history["market_quantities"]),
        "field_counts": dict(history["field_counts"]),
        "turns_since": {
            op: (step_index - last_seen[op] if op in last_seen else 999)
            for op in ("HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL",
                       "BUY_PRODUCT", "SELL")
        },
        "previous_day_money": history.get("previous_day_money"),
        "previous_day_plants": history.get("previous_day_plants"),
        "previous_day_animals": history.get("previous_day_animals"),
    }


def update_history(history, row, step_index):
    for op, count in row["labels"]["field_ops"].items():
        history["field_counts"][op] += count
    for order in row["labels"]["market_orders"]:
        op = order[0]
        history["market_counts"][op] += 1
        history["last_seen"][op] = step_index
        quantity = order[2] if len(order) > 2 and isinstance(order[2], (int, float)) else 1
        history["market_quantities"][op] += quantity
        if len(order) > 1:
            history["market_quantities"][f"{op}:{order[1]}"] += quantity
    if row["hour"] == 0:
        history["previous_day_money"] = row["money"]
        history["previous_day_plants"] = total_counts(row["farm"]["crops"])
        history["previous_day_animals"] = total_counts(row["farm"]["animals"])


def total_counts(mapping):
    return sum((mapping or {}).values())


def build_row(replay_file, episode_id, step_index, seat, agent_name, state, history):
    obs = state["observation"]
    farms = obs["farms"]
    me, opponent = farms[seat], farms[1 - seat]
    private = obs.get("private") or {}
    carried = Counter()
    for inventory in private.get("inventories") or []:
        carried.update(inventory or {})
    return {
        "episode_id": episode_id, "replay": replay_file.name,
        "step": step_index, "seat": seat, "agent": agent_name,
        "day": obs.get("day"), "hour": obs.get("hour"),
        "money": me.get("money"), "hands": len(me.get("hands") or []),
        "quadrants": len(me.get("unlocked_quadrants") or []),
        "farm": farm_counts(me), "opponent": farm_counts(opponent),
        "opponent_money": opponent.get("money"),
        "shed": compact_inventory(private.get("shed")),
        "seeds": compact_inventory(private.get("seeds")),
        "carried": compact_inventory(carried),
        "market_prices": obs.get("market", {}).get("prices", {}),
        "market_inventory": obs.get("market", {}).get("inventory", {}),
        "town_shops": obs.get("town", {}).get("unlocked_shops", []),
        "history": history_snapshot(history, step_index),
        "labels": action_labels(state.get("action")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="top10_ladder/manifest.csv")
    parser.add_argument("--glob", default="top10_ladder/replays/*.json")
    parser.add_argument("--output", default="ml/artifacts/top_policy.jsonl")
    parser.add_argument("--summary", default="ml/artifacts/top_policy_summary.json")
    args = parser.parse_args()

    manifest_path = ROOT / args.manifest
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    top_names = {row["team"].strip().casefold() for row in manifest}
    top_by_episode = {}
    for row in manifest:
        top_by_episode.setdefault(str(row["episode_id"]), set()).add(
            row["team"].strip().casefold())

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(path) for path in glob.glob(str(ROOT / args.glob)))
    rows = farms = strategic_rows = 0
    agents = Counter()
    market_ops = Counter()
    field_ops = Counter()
    used_episodes = set()
    with output.open("w", encoding="utf-8") as sink:
        for replay_file in files:
            episode_id = replay_file.name.split("-")[1]
            wanted = top_by_episode.get(episode_id, top_names)
            replay = json.loads(replay_file.read_text(encoding="utf-8"))
            names = [str(agent.get("Name", "")).strip() for agent in replay["info"]["Agents"]]
            seats = [seat for seat, name in enumerate(names) if name.casefold() in wanted]
            if not seats:
                continue
            used_episodes.add(episode_id)
            farms += len(seats)
            histories = {
                seat: {
                    "market_counts": Counter(), "market_quantities": Counter(),
                    "field_counts": Counter(), "last_seen": {},
                }
                for seat in seats
            }
            for step_index, step in enumerate(replay["steps"]):
                for seat in seats:
                    row = build_row(replay_file, episode_id, step_index, seat,
                                    names[seat], step[seat], histories[seat])
                    sink.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
                    update_history(histories[seat], row, step_index)
                    rows += 1
                    agents[names[seat]] += 1
                    labels = row["labels"]
                    field_ops.update(labels["field_ops"])
                    for order in labels["market_orders"]:
                        market_ops[order[0]] += 1
                    if labels["market_orders"]:
                        strategic_rows += 1

    summary = {
        "source_manifest": args.manifest, "replay_files_seen": len(files),
        "episodes_used": len(used_episodes), "top_farms": farms, "rows": rows,
        "rows_with_market_decision": strategic_rows,
        "agents": dict(agents), "market_ops": dict(market_ops),
        "field_ops": dict(field_ops), "output": args.output,
    }
    summary_path = ROOT / args.summary
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    # Windows' default console encoding may not represent international team names.
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
