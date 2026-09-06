"""Cross-build cash-crater teardown for a ladder submission's LOSSES.

Every loss on 56034847 / 56039865 / 56044961 / 56050226 shares one shape: our
day-10 money is a few hundred to ~1.5k, it *drops* by day 15 instead of
compounding, and the opponent breaks 10-30k in the same window. This tool makes
that shape measurable per game:

  * bucket each loss by final coin deficit -- close (<10k) / recoverable
    (10-30k) / blowout (>30k). Only close+recoverable are realistically
    flippable by an economy change.
  * per day 0-16: our money, day-delta, opp money, and exact discretionary
    spend by category ($seed / $anim / $land by quadrant tier / #hires).
  * "crater onset" = first day in 6..15 where our money falls below FLOOR and
    stays below it through day 15.
  * "biggest early spend" = largest single-day discretionary $ outlay in
    days 0-6 -- the first-irreversible-spend candidate the plan asks for.
  * aggregate: bucket -> n, mean onset day, mean day0 / day0-2 spend split.

    python tools/trace_crater.py <SUB_REF> [<SUB_REF> ...] [--floor 1500] [--n 40]

Reuses the replay plumbing conventions from tools/trace_cashflow.py.
"""
import json, csv, collections, os, argparse

IDX = "episodes/index.csv"
ME_NAMES = {"faheem", "faheemkhaskheli9", "faheem khaskheli"}
CATS = ("HIRE", "BUY_LAND", "BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT", "SELL")
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
LAND_TIER = [1000, 2000, 4000]   # cost of the 2nd / 3rd / 4th quadrant


