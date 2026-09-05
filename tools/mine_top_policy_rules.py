"""Mine explicit BUY_LAND / BUY_ANIMAL timing-value rules from top-player replays.

`tools/benchmark_top_policy.py` showed a categorical classifier cannot learn
BUY_LAND (4.9% F1) or BUY_ANIMAL (6.5% F1) — they are rare, high-value, and
context-dependent. Per `docs/IMPACT_RANKED_LEADERBOARD_PLAN.md` Workstream A,
the replacement approach is to mine the preconditions of every real top-player
purchase directly and turn them into explicit thresholds, instead of training
a classifier on them. Also reconstructs the day-by-day herd/quadrant
trajectory of the top farms, since "opponent commonly reaches 10-19 animals
while ours reaches 6-11" is the #1 ranked lever in that plan.

Usage:
    python tools/mine_top_policy_rules.py
    python tools/mine_top_policy_rules.py --dataset ml/artifacts/top_policy.jsonl
"""
import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANIMAL_COST = {"COW": 300, "SHEEP": 200, "CHICKEN": 100}  # knowledge-base/02
LAND_COST = {1: 1000, 2: 2000, 3: 4000}  # quadrants-owned-before-buy -> price


def total(mapping):
    return sum((mapping or {}).values())


def pct(values, q):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def summarize(values):
    if not values:
        return None
    return {
        "n": len(values), "min": min(values), "p25": pct(values, 0.25),
        "median": statistics.median(values), "p75": pct(values, 0.75),
        "max": max(values),
    }


def load_rows(dataset):
    with (ROOT / dataset).open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def mine_land(rows):
    """BUY_LAND orders include failed/unaffordable attempts (silent no-ops per
    the engine rules — e.g. a farm queuing BUY_LAND at $93 then again at $8,
    needing $1000). Detect *successful* buys by watching `quadrants` actually
    increase between consecutive rows of the same farm, in step order, rather
    than trusting every emitted order label.
    """
    attempted = 0
    by_farm = defaultdict(list)
    for row in rows:
        if any(order and order[0] == "BUY_LAND" for order in row["labels"]["market_orders"]):
            attempted += 1
        by_farm[(row["episode_id"], row["seat"], row["agent"])].append(row)

    events = []
    for (episode, seat, agent), farm_rows in by_farm.items():
        farm_rows.sort(key=lambda r: r["step"])
        for prev, curr in zip(farm_rows, farm_rows[1:]):
            if curr["quadrants"] > prev["quadrants"]:
                before_q = prev["quadrants"]
                events.append({
                    "episode": episode, "agent": agent, "seat": seat,
                    "step": prev["step"],
                    "transition": f"{before_q}->{before_q + 1}",
                    "day": prev["day"], "hour": prev["hour"],
                    "money": prev["money"], "hands": prev["hands"],
                    "plants": total(prev["farm"]["crops"]),
                    "price": LAND_COST.get(before_q),
                    "cushion": (prev["money"] - LAND_COST[before_q])
                               if before_q in LAND_COST else None,
                    "opp_plants": total(prev["opponent"]["crops"]),
                })
    by_transition = defaultdict(list)
    for event in events:
        by_transition[event["transition"]].append(event)
    report = {}
    for transition, group in sorted(by_transition.items()):
        report[transition] = {
            "day": summarize([e["day"] for e in group]),
            "hour": summarize([e["hour"] for e in group]),
            "money_at_buy": summarize([e["money"] for e in group]),
            "cushion_over_price": summarize(
                [e["cushion"] for e in group if e["cushion"] is not None]),
            "hands_at_buy": summarize([e["hands"] for e in group]),
            "plants_at_buy": summarize([e["plants"] for e in group]),
            "agents": dict(Counter(e["agent"] for e in group)),
        }
    return events, attempted, report


