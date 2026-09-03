import json, sys, collections
ep = sys.argv[1]
max_day = int(sys.argv[2]) if len(sys.argv) > 2 else 9
ME = {"faheem", "faheemkhaskheli9", "faheem khaskheli"}
r = json.load(open(f"replays/episode-{ep}-replay.json"))
names = [str(a.get("Name", "")).lower() for a in r["info"]["Agents"]]
me = 0 if names[0] in ME else 1
opp = 1 - me
steps = r["steps"]
print(f"ep {ep} me=seat{me} {names}")
print(f"{'st':>3} {'d':>2} {'h':>2} {'money':>7} {'opp$':>7} {'pl':>3} {'wd':>2} {'an':>2} {'q':>1} {'hd':>2} {'seeds':>22} {'shed':>20}  acts | market")
for i, per in enumerate(steps):
    if me >= len(per): continue
    obs = per[me].get("observation") or {}
    day = obs.get("day", i // 24); hour = obs.get("hour", i % 24)
    if day > max_day: break
    if not (hour <= 7 or hour % 6 == 0): continue
    farms = obs.get("farms") or [{}, {}]
    fm = farms[me]; of = farms[opp] if len(farms) > opp else {}
    priv = obs.get("private") or {}
    pc = collections.Counter(); weeds = anim = 0
    for row in fm.get("tiles", []):
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT": pc[t["crop"]] += 1
                elif t.get("kind") == "WEED": weeds += 1
                if t.get("animal"): anim += 1
    seeds = {k: v for k, v in (priv.get("seeds") or {}).items() if v}
    shed = {k: int(v) for k, v in sorted((priv.get("shed") or {}).items(), key=lambda x: -x[1]) if v}
    act = per[me].get("action") or {}
    us = []
    fa = act.get("farmer")
    if isinstance(fa, list) and fa: us.append(fa[0])
    for h in act.get("hands") or []:
        if isinstance(h, list) and h: us.append(h[0])
    ac = dict(collections.Counter(us))
    print(f"{i:>3} {day:>2} {hour:>2} {fm.get('money',0):>7.0f} {of.get('money',0):>7.0f} {sum(pc.values()):>3} {weeds:>2} {anim:>2} {len(fm.get('unlocked_quadrants',[])):>1} {len(fm.get('hands',[])):>2} {str(dict(seeds))[:22]:>22} {str(dict(list(shed.items())[:2]))[:20]:>20}  {ac} | {act.get('market') or []}")
