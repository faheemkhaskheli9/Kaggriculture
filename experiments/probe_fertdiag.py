"""One local game -> fertilizer/STR tick diagnostics for OUR seat."""
import sys, os, io, contextlib, collections
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.chdir(r"E:\Competitions\Kaggriculture")
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from kaggle_environments import make
ours, opp, seed, seat = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
CFG = {"episodeSteps": 720, "actTimeout": 1, "runTimeout": 1200, "startingMoney": 3000, "turnsPerDay": 24, "maxMarketOrdersPerTurn": 10, "seed": seed}
env = make("kaggriculture", configuration=CFG, debug=False)
with contextlib.redirect_stdout(io.StringIO()):
    env.run([ours, opp] if seat == 0 else [opp, ours])
S = env.steps
TICK = {"STRAWBERRY": (10, 12, 14, 16), "TOMATO": (8, 9, 10, 11)}
C = collections.Counter
perday = collections.defaultdict(C)
tot = C()
for i in range(1, len(S)):
    act = S[i][seat].get("action") or {}
    pobs = S[i-1][0]["observation"]; obs = S[i][0]["observation"]
    day, hour = pobs.get("day", 0), pobs.get("hour", 0)
    for a in [act.get("farmer")] + list(act.get("hands") or []):
        if a and a[0] in ("FERTILIZE", "WATER", "PASS", "COLLECT_FERTILIZER", "HARVEST"):
            perday[day][a[0]] += 1
        if a and a[0] == "PICKUP" and len(a) > 2 and a[1] == "FERTILIZER":
            perday[day]["pickF"] += int(a[2])
    for o in (act.get("market") or []):
        if o and o[0] == "SELL" and o[1] in ("FERTILIZER", "STRAWBERRY", "MILK", "EGG", "WOOL", "MELON", "WHEAT"):
            perday[day]["sell_" + o[1][:4]] += int(o[2])
        if o and o[0] == "BUY_PRODUCT" and o[1] == "FERTILIZER":
            perday[day]["buy_FERT"] += int(o[2])
    if hour == 0:
        priv0 = S[i-1][seat]["observation"].get("private") or {}
        perday[day]["shedF@h0"] = int((priv0.get("shed") or {}).get("FERTILIZER", 0))
        perday[day]["shedTot@h0"] = int(sum((priv0.get("shed") or {}).values()))
        for row in pobs["farms"][seat]["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") in TICK:
                    age = day - int(t.get("planted_day", day))
                    if (age + 1) in TICK[t["crop"]] and t.get("fertilized_until_day", -1) < day:
                        perday[day]["want@h0"] += 1
    if hour == 2:
        priv = S[i][seat]["observation"].get("private") or {}
        perday[day]["shedF@h2"] = int((priv.get("shed") or {}).get("FERTILIZER", 0))
        pr = (obs.get("market") or {}).get("prices") or {}
        perday[day]["pSTR"] = int(pr.get("STRAWBERRY", 0)); perday[day]["pFERT"] = int(pr.get("FERTILIZER", 0)); perday[day]["pMILK"] = int(pr.get("MILK", 0))
    if hour == 23:
        for row in obs["farms"][seat]["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("animal"):
                    cap = {"GOOSE": 4, "COW": 6, "SHEEP": 6}[t["animal"]]
                    if t.get("yield_units", 0) >= cap: perday[day]["an_cap"] += 1
                    perday[day]["an_held"] += int(t.get("yield_units", 0))
                if isinstance(t, dict) and t.get("kind") == "WEED": perday[day]["weeds"] += 1
    if hour == 23:   # state after the last action of the day, before refresh? use post-action obs of the h23 step
        farm = obs["farms"][seat] if obs.get("day", 0) == day else pobs["farms"][seat]
        for row in farm["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") in TICK:
                    age = day - int(t.get("planted_day", day))
                    if (age + 1) in TICK[t["crop"]]:
                        k = t["crop"][:3]
                        perday[day]["tick_" + k] += 1
                        f = t.get("fertilized_until_day", -1) >= day
                        w = bool(t.get("watered_today"))
                        if f and w: perday[day]["tickFW_" + k] += 1
                        elif f: perday[day]["tickF_dry_" + k] += 1
L = S[-1][0]["observation"]["farms"]
print("final ours/opp:", L[seat]["money"], L[1-seat]["money"])
cols = ["want@h0", "shedF@h0", "shedTot@h0", "pickF", "FERTILIZE", "sell_FERT", "pFERT", "pSTR", "pMILK", "tick_STR", "tickFW_STR", "tickF_dry_STR", "sell_STRA", "WATER", "PASS", "an_cap", "an_held", "weeds"]
print("day " + " ".join(f"{c[:10]:>10}" for c in cols))
for d in sorted(perday):
    if d >= 8:
        print(f"{d:3} " + " ".join(f"{perday[d].get(c, 0):>10}" for c in cols))
for c in cols:
    tot[c] = sum(perday[d].get(c, 0) for d in perday)
print("TOT " + " ".join(f"{tot[c]:>10}" for c in cols))
