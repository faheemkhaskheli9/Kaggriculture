"""Per-submission ladder replay analysis. Low-memory: one replay at a time.

Usage: python ladder_analyze.py [SUB_REF ...]   (default: all subs in index.csv)
"""
import json, csv, collections, statistics, sys, os

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
IDX = "episodes/index.csv"
ME_NAMES = {"faheem", "faheemkhaskheli9", "faheem khaskheli"}


def load_index():
    m = {}
    with open(IDX) as f:
        for row in csv.DictReader(f):
            m[row["episode_id"]] = row
    return m


def farm(steps, i, seat):
    try:
        return steps[i][0]["observation"]["farms"][seat]
    except Exception:
        return None


def traj(steps, seat):
    out = {}
    for d in range(30):
        i = min(d * 24, len(steps) - 1)
        fm = farm(steps, i, seat)
        if not fm:
            continue
        plants = collections.Counter()
        weeds = animals = 0
        for rr in fm.get("tiles", []):
            for t in rr:
                if isinstance(t, dict):
                    k = t.get("kind")
                    if k == "PLANT":
                        plants[t.get("crop")] += 1
                    elif k == "WEED":
                        weeds += 1
                    if t.get("animal"):
                        animals += 1
        out[d] = dict(money=fm.get("money", 0), plants=sum(plants.values()),
                      weeds=weeds, animals=animals,
                      quads=len(fm.get("unlocked_quadrants", [])), mix=dict(plants))
    return out


def tally(steps, seat):
    mv = nonpass = 0
    sells = collections.Counter()
    acts = collections.Counter()
    hires = 0
    for per in steps:
        if seat >= len(per):
            continue
        a = per[seat].get("action") or {}
        us = []
        fa = a.get("farmer")
        if isinstance(fa, list) and fa:
            us.append(fa[0])
        for h in a.get("hands") or []:
            if isinstance(h, list) and h:
                us.append(h[0])
        for u in us:
            if u == "PASS":
                continue
            nonpass += 1
            acts[u] += 1
            if u in MOVES:
                mv += 1
        for o in a.get("market") or []:
            if isinstance(o, list) and o:
                if o[0] == "SELL" and len(o) >= 3:
                    try:
                        sells[o[1]] += int(o[2])
                    except Exception:
                        pass
                if o[0] == "HIRE":
                    hires += 1
    return dict(move_pct=(mv / nonpass if nonpass else 0), sells=dict(sells),
                acts=dict(acts.most_common(6)), nonpass=nonpass, hires=hires)


def classify_opp(ot, oa):
    amax = max((ot.get(d, {}).get("animals", 0) for d in range(30)), default=0)
    pmax = max((ot.get(d, {}).get("plants", 0) for d in range(30)), default=0)
    s = oa["sells"]
    tot = sum(s.values()) or 1
    wheat_f = s.get("WHEAT", 0) / tot
    mix29 = ot.get(29, {}).get("mix", {})
    if amax >= 4 and (s.get("FERTILIZER", 0) + s.get("MILK", 0) + s.get("WOOL", 0)) / tot > 0.3:
        return "animal_factory"
    if wheat_f > 0.6 and pmax > 25:
        return "wheat_flood"
    if mix29.get("MELON", 0) >= 8:
        return "melon_mono"
    if (mix29.get("STRAWBERRY", 0) + mix29.get("TOMATO", 0)) >= 8 and pmax < 25 and oa["nonpass"] < 3000:
        return "premium"
    if pmax <= 5 and amax == 0:
        return "passive"
    if oa["nonpass"] < 500:
        return "passive"
    return "other"


