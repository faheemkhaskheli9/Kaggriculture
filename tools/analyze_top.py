"""Tear down the top-10 ladder replays (top10_ladder/replays/*.json).

Per game, per farm, extracts: quadrant-unlock timing, hand-count growth,
crop/animal mix over time, money curve, movement share of hand-actions, and
endgame liquidation pattern. Prints an aggregate summary; use --detail for
a per-game dump.

    python tools/analyze_top.py
    python tools/analyze_top.py --detail
"""
import argparse
import glob
import json
import statistics as st
from collections import Counter, defaultdict

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
STEPS_PER_DAY = 24


def analyze_farm(steps, farm_idx):
    """steps: the full replay 'steps' list. Returns a dict of extracted series
    for farm_idx (0 or 1), reading that farm's own perspective for private
    data (hand actions come from that agent's own action log)."""
    money_by_day = {}
    quad_by_day = {}
    hands_by_day = {}
    capacity_by_day = {}
    crop_counts_by_day = {}   # day -> Counter(crop -> tile count)
    animal_counts_by_day = {}  # day -> Counter(species -> count)
    weed_by_day = {}
    move_tokens = 0
    total_hand_tokens = 0
    hand_token_counts = Counter()
    final_money = None

    for st_entry in steps:
        agent_step = st_entry[farm_idx]
        obs = agent_step["observation"]
        day = obs["day"]
        hour = obs["hour"]
        farm = obs["farms"][farm_idx]

        # hands are re-hired each day, so the count is 0 at hour==0 before
        # any HIRE resolves that day -- track the day's max instead.
        hands_by_day[day] = max(hands_by_day.get(day, 0), len(farm["hands"]))

        if hour == 0:
            money_by_day[day] = farm["money"]
            quad_by_day[day] = len(farm["unlocked_quadrants"])
            cap = sum(
                1 for row in farm["tiles"] for t in row if t != "LOCKED"
            )
            capacity_by_day[day] = cap
            crops = Counter()
            animals = Counter()
            weeds = 0
            for row in farm["tiles"]:
                for t in row:
                    if not isinstance(t, dict):
                        continue
                    if t.get("kind") == "PLANT":
                        crops[t.get("crop")] += 1
                    elif t.get("kind") == "WEED":
                        weeds += 1
                    elif t.get("kind") in ("PASTURE", "COOP") and t.get("animal"):
                        animals[t["animal"]] += 1
            crop_counts_by_day[day] = crops
            animal_counts_by_day[day] = animals
            weed_by_day[day] = weeds

        final_money = farm["money"]
        act = agent_step["action"]
        for h in act.get("hands", []):
            if not h:
                continue
            tok = h[0]
            hand_token_counts[tok] += 1
            total_hand_tokens += 1
            if tok in MOVES:
                move_tokens += 1

    return {
        "money_by_day": money_by_day,
        "quad_by_day": quad_by_day,
        "hands_by_day": hands_by_day,
        "capacity_by_day": capacity_by_day,
        "crop_counts_by_day": crop_counts_by_day,
        "animal_counts_by_day": animal_counts_by_day,
        "weed_by_day": weed_by_day,
        "move_share": (move_tokens / total_hand_tokens) if total_hand_tokens else 0.0,
        "hand_token_counts": hand_token_counts,
        "final_money": final_money,
    }