def mine_animal(rows):
    """BUY_ANIMAL orders also include unaffordable attempts, and — like
    BUY_LAND — the replay's per-row `action` is the decision that *produced*
    that same row's observation (computed from the previous row's state), not
    one about to be applied next. Confirmed against the raw replay: a row's
    own `money`/`hands` already reflect that row's own action having landed.
    So pair each BUY_ANIMAL label with the *previous* row's state (what the
    agent actually saw when it decided), not its own row's post-purchase
    state. Approximate a successful buy as one the previous state could
    afford in full — this ignores the shed-full (cap 100) failure mode and
    same-turn slot ordering ahead of the animal order, so treat counts as an
    upper bound, not exact.
    """
    events = []
    attempted = failed_afford = 0
    by_farm = defaultdict(list)
    for row in rows:
        by_farm[(row["episode_id"], row["seat"], row["agent"])].append(row)

    for (episode, seat, agent), farm_rows in by_farm.items():
        farm_rows.sort(key=lambda r: r["step"])
        for prev, curr in zip(farm_rows, farm_rows[1:]):
            structures = prev["farm"]["structures"]
            herd_before = total(prev["farm"]["animals"])
            for order in curr["labels"]["market_orders"]:
                if not (order and order[0] == "BUY_ANIMAL"):
                    continue
                attempted += 1
                animal = order[1] if len(order) > 1 else None
                qty = order[2] if len(order) > 2 else 1
                cost = ANIMAL_COST.get(animal, 0) * (qty or 1)
                if prev["money"] < cost:
                    failed_afford += 1
                    continue
                events.append({
                    "episode": episode, "agent": agent, "seat": seat,
                    "step": prev["step"],
                    "animal": animal, "qty": qty,
                    "day": prev["day"], "hour": prev["hour"],
                    "money": prev["money"], "hands": prev["hands"],
                    "structures_before": structures,
                    "herd_before": herd_before,
                    "cash_floor_after": prev["money"] - cost,
                    "opp_animals": total(prev["opponent"]["animals"]),
                })
    by_animal = defaultdict(list)
    for event in events:
        by_animal[event["animal"]].append(event)
    report = {}
    for animal, group in sorted(by_animal.items()):
        first_buys = [e for e in group if e["herd_before"] == 0]
        report[animal] = {
            "n_orders": len(group),
            "total_units": sum(e["qty"] or 1 for e in group),
            "day_of_first_buy": summarize([e["day"] for e in first_buys]),
            "day_all_buys": summarize([e["day"] for e in group]),
            "batch_qty": summarize([e["qty"] or 1 for e in group]),
            "money_at_buy": summarize([e["money"] for e in group]),
            "cash_floor_after": summarize([e["cash_floor_after"] for e in group]),
            "hands_at_buy": summarize([e["hands"] for e in group]),
            "structures_before": summarize([e["structures_before"] for e in group]),
            "herd_before": summarize([e["herd_before"] for e in group]),
            "agents": dict(Counter(e["agent"] for e in group)),
        }
    return events, attempted, failed_afford, report


def herd_and_land_trajectory(rows):
    """Day-by-day median herd size / quadrant count, sampled at hour==0."""
    by_day = defaultdict(lambda: {"herd": [], "quadrants": [], "plants": []})
    seen = set()
    for row in rows:
        if row["hour"] != 0:
            continue
        key = (row["episode_id"], row["seat"], row["day"])
        if key in seen:
            continue
        seen.add(key)
        by_day[row["day"]]["herd"].append(total(row["farm"]["animals"]))
        by_day[row["day"]]["quadrants"].append(row["quadrants"])
        by_day[row["day"]]["plants"].append(total(row["farm"]["crops"]))
    trajectory = {}
    for day, values in sorted(by_day.items()):
        trajectory[day] = {
            "n_farm_days": len(values["herd"]),
            "herd_median": statistics.median(values["herd"]),
            "quadrants_median": statistics.median(values["quadrants"]),
            "plants_median": statistics.median(values["plants"]),
        }
    return trajectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="ml/artifacts/top_policy.jsonl")
    parser.add_argument("--output", default="ml/artifacts/top_policy_rules.json")
    args = parser.parse_args()

    rows = list(load_rows(args.dataset))
    land_events, land_attempted, land_report = mine_land(rows)
    animal_events, animal_attempted, animal_failed, animal_report = mine_animal(rows)
    trajectory = herd_and_land_trajectory(rows)

    result = {
        "dataset": args.dataset, "rows": len(rows),
        "buy_land": {
            "orders_attempted": land_attempted,
            "orders_succeeded": len(land_events),
            "by_transition": land_report,
        },
        "buy_animal": {
            "orders_attempted": animal_attempted,
            "orders_failed_unaffordable": animal_failed,
            "orders_succeeded_approx": len(animal_events),
            "by_animal": animal_report,
        },
        "day_trajectory": trajectory,
    }
    output = ROOT / args.output
    output.write_text(json.dumps(result, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str, ensure_ascii=True))


if __name__ == "__main__":
    main()
