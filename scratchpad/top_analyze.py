"""Dissect the top-10 ladder replays: what do 2840-2963 agents actually do?"""
import json, glob, collections, statistics, os

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}

def load(p):
    return json.load(open(p))

def farm(steps, i, seat):
    try:
        return steps[i][0]["observation"]["farms"][seat]
    except Exception:
        return None

def snap(fm):
    plants = collections.Counter(); weeds = animals = built = 0
    for rr in fm.get("tiles", []):
        for t in rr:
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "PLANT": plants[t.get("crop")] += 1
                elif k == "WEED": weeds += 1
                if t.get("animal"): animals += 1
    return dict(money=fm.get("money", 0), plants=sum(plants.values()), mix=dict(plants),
               weeds=weeds, animals=animals, quads=len(fm.get("unlocked_quadrants", [])))

def tally(steps, seat):
    mv = nonpass = hires = 0
    sells = collections.Counter(); buys = collections.Counter(); acts = collections.Counter()
    for per in steps:
        if seat >= len(per): continue
        a = per[seat].get("action") or {}
        us = []
        fa = a.get("farmer")
        if isinstance(fa, list) and fa: us.append(fa[0])
        for h in a.get("hands") or []:
            if isinstance(h, list) and h: us.append(h[0])
        for u in us:
            if u == "PASS": continue
            nonpass += 1; acts[u] += 1
            if u in MOVES: mv += 1
        for o in a.get("market") or []:
            if isinstance(o, list) and o:
                if o[0] == "SELL" and len(o) >= 3:
                    try: sells[o[1]] += int(o[2])
                    except Exception: pass
                if o[0] == "HIRE": hires += 1
                if o[0] and str(o[0]).startswith("BUY"): buys[tuple(o)] += 1
    return dict(move_pct=mv/nonpass if nonpass else 0, nonpass=nonpass, hires=hires,
               sells=dict(sells.most_common()), acts=dict(acts.most_common(8)))

for p in sorted(glob.glob("top10_ladder/replays/*.json")):
    r = load(p)
    ag = r["info"]["Agents"]
    steps = r["steps"]
    names = [a.get("Name","?") for a in ag]
    finals = [steps[-1][s].get("reward") or 0 for s in range(2)]
    win = 0 if finals[0] >= finals[1] else 1
    print("="*100)
    print(f"{os.path.basename(p)}  {names[0]} {int(finals[0])}  vs  {names[1]} {int(finals[1])}   winner=seat{win}")
    for seat in range(2):
        traj = []
        for d in (5, 10, 15, 20, 25, 29):
            fm = farm(steps, min(d*24, len(steps)-1), seat)
            if fm: traj.append((d, snap(fm)))
        t = tally(steps, seat)
        m = [f"d{d}:${s['money']//1000}k/p{s['plants']}/w{s['weeds']}/a{s['animals']}/q{s['quads']}" for d, s in traj]
        print(f" seat{seat} {names[seat][:22]:22} {'WIN' if seat==win else '   '}")
        print(f"   {'  '.join(m)}")
        last_mix = traj[-1][1]['mix'] if traj else {}
        print(f"   final mix={last_mix}  move%={t['move_pct']:.0%}  hires={t['hires']}  acts={t['nonpass']}")
        print(f"   sells={t['sells']}")
        print(f"   acts={t['acts']}")
    del r, steps
