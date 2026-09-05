"""E2/E3 diagnostic: day-by-day cash trace for our worst animal_factory losses.

Reconstructs, per day 0-15, our own farm's money trajectory alongside the
market-order categories we fired that day (BUY_LAND / BUY_ANIMAL / HIRE /
BUY_SEED / BUY_PRODUCT / SELL counts), so the first irreversible spend behind
a day-10-15 cash floor is visible directly from the real ladder replay
instead of guessed from aggregate stats. Companion to `tools/ladder_analyze.py`
(which classifies archetype + end-state) -- this tool answers "when/what", not
"how many wins".

    python tools/trace_cashflow.py <SUB_REF> [--arch animal_factory] [--n 8]
"""
import json, csv, collections, sys, os, argparse

IDX = "episodes/index.csv"
ME_NAMES = {"faheem", "faheemkhaskheli9", "faheem khaskheli"}
CATS = ("HIRE", "BUY_LAND", "BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT", "SELL")

# Cost constants (main.py CROPS/ANIMALS) so per-category spend can be summed
# from the order log directly, not just counted -- distinguishes "many cheap
# seed orders" from "a few animal buys" as the actual day-0 cash driver.
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}


def load_index():
    m = {}
    with open(IDX, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m[row["episode_id"]] = row
    return m


def farm_money(steps, i, seat):
    try:
        return steps[i][seat]["observation"]["farms"][seat]["money"]
    except Exception:
        return None


def day_orders(steps, seat, day):
    """Market-order op counts + approximate $ spend by `seat` during day `day`.

    $ is exact for BUY_SEED/BUY_ANIMAL (fixed unit costs), a flat $1000
    estimate for BUY_LAND (true cost is 1000/2000/4000 by quadrant -- rare
    enough in the day 0-15 window that the approximation doesn't matter to
    the diagnosis), and omitted for HIRE (fib(n), resets daily, not worth
    approximating here) and BUY_PRODUCT (wheat buyback at curve price).
    """
    cnt = collections.Counter()
    spend = collections.Counter()
    lo, hi = day * 24, min(day * 24 + 24, len(steps))
    for i in range(lo, hi):
        per = steps[i]
        if seat >= len(per):
            continue
        a = per[seat].get("action") or {}
        for o in a.get("market") or []:
            if isinstance(o, list) and o:
                op = o[0]
                cnt[op] += 1
                if op == "BUY_SEED" and len(o) >= 3:
                    spend[op] += SEED_COST.get(o[1], 0) * int(o[2])
                elif op == "BUY_ANIMAL" and len(o) >= 3:
                    spend[op] += ANIMAL_COST.get(o[1], 0) * int(o[2])
                elif op == "BUY_LAND":
                    spend[op] += 1000
    return cnt, spend


def classify_opp_quick(steps, opp):
    """Same signal ladder_analyze.py uses, inlined to avoid importing it as a module."""
    amax = 0
    for d in range(30):
        i = min(d * 24, len(steps) - 1)
        try:
            fm = steps[i][opp]["observation"]["farms"][opp]
        except Exception:
            continue
        a = 0
        for row in fm.get("tiles", []):
            for t in row:
                if isinstance(t, dict) and t.get("animal"):
                    a += 1
        amax = max(amax, a)
    return amax


def trace(ep, sub_score, steps, me, opp):
    print(f"\n{'='*90}\nEP {ep}  sub_score={sub_score}")
    print(f"{'d':>3} {'money':>8} {'delta':>8}  " + "  ".join(f"{c:>11}" for c in CATS)
          + f"  {'$seed':>7} {'$anim':>7}")
    prev = None
    tot_seed = tot_anim = 0
    for d in range(16):
        i = min(d * 24, len(steps) - 1)
        m = farm_money(steps, i, me)
        if m is None:
            continue
        delta = "" if prev is None else f"{m - prev:+.0f}"
        cnt, spend = day_orders(steps, me, d)
        tot_seed += spend.get("BUY_SEED", 0)
        tot_anim += spend.get("BUY_ANIMAL", 0)
        print(f"{d:>3} {m:>8.0f} {delta:>8}  " + "  ".join(f"{cnt.get(c, 0):>11}" for c in CATS)
              + f"  {spend.get('BUY_SEED', 0):>7} {spend.get('BUY_ANIMAL', 0):>7}")
        prev = m
    last = steps[-1]
    print(f"  totals d0-15: $seed={tot_seed} $anim={tot_anim}")
    print(f"  FINAL me {last[me].get('reward')}  opp {last[opp].get('reward')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sub_refs", nargs="*")
    ap.add_argument("--arch", default="animal_factory", choices=["animal_factory", "any"])
    ap.add_argument("--n", type=int, default=8, help="worst-N loss games to trace")
    args = ap.parse_args()
    refs = set(args.sub_refs)

    idx = load_index()
    cand = []
    for ep, meta in idx.items():
        if refs and meta["submission_ref"] not in refs:
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
        last = steps[-1]
        my_r = last[me].get("reward") or 0
        op_r = last[opp].get("reward") or 0
        if my_r >= op_r:
            continue  # only losses
        if args.arch == "animal_factory":
            amax = classify_opp_quick(steps, opp)
            if amax < 4:
                continue
        cand.append((my_r - op_r, ep, meta["submission_score"], steps, me, opp))
        del r

    cand.sort(key=lambda x: x[0])  # worst deficit first
    print(f"{len(cand)} matching loss game(s) found; tracing worst {min(args.n, len(cand))}")
    for deficit, ep, score, steps, me, opp in cand[: args.n]:
        trace(ep, score, steps, me, opp)


if __name__ == "__main__":
    main()