def load_index():
    m = {}
    with open(IDX, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m[row["episode_id"]] = row
    return m


def money(steps, i, seat):
    try:
        return steps[i][seat]["observation"]["farms"][seat]["money"]
    except Exception:
        return None


def fib_cost(n):
    """Total coins for the n HIREs of a day (each costs fib(k), k=1..n, resets daily)."""
    a, b, tot = 1, 1, 0
    for _ in range(n):
        tot += a
        a, b = b, a + b
    return tot


def day_spend(steps, seat, day, land_tier_state):
    cnt = collections.Counter()
    spend = collections.Counter()
    lo, hi = day * 24, min(day * 24 + 24, len(steps))
    for i in range(lo, hi):
        per = steps[i]
        if seat >= len(per):
            continue
        a = per[seat].get("action") or {}
        for o in a.get("market") or []:
            if not (isinstance(o, list) and o):
                continue
            op = o[0]
            cnt[op] += 1
            if op == "BUY_SEED" and len(o) >= 3:
                spend["BUY_SEED"] += SEED_COST.get(o[1], 0) * int(o[2])
            elif op == "BUY_ANIMAL" and len(o) >= 3:
                spend["BUY_ANIMAL"] += ANIMAL_COST.get(o[1], 0) * int(o[2])
            elif op == "BUY_LAND":
                tier = min(land_tier_state[0], len(LAND_TIER) - 1)
                spend["BUY_LAND"] += LAND_TIER[tier]
                land_tier_state[0] += 1
    spend["HIRE"] = fib_cost(cnt.get("HIRE", 0))
    disc = spend["BUY_SEED"] + spend["BUY_ANIMAL"] + spend["BUY_LAND"] + spend["HIRE"]
    return cnt, spend, disc


def classify_opp(steps, opp):
    amax = 0
    for d in range(30):
        i = min(d * 24, len(steps) - 1)
        try:
            fm = steps[i][opp]["observation"]["farms"][opp]
        except Exception:
            continue
        a = sum(1 for row in fm.get("tiles", []) for t in row
                if isinstance(t, dict) and t.get("animal"))
        amax = max(amax, a)
    return "animal_factory" if amax >= 4 else "other"


def bucket(deficit):
    d = -deficit
    if d < 10000:
        return "close(<10k)"
    if d <= 30000:
        return "recover(10-30k)"
    return "blowout(>30k)"


def trace_one(ep, steps, me, opp, floor):
    land_state = [0]
    rows = []
    for d in range(17):
        i = min(d * 24, len(steps) - 1)
        m = money(steps, i, me)
        om = money(steps, i, opp)
        if m is None:
            continue
        cnt, spend, disc = day_spend(steps, me, d, land_state)
        rows.append((d, m, om, spend, cnt, disc))

    # crater onset: first day 6..15 below floor that stays below through 15
    onset = None
    by_day = {r[0]: r[1] for r in rows}
    for d in range(6, 16):
        if d in by_day and by_day[d] < floor and all(
                by_day.get(k, 0) < floor for k in range(d, 16) if k in by_day):
            onset = d
            break
    early = [(r[5], r[0]) for r in rows if r[0] <= 6]
    big_spend, big_day = max(early) if early else (0, None)
    deficit = (steps[-1][me].get("reward") or 0) - (steps[-1][opp].get("reward") or 0)
    return rows, onset, big_spend, big_day, deficit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sub_refs", nargs="+")
    ap.add_argument("--floor", type=float, default=1500)
    ap.add_argument("--n", type=int, default=40, help="max losses to print in full")
    ap.add_argument("--full", action="store_true", help="print every daily ledger")
    args = ap.parse_args()
    refs = set(args.sub_refs)
    idx = load_index()

    losses = []
    for ep, meta in idx.items():
        if meta["submission_ref"] not in refs:
            continue
        rp = f"replays/episode-{ep}-replay.json"
        if not os.path.exists(rp):
            continue
        try:
            r = json.load(open(rp, encoding="utf-8"))
        except Exception:
            continue
        names = [str(a.get("Name", "")).lower() for a in r["info"]["Agents"]]
        me = 0 if names[0] in ME_NAMES else (1 if names[1] in ME_NAMES else 0)
        opp = 1 - me
        steps = r["steps"]
        my_r = steps[-1][me].get("reward") or 0
        op_r = steps[-1][opp].get("reward") or 0
        if my_r >= op_r:
            continue
        arch = classify_opp(steps, opp)
        rows, onset, big_spend, big_day, deficit = trace_one(ep, steps, me, opp, args.floor)
        losses.append(dict(ep=ep, sub=meta["submission_ref"], arch=arch, rows=rows,
                           onset=onset, big_spend=big_spend, big_day=big_day,
                           deficit=deficit, bucket=bucket(deficit)))
        del r

    losses.sort(key=lambda x: x["deficit"])
    print(f"{len(losses)} loss game(s) across {sorted(refs)}  floor=${args.floor:.0f}\n")

    # ---- aggregate ----
    agg = collections.defaultdict(list)
    for L in losses:
        agg[(L["sub"], L["bucket"], L["arch"])].append(L)
    print(f"{'sub':>9} {'bucket':>16} {'arch':>15} {'n':>3} {'onset~d':>8} "
          f"{'d0 disc$':>9} {'d0-2 seed$':>11} {'d0-2 anim$':>11} {'d0-2 land$':>11} {'d0-2 hire$':>11}")
    for key in sorted(agg):
        g = agg[key]
        def mean(f):
            v = [f(x) for x in g if f(x) is not None]
            return sum(v) / len(v) if v else float("nan")
        d0 = mean(lambda L: next((r[5] for r in L["rows"] if r[0] == 0), None))
        def d02(cat):
            return mean(lambda L: sum(r[3].get(cat, 0) for r in L["rows"] if r[0] <= 2))
        onset = mean(lambda L: L["onset"])
        print(f"{key[0]:>9} {key[1]:>16} {key[2]:>15} {len(g):>3} {onset:>8.1f} "
              f"{d0:>9.0f} {d02('BUY_SEED'):>11.0f} {d02('BUY_ANIMAL'):>11.0f} "
              f"{d02('BUY_LAND'):>11.0f} {d02('HIRE'):>11.0f}")

    # ---- per-game ----
    for L in losses[: args.n]:
        print(f"\n{'='*104}\nEP {L['ep']} sub {L['sub']}  {L['arch']}  {L['bucket']}  "
              f"deficit {L['deficit']:+.0f}  crater onset d{L['onset']}  "
              f"biggest early spend ${L['big_spend']:.0f} on d{L['big_day']}")
        print(f"{'d':>3} {'money':>8} {'chg':>8} {'opp':>8}   {'$seed':>7} {'$anim':>7} "
              f"{'$land':>7} {'#hire':>6} {'disc$':>7}")
        prev = None
        for d, m, om, spend, cnt, disc in L["rows"]:
            dl = "" if prev is None else f"{m-prev:+.0f}"
            mark = "  <-- onset" if d == L["onset"] else ""
            print(f"{d:>3} {m:>8.0f} {dl:>8} {om:>8.0f}   {spend.get('BUY_SEED',0):>7.0f} "
                  f"{spend.get('BUY_ANIMAL',0):>7.0f} {spend.get('BUY_LAND',0):>7.0f} "
                  f"{cnt.get('HIRE',0):>6} {disc:>7.0f}{mark}")
            prev = m


if __name__ == "__main__":
    main()
