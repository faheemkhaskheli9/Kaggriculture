from kaggle_environments import make

env = make("kaggriculture", configuration={
    # "episodeSteps": 720,
    # "startingMoney": 3000,
    # "turnsPerDay": 24,
    "seed": 0
    }, debug=False)
# env.run(["main.py", "main_p2.py"])
# env.run(["main.py", "main_p3.py"])
# env.run(["experiments/main_v6.py", "main_p3.py"])
env.run(["main.py", "main.py"])
# env.run(["main.py", "main_v3.py"])

# View result
final = env.steps[-1]
for i, s in enumerate(final):
    print(f"Player {i}: reward={s.reward}, status={s.status}")

# Render in a notebook (needs IPython; skip when running as a plain script)
# try:
#     env.render(width=1200, height=800)
# except ModuleNotFoundError:
#     pass

# # Dump a replay JSON for the visualizer / offline analysis
# import json
# with open("replay.json", "w") as f:
#     json.dump(env.toJSON(), f)
# print("wrote replay.json")
