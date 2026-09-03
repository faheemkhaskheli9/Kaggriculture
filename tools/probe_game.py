import importlib.util, sys, collections
from kaggle_environments import make

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m
    spec.loader.exec_module(m); return m.agent

cand = load(sys.argv[1] if len(sys.argv)>1 else "main.py", "cand")
env = make("kaggriculture", configuration={"episodeSteps":720, "seed":10000001}, debug=True)
env.run([cand, "starter"])
steps = env.steps
print(f"{'d':>3} {'money':>8} {'plants':>6} {'weeds':>5} {'anim':>4} {'quads':>5} {'hands':>5} {'seeds':>18} {'shed_top':>28}")
for d in range(30):
    i = min(d*24 + 1, len(steps)-1)
    st = steps[i][0]
    obs = st.observation
    fm = obs["farms"][0]
    priv = obs["private"]
    tiles = fm["tiles"]
    pc = collections.Counter(); weeds=anim=0
    for row in tiles:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind")=="PLANT": pc[t["crop"]]+=1
                elif t.get("kind")=="WEED": weeds+=1
                if t.get("animal"): anim+=1
    seeds = {k:v for k,v in (priv.get("seeds") or {}).items() if v}
    shed = {k:int(v) for k,v in sorted((priv.get("shed") or {}).items(), key=lambda x:-x[1]) if v}
    shed_top = dict(list(shed.items())[:4])
    print(f"{d:>3} {fm['money']:>8.0f} {sum(pc.values()):>6} {weeds:>5} {anim:>4} {len(fm.get('unlocked_quadrants',[])):>5} {len(fm.get('hands',[])):>5} {str(seeds):>18} {str(shed_top):>28}  mix={dict(pc)}")
final = steps[-1]
print("FINAL me", final[0].observation["farms"][0]["money"], "opp", final[1].observation["farms"][1]["money"])
