"""Kaggriculture v2: robust multi-unit, demand-aware crop agent."""
from collections import Counter

CROPS = {
    "WHEAT": (10, 4, 25), "CARROT": (20, 3, 26),
    "TOMATO": (50, 11, 18), "STRAWBERRY": (100, 16, 13),
    "MELON": (80, 10, 19),
}
BASE = {"WHEAT":25, "CARROT":35, "TOMATO":60, "STRAWBERRY":120,
        "MELON":250, "EGG":50, "MILK":160, "WOOL":200, "FERTILIZER":100}
DEMAND = {
    "Bakery":{"EGG":1,"WHEAT":1}, "Pizza Shop":{"MILK":1,"TOMATO":1,"WHEAT":1},
    "Brunch Spot":{"EGG":1,"WHEAT":1,"STRAWBERRY":1}, "Yarn Store":{"WOOL":2},
    "Ice Cream Shop":{"STRAWBERRY":1,"MILK":1,"WHEAT":1},
    "Pet Cafe":{"CARROT":2}, "Smoothie Shop":{"STRAWBERRY":1,"MILK":1},
    "Farmers Market":{"WHEAT":1,"CARROT":1,"TOMATO":1,"STRAWBERRY":1},
}
ONE_TIME = {"WHEAT", "CARROT", "MELON"}
SHED = {(4,4),(5,4),(4,5),(5,5)}

def dist(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])

def move(a,b):
    x,y=a; X,Y=b
    if x<X:return ["EAST"]
    if x>X:return ["WEST"]
    if y<Y:return ["SOUTH"]
    if y>Y:return ["NORTH"]
    return ["PASS"]

def inv_total(inv):
    return sum(max(0,int(v)) for v in (inv or {}).values())

def field_counts(farm):
    c=Counter()
    for row in farm.get("tiles",[]):
        for t in row:
            if isinstance(t,dict) and t.get("kind")=="PLANT": c[t.get("crop")]+=1
    return c

def choose_crop(obs, me, private, counts):
    day=obs.get("day",0); prices=(obs.get("market") or {}).get("prices",{})
    demand=Counter()
    for shop in (obs.get("town") or {}).get("unlocked_shops",[]):
        demand.update(DEMAND.get(shop,{}))
    opp=field_counts(obs["farms"][1-obs["player"]])
    # Two compact quadrants. Staples get most of the area; premium crops are
    # deliberately capped because their price collapses under a glut.
    caps={"WHEAT":16,"CARROT":12,"TOMATO":7,"STRAWBERRY":4,"MELON":4}
    best=None
    for crop,(cost,peak,cutoff) in CROPS.items():
        if day>cutoff or counts[crop]>=caps[crop]: continue
        score=2*prices.get(crop,BASE[crop])/BASE[crop]
        score+=.65*demand[crop]-.12*opp[crop]-.10*peak-.18*counts[crop]
        score+=.75 if crop=="WHEAT" else (.35 if crop=="CARROT" else 0)
        if crop in {"STRAWBERRY","MELON"} and not demand[crop]: score-=1.25
        candidate=(score,crop)
        if best is None or candidate>best: best=candidate
    return best[1] if best else None

def tasks_for(obs, me, private, crop):
    day=obs.get("day",0); hour=obs.get("hour",0); tasks=[]; counts=Counter()
    for y,row in enumerate(me["tiles"]):
        for x,t in enumerate(row):
            if not isinstance(t,dict): continue
            pos=(x,y); kind=t.get("kind")
            if kind=="PLANT":
                name=t.get("crop"); counts[name]+=1
                age=day-t.get("planted_day",day)
                ripe=t.get("yield_units",0)>0 and (name not in ONE_TIME or age>=CROPS[name][1])
                if ripe: tasks.append((940 if name not in ONE_TIME else 900+age,pos,["HARVEST"]))
                elif not t.get("watered_today",False):
                    tasks.append((1000+80*t.get("consecutive_unwatered",0)+3*hour,pos,["WATER"]))
            elif kind in {"COOP","PASTURE"} and t.get("animal"):
                if not t.get("fed_today",False):
                    tasks.append((1030+80*t.get("consecutive_unfed",0)+3*hour,pos,["FEED"]))
                if t.get("yield_units",0)>0: tasks.append((920,pos,["HARVEST"]))
            elif kind=="WEED": tasks.append((230,pos,["DIG"]))
    units=1+len(me.get("hands",[])); capacity=min(43,max(8,units*6+1))
    seeds=private.get("seeds",{})
    if crop and seeds.get(crop,0)>0 and hour<23 and sum(counts.values())<capacity:
        empty=[]
        for y,row in enumerate(me["tiles"]):
            for x,t in enumerate(row):
                if t is None: empty.append((dist((x,y),(4,4)),y,x))
        # More simultaneous PLANT commands than available seeds invalidate all of
        # them, so expose at most the currently observed seed count as tasks.
        plant_slots=min(capacity-sum(counts.values()),int(seeds.get(crop,0)))
        for _,y,x in sorted(empty)[:plant_slots]:
            tasks.append((300,(x,y),["PLANT",crop]))
    return tasks,counts

