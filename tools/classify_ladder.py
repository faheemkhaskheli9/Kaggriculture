import json, glob, csv, collections, statistics

MOVES = {"NORTH","SOUTH","EAST","WEST"}
SUB = "55952982"

def load_index():
    m = {}
    with open("episodes/index.csv") as f:
        for row in csv.DictReader(f):
            m[row["episode_id"]] = row
    return m

idx = load_index()
rows = []
for ep, meta in sorted(idx.items()):
    if meta["submission_ref"] != SUB: continue
    rp = f"replays/episode-{ep}-replay.json"
    try: r = json.load(open(rp))
    except FileNotFoundError: continue
    names = [a["Name"] for a in r["info"]["Agents"]]
    me = 0 if names[0] == "faheem" else 1
    opp = 1 - me
    steps = r["steps"]
    last = steps[-1]
    my_r = last[me].get("reward") or 0
    op_r = last[opp].get("reward") or 0
    res = "W" if my_r > op_r else ("L" if my_r < op_r else "T")

    def farm(i, seat): 
        try: return steps[i][0]["observation"]["farms"][seat]
        except Exception: return None
    # trajectories
    def traj(seat):
        out = {}
        for d in range(0,30):
            i = min(d*24, len(steps)-1)
            fm = farm(i, seat)
            if not fm: continue
            tiles = fm.get("tiles",[])
            plants = collections.Counter()
            weeds = animals = 0
            for rr in tiles:
                for t in rr:
                    if isinstance(t, dict):
                        k = t.get("kind")
                        if k == "PLANT": plants[t.get("crop")] += 1
                        elif k == "WEED": weeds += 1
                        if t.get("animal"): animals += 1
            out[d] = dict(money=fm.get("money",0), plants=sum(plants.values()),
                          weeds=weeds, animals=animals,
                          quads=len(fm.get("unlocked_quadrants",[])), mix=dict(plants))
        return out
    mt, ot = traj(me), traj(opp)
    # action + sell tally
    def tally(seat):
        mv=nonpass=0; sells=collections.Counter(); acts=collections.Counter()
        for per in steps:
            if seat>=len(per): continue
            a = per[seat].get("action") or {}
            us = []
            fa = a.get("farmer")
            if isinstance(fa,list) and fa: us.append(fa[0])
            for h in a.get("hands") or []:
                if isinstance(h,list) and h: us.append(h[0])
            for u in us:
                if u=="PASS": continue
                nonpass+=1; acts[u]+=1
                if u in MOVES: mv+=1
            for o in a.get("market") or []:
                if isinstance(o,list) and o and o[0]=="SELL" and len(o)>=3:
                    try: sells[o[1]] += int(o[2])
                    except: pass
        return dict(move_pct=(mv/nonpass if nonpass else 0), sells=dict(sells),
                    acts=dict(acts.most_common(6)), nonpass=nonpass)
    ma, oa = tally(me), tally(opp)
    def d(t, day, k): return t.get(day,{}).get(k,0)
    rows.append(dict(ep=ep, res=res, my=int(my_r), op=int(op_r),
        my_d=[int(d(mt,x,"money")) for x in (10,15,20,25,29)],
        op_d=[int(d(ot,x,"money")) for x in (10,15,20,25,29)],
        my_plants29=d(mt,29,"plants"), my_weeds29=d(mt,29,"weeds"),
        my_animals_max=max((d(mt,x,"animals") for x in range(30)), default=0),
        op_animals_max=max((d(ot,x,"animals") for x in range(30)), default=0),
        op_plants_max=max((d(ot,x,"plants") for x in range(30)), default=0),
        my_quads=d(mt,29,"quads"), op_quads=d(ot,29,"quads"),
        my_move=ma["move_pct"], my_sells=ma["sells"], op_sells=oa["sells"],
        op_mix29=ot.get(29,{}).get("mix",{}), my_mix29=mt.get(29,{}).get("mix",{})))

W = sum(r["res"]=="W" for r in rows); L=sum(r["res"]=="L" for r in rows); T=sum(r["res"]=="T" for r in rows)
print(f"=== sub {SUB}: {len(rows)} games  {W}W-{T}T-{L}L ===")
print(f"my coins: mean {statistics.mean(r['my'] for r in rows):.0f}  median {statistics.median(r['my'] for r in rows):.0f}  min {min(r['my'] for r in rows)}  max {max(r['my'] for r in rows)}")
print()
for r in sorted(rows, key=lambda x:x["my"]-x["op"]):
    tag = f"opp_anim={r['op_animals_max']:2d} opp_plants={r['op_plants_max']:2d} opp_quads={r['op_quads']}"
    print(f"{r['ep']} {r['res']}  me {r['my']:6d} vs {r['op']:6d}  d10/15/20/25/29 me {r['my_d']}  op {r['op_d']}")
    print(f"    me: plants29={r['my_plants29']} weeds29={r['my_weeds29']} anim_max={r['my_animals_max']} quads={r['my_quads']} move%={r['my_move']:.0%}")
    print(f"    me sells: { {k:v for k,v in sorted(r['my_sells'].items(), key=lambda x:-x[1])} }")
    print(f"    OPP [{tag}] sells: { {k:v for k,v in sorted(r['op_sells'].items(), key=lambda x:-x[1])} }  mix29={r['op_mix29']}")