def first_day_at_least(by_day, n):
    for day in sorted(by_day):
        if by_day[day] >= n:
            return day
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="top10_ladder/replays/*.json")
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(args.glob))
    print(f"{len(files)} replay files")

    all_farm_results = []  # (file, farm_idx, result)
    for fp in files:
        d = json.load(open(fp, encoding="utf-8"))
        steps = d["steps"]
        for farm_idx in (0, 1):
            r = analyze_farm(steps, farm_idx)
            all_farm_results.append((fp, farm_idx, r))

    # ---- aggregate: quadrant-unlock timing ----
    q2_days, q3_days, q4_days = [], [], []
    for fp, fi, r in all_farm_results:
        d2 = first_day_at_least(r["quad_by_day"], 2)
        d3 = first_day_at_least(r["quad_by_day"], 3)
        d4 = first_day_at_least(r["quad_by_day"], 4)
        if d2 is not None:
            q2_days.append(d2)
        if d3 is not None:
            q3_days.append(d3)
        if d4 is not None:
            q4_days.append(d4)

    def fmt_stats(xs, label):
        if not xs:
            print(f"  {label}: never reached ({len(all_farm_results)} farms)")
            return
        print(
            f"  {label}: reached by {len(xs)}/{len(all_farm_results)} farms | "
            f"median day {st.median(xs):.0f}, mean {st.mean(xs):.1f}, "
            f"min {min(xs)}, max {max(xs)}"
        )

    print("\n=== Quadrant unlock timing ===")
    fmt_stats(q2_days, "2nd quadrant")
    fmt_stats(q3_days, "3rd quadrant")
    fmt_stats(q4_days, "4th quadrant (all)")

    # ---- hands hired by day 5/10/15/20 ----
    print("\n=== Hands hired (crew size) ===")
    for checkpoint in (5, 10, 15, 20, 29):
        vals = [
            r["hands_by_day"].get(checkpoint)
            for _, _, r in all_farm_results
            if checkpoint in r["hands_by_day"]
        ]
        if vals:
            print(
                f"  day {checkpoint}: median {st.median(vals):.0f}, "
                f"mean {st.mean(vals):.1f}, min {min(vals)}, max {max(vals)}"
            )

    # ---- field capacity (unlocked tiles) by day ----
    print("\n=== Field capacity (unlocked, non-LOCKED tiles) ===")
    for checkpoint in (5, 10, 15, 20, 29):
        vals = [
            r["capacity_by_day"].get(checkpoint)
            for _, _, r in all_farm_results
            if checkpoint in r["capacity_by_day"]
        ]
        if vals:
            print(
                f"  day {checkpoint}: median {st.median(vals):.0f}, "
                f"mean {st.mean(vals):.1f}, min {min(vals)}, max {max(vals)}"
            )

    # ---- money curve ----
    print("\n=== Money curve ===")
    for checkpoint in (2, 5, 10, 15, 20, 25, 29):
        vals = [
            r["money_by_day"].get(checkpoint)
            for _, _, r in all_farm_results
            if checkpoint in r["money_by_day"]
        ]
        if vals:
            print(
                f"  day {checkpoint}: median {st.median(vals):.0f}, "
                f"mean {st.mean(vals):.1f}, min {min(vals):.0f}, max {max(vals):.0f}"
            )
    finals = [r["final_money"] for _, _, r in all_farm_results if r["final_money"] is not None]
    if finals:
        print(
            f"  FINAL: median {st.median(finals):.0f}, mean {st.mean(finals):.1f}, "
            f"min {min(finals):.0f}, max {max(finals):.0f}"
        )

    # ---- movement share ----
    print("\n=== Movement share of hand-actions ===")
    shares = [r["move_share"] for _, _, r in all_farm_results if r["move_share"]]
    if shares:
        print(
            f"  median {st.median(shares)*100:.1f}%, mean {st.mean(shares)*100:.1f}%, "
            f"min {min(shares)*100:.1f}%, max {max(shares)*100:.1f}%"
        )
    combined = Counter()
    for _, _, r in all_farm_results:
        combined.update(r["hand_token_counts"])
    total = sum(combined.values())
    print("  action-token distribution (all farms, all games):")
    for tok, cnt in combined.most_common():
        print(f"    {tok:20s} {cnt:7d}  ({100*cnt/total:.1f}%)")

    # ---- crop mix at day 20 ----
    print("\n=== Crop mix at day 20 (tile counts, summed across farms) ===")
    crop_total = Counter()
    for _, _, r in all_farm_results:
        crop_total.update(r["crop_counts_by_day"].get(20, {}))
    total_crops = sum(crop_total.values())
    for crop, cnt in crop_total.most_common():
        print(f"    {crop:12s} {cnt:6d}  ({100*cnt/total_crops:.1f}%)" if total_crops else "")

    # ---- animal mix at day 20 ----
    print("\n=== Animal mix at day 20 (summed across farms) ===")
    animal_total = Counter()
    for _, _, r in all_farm_results:
        animal_total.update(r["animal_counts_by_day"].get(20, {}))
    total_animals = sum(animal_total.values())
    for sp, cnt in animal_total.most_common():
        pct = f" ({100*cnt/total_animals:.1f}%)" if total_animals else ""
        print(f"    {sp:12s} {cnt:6d}{pct}")

    # ---- weeds late-game ----
    print("\n=== Weeds at day 25 ===")
    vals = [r["weed_by_day"].get(25) for _, _, r in all_farm_results if 25 in r["weed_by_day"]]
    if vals:
        print(f"  median {st.median(vals):.0f}, mean {st.mean(vals):.1f}, max {max(vals)}")

    if args.detail:
        print("\n=== Per-game detail ===")
        for fp, fi, r in all_farm_results:
            print(
                f"{fp} farm{fi}: final_money={r['final_money']:.0f} "
                f"q@d10={r['quad_by_day'].get(10)} hands@d10={r['hands_by_day'].get(10)} "
                f"cap@d10={r['capacity_by_day'].get(10)} move%={r['move_share']*100:.0f}"
            )


if __name__ == "__main__":
    main()