def assign(obs, me, private, tasks):
    pos=[tuple(me["farmer"])]+[tuple(p) for p in me.get("hands",[])]
    inv=list(private.get("inventories",[]))+[{}]*len(pos)
    actions=[["PASS"] for _ in pos]; used=set(); busy=set()
    hour=obs.get("hour",0)
    for i,p in enumerate(pos):
        if inv_total(inv[i]) and (hour>=20 or inv_total(inv[i])>=8):
            target=min(SHED,key=lambda q:dist(p,q))
            actions[i]=["DROP"] if p in SHED else move(p,target); busy.add(i)
    # Assign urgent tasks before units: best available unit for each task avoids
    # a distant farmer reserving a deadline that a nearby hand could satisfy.
    for priority,target,action in sorted(tasks,key=lambda t:t[0],reverse=True):
        if target in used: continue
        candidates=[(dist(pos[i],target),i) for i in range(len(pos)) if i not in busy]
        if not candidates: break
        _,i=min(candidates)
        actions[i]=action if pos[i]==target else move(pos[i],target)
        used.add(target); busy.add(i)
    return actions

def market_orders(obs, me, private, crop, counts):
    day=obs.get("day",0); hour=obs.get("hour",0); money=int(me.get("money",0))
    prices=(obs.get("market") or {}).get("prices",{}); out=[]
    for item,qty in private.get("shed",{}).items():
        if qty<=0 or item not in BASE: continue
        premium=item in {"STRAWBERRY","MELON","MILK","WOOL"}
        if day>=27 or not premium or prices.get(item,BASE[item])>=BASE[item]:
            out.append(["SELL",item,min(qty,3) if premium and day<29 else qty])
    # Six hands cost only 20 coins/day (1+1+2+3+5+8), while providing 144
    # additional unit-actions. Taper late when planting has stopped.
    desired=6 if day<26 else (4 if day<28 else (2 if day<29 else 0))
    if hour<=2:
        for _ in range(max(0,desired-int(me.get("hires_today",0)))): out.append(["HIRE"])
    if crop:
        cost=CROPS[crop][0]; desired_seed=4 if crop in {"WHEAT","CARROT"} else 2
        need=max(0,desired_seed-int(private.get("seeds",{}).get(crop,0)))
        buy=min(need,max(0,(money-250)//cost))
        if buy: out.append(["BUY_SEED",crop,buy]); money-=buy*cost
    unlocked=set(me.get("unlocked_quadrants",[]))
    occupied=sum(counts.values())
    if day<=19 and len(unlocked)==1 and occupied>=22 and money>=1800:
        out.append(["BUY_LAND"])
    return out[:10]

def agent(obs):
    try:
        player=int(obs.get("player",0)); farms=obs.get("farms",[])
        if len(farms)<2:return {"farmer":["PASS"],"hands":[],"market":[]}
        me=farms[player]; private=obs.get("private") or {}; counts=field_counts(me)
        crop=choose_crop(obs,me,private,counts)
        tasks,counts=tasks_for(obs,me,private,crop)
        actions=assign(obs,me,private,tasks)
        return {"farmer":actions[0],"hands":actions[1:],
                "market":market_orders(obs,me,private,crop,counts)}
    except Exception:
        try:n=len(obs["farms"][obs["player"]].get("hands",[]))
        except Exception:n=0
        return {"farmer":["PASS"],"hands":[["PASS"] for _ in range(n)],"market":[]}

if __name__=="__main__":
    print("Kaggriculture Agent v2")