def analyze(refs):
    idx = load_index()
    bysub = collections.defaultdict(list)
    for ep, meta in idx.items():
        if refs and meta["submission_ref"] not in refs:
            continue
        rp = f"replays/episode-{ep}-replay.json"
        if not os.path.exists(rp):
            continue
        try:
            r = json.load(open(rp))
        except Exception as e:
            print(f"  skip {ep}: {e}")
            continue
        names = [str(a.get("Name", "")).lower() for a in r["info"]["Agents"]]
        me = 0 if names[0] in ME_NAMES else (1 if names[1] in ME_NAMES else 0)
        opp = 1 - me
        steps = r["steps"]
        last = steps[-1]
        my_r = last[me].get("reward") or 0
        op_r = last[opp].get("reward") or 0
        res = "W" if my_r > op_r else ("L" if my_r < op_r else "T")
        mt, ot = traj(steps, me), traj(steps, opp)
        ma, oa = tally(steps, me), tally(steps, opp)
        arch = classify_opp(ot, oa)
        bysub[meta["submission_ref"]].append(dict(
            ep=ep, score=meta["submission_score"], res=res, my=int(my_r), op=int(op_r),
            arch=arch,
            my_d=[int(mt.get(x, {}).get("money", 0)) for x in (5, 10, 15, 20, 25, 29)],
            op_d=[int(ot.get(x, {}).get("money", 0)) for x in (5, 10, 15, 20, 25, 29)],
            my_p=[mt.get(x, {}).get("plants", 0) for x in (5, 10, 15, 20, 25, 29)],
            my_w29=mt.get(29, {}).get("weeds", 0),
            my_a=max((mt.get(x, {}).get("animals", 0) for x in range(30)), default=0),
            op_a=max((ot.get(x, {}).get("animals", 0) for x in range(30)), default=0),
            my_q=mt.get(29, {}).get("quads", 0),
            my_move=ma["move_pct"], my_hires=ma["hires"],
            my_sells=ma["sells"], op_sells=oa["sells"],
            my_mix29=mt.get(29, {}).get("mix", {}),
            my_nonpass=ma["nonpass"],
        ))
        del r, steps
    for sub in sorted(bysub, key=lambda s: float(bysub[s][0]["score"])):
        rows = bysub[sub]
        W = sum(x["res"] == "W" for x in rows)
        L = sum(x["res"] == "L" for x in rows)
        T = sum(x["res"] == "T" for x in rows)
        print(f"\n{'='*90}\nSUB {sub}  ladder {rows[0]['score']}  |  {len(rows)} eps  {W}W-{T}T-{L}L  "
              f"score-rate {(W+0.5*T)/len(rows):.0%}")
        print(f"  my coins: mean {statistics.mean(x['my'] for x in rows):.0f}  "
              f"median {statistics.median(x['my'] for x in rows):.0f}  "
              f"min {min(x['my'] for x in rows)}  max {max(x['my'] for x in rows)}")
        by_arch = collections.Counter(x["arch"] for x in rows)
        arch_res = collections.defaultdict(lambda: [0, 0, 0])
        for x in rows:
            arch_res[x["arch"]][0 if x["res"] == "W" else (2 if x["res"] == "L" else 1)] += 1
        print("  vs archetype:", {a: f"{arch_res[a][0]}W-{arch_res[a][1]}T-{arch_res[a][2]}L" for a in by_arch})
        print(f"  avg move%: {statistics.mean(x['my_move'] for x in rows):.0%}  "
              f"avg plants d10/20/29: "
              f"{statistics.mean(x['my_p'][1] for x in rows):.0f}/"
              f"{statistics.mean(x['my_p'][3] for x in rows):.0f}/"
              f"{statistics.mean(x['my_p'][5] for x in rows):.0f}  "
              f"avg weeds29: {statistics.mean(x['my_w29'] for x in rows):.0f}  "
              f"avg animals: {statistics.mean(x['my_a'] for x in rows):.1f}  "
              f"avg quads29: {statistics.mean(x['my_q'] for x in rows):.1f}")
        allsell = collections.Counter()
        for x in rows:
            allsell.update(x["my_sells"])
        print(f"  my total sells (all eps): {dict(allsell.most_common())}")
        print("  --- games (worst first) ---")
        for x in sorted(rows, key=lambda z: z["my"] - z["op"]):
            print(f"  {x['ep']} {x['res']} [{x['arch']:14}] me {x['my']:6d} vs {x['op']:6d}  "
                  f"money d5/10/15/20/25/29 me {x['my_d']} op {x['op_d']}")
            print(f"       plants {x['my_p']} weeds29={x['my_w29']} anim={x['my_a']}(opp {x['op_a']}) "
                  f"quads={x['my_q']} move%={x['my_move']:.0%} hires={x['my_hires']} acts={x['my_nonpass']}")
            print(f"       me sells {dict(sorted(x['my_sells'].items(), key=lambda i:-i[1]))}")
            print(f"       opp sells {dict(sorted(x['op_sells'].items(), key=lambda i:-i[1]))} mix29={x['my_mix29']}")


if __name__ == "__main__":
    analyze(set(sys.argv[1:]))
