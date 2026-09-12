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


LOGS_DIR = "logs"
CRATER_FLOOR = 1500  # same floor as tools/trace_crater.py, kept in sync deliberately


def log_diagnostics(ep, meta, seat):
    """Rule out an agent() exception first (workflow rule) and flag any step
    over the ~1s wall-clock budget (CLAUDE.md constraint) for our seat's log."""
    avail = (meta.get("logs") or "").split(",")
    if str(seat) not in avail:
        return dict(checked=False, exc=False, slow=0, max_dur=0.0)
    path = f"{LOGS_DIR}/episode-{ep}-agent-{seat}-logs.json"
    if not os.path.exists(path):
        return dict(checked=False, exc=False, slow=0, max_dur=0.0)
    try:
        steps = json.load(open(path, encoding="utf-8"))
    except Exception:
        return dict(checked=False, exc=False, slow=0, max_dur=0.0)
    exc = slow = 0
    max_dur = 0.0
    for per in steps:
        for call in per if isinstance(per, list) else [per]:
            if not isinstance(call, dict):
                continue
            err = call.get("stderr") or ""
            if "Traceback" in err:
                exc += 1
            dur = call.get("duration") or 0.0
            max_dur = max(max_dur, dur)
            if dur > 1.0:
                slow += 1
    return dict(checked=True, exc=bool(exc), exc_count=exc, slow=slow, max_dur=max_dur)


def classify_loss_cause(x, diag):
    """Bucket a loss by the failure mode that already has a name/history in
    this project, so a bad read doesn't need a fresh by-hand trace every time
    (see experiments/LEDGER.md's mid-game-crater / weed-pileup / movement
    write-ups). Order matters -- most actionable / most certain first."""
    if diag.get("exc"):
        return "EXCEPTION"
    if diag.get("slow"):
        return "OVER_BUDGET"
    margin = x["op"] - x["my"]
    if margin <= 0:
        return "n/a"
    # Mid-game cash crater: still under CRATER_FLOOR at d15 while the
    # opponent has pulled well clear -- the animal_factory pattern traced in
    # tools/trace_crater.py / trace_cashflow.py.
    my_d15, op_d15 = x["my_d"][2], x["op_d"][2]
    if my_d15 < CRATER_FLOOR and op_d15 > 3 * CRATER_FLOOR:
        return "CRATER"
    if x["my_w29"] >= 15:
        return "WEED_PILEUP"
    if margin < 0.1 * max(x["my"], x["op"], 1):
        return "CLOSE/NOISE"
    return "OTHER"


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
        diag = log_diagnostics(ep, meta, me)
        bysub[meta["submission_ref"]].append(dict(
            diag=diag,
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
        exc_eps = [x["ep"] for x in rows if x["diag"].get("exc")]
        slow_eps = [x["ep"] for x in rows if x["diag"].get("slow")]
        if exc_eps:
            print(f"  \\!/ AGENT() EXCEPTION in {len(exc_eps)} ep(s) (rule out first): {exc_eps}")
        if slow_eps:
            print(f"  \\!/ OVER ~1s WALL-CLOCK BUDGET in {len(slow_eps)} ep(s): {slow_eps}")
        losses = [x for x in rows if x["res"] == "L"]
        if losses:
            causes = collections.Counter(classify_loss_cause(x, x["diag"]) for x in losses)
            print(f"  loss causes ({len(losses)} L): {dict(causes.most_common())}")
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
            tag = f" <{classify_loss_cause(x, x['diag'])}>" if x["res"] == "L" else ""
            flags = ""
            if x["diag"].get("exc"):
                flags += " [EXC]"
            if x["diag"].get("slow"):
                flags += f" [SLOW x{x['diag']['slow']}]"
            print(f"  {x['ep']} {x['res']}{tag}{flags} [{x['arch']:14}] me {x['my']:6d} vs {x['op']:6d}  "
                  f"money d5/10/15/20/25/29 me {x['my_d']} op {x['op_d']}")
            print(f"       plants {x['my_p']} weeds29={x['my_w29']} anim={x['my_a']}(opp {x['op_a']}) "
                  f"quads={x['my_q']} move%={x['my_move']:.0%} hires={x['my_hires']} acts={x['my_nonpass']}")
            print(f"       me sells {dict(sorted(x['my_sells'].items(), key=lambda i:-i[1]))}")
            print(f"       opp sells {dict(sorted(x['op_sells'].items(), key=lambda i:-i[1]))} mix29={x['my_mix29']}")


if __name__ == "__main__":
    analyze(set(sys.argv[1:]))
