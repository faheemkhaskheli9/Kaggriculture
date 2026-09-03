"""C2 -- animal + fertilizer factory contender (PLAN_CONTENDERS.md section 4).

Mirrors the ladder archetype that scored 38k-74k: 3-4 quadrants, a big herd
(COW 12 / GOOSE 4 / SHEEP 3) placed and *producing* by ~day 10, wheat grown
only as feed, CARE every animal every day, and a steady spread sale of
FERTILIZER + MILK + EGG + WOOL. Every surviving animal also drops 1 fertilizer/
day for free even unfed.

The engine's animal crew already sweeps FEED -> CARE -> COLLECT_FERTILIZER ->
HARVEST each day, and `build_tasks` emits COLLECT_FERTILIZER + HARVEST as generic
tasks any idle hand can grab, so CARE coverage comes for free once the herd is
placed. The engine's default sell logic already caps the contested lines
(MILK/WOOL/FERTILIZER) at 8/turn and skips them below 0.5x base -- exactly the
"spread sale" this archetype needs -- so no sell overrides here.

Key risk (memory / PLAN_GOLD): buying animals too early on the $3000 start
strands cash for ~18 days. `_animal_target_fn` below ramps the herd cap by day
(2 -> 6 -> 12 -> 16) so the per-turn money gate paces the purchases instead of
draining the account on day 1.

    python test.py --games 30 --candidate contenders/c_animalfactory.py \
        --incumbent main.py --opponents starter main_v5.py bots/bot_wheatflood.py
"""
from _engine import make_agent, _placed_animal_counts, demand_counts


def _hire_fn(day, nq):
    if day < 3:
        return 6
    if day < 6:
        return 9
    if day < 27:
        return 13                     # 14 units -- big herd + crop crew + crew
    if day < 29:
        return 8
    return 0


def _land_ok_fn(nth, day, fill, money, cost):
    # 3 quadrants by ~day 8; the $4k one only if genuinely rich and not late.
    if nth < 2:
        return day <= 14 and fill >= 0.45 and money >= cost + 700 + 300 * nth
    return 8 <= day <= 18 and fill >= 0.55 and money >= cost + 3000


def _animal_target_fn(obs, me):
    day = obs.get("day", 0)
    have = _placed_animal_counts(me)
    if day > 18:
        return dict(have)                       # freeze; hold what we have
    opp = obs["farms"][1 - obs["player"]]
    opp_animals = sum(1 for row in opp.get("tiles", []) for t in row
                      if isinstance(t, dict) and t.get("animal"))
    if day >= 7 and opp_animals >= 5:
        # opponent is also an animal farm -> milk/wool floor to ~$5 under mutual
        # dumping; keep just the free-fertilizer + egg value.
        return {"COW": max(have["COW"], 3), "GOOSE": max(have["GOOSE"], 3)}
    total_cap = 2 if day < 4 else (6 if day < 8 else (12 if day < 12 else 16))
    dem = demand_counts(obs)
    want = [("COW", 12), ("GOOSE", 4), ("SHEEP", 3 if dem["WOOL"] else 1)]
    out, tot = {}, 0
    for a, w in want:
        take = max(have[a], min(w, total_cap - tot))
        if take > 0:
            out[a] = take
            tot += take
    return out


agent = make_agent({
    "name": "animalfactory",
    "use_animals": True,
    "hire_fn": _hire_fn,
    "land_ok_fn": _land_ok_fn,
    "animal_target_fn": _animal_target_fn,
    "crop_cfg": {
        # wheat = feed + early cash; carrot = week-1 liquidity only; a strawberry
        # block for a non-contested premium line alongside the animal products.
        "WHEAT":      {"early": 0.55, "main": 0.42},
        "CARROT":     {"early": 0.30, "main_demand": 0.05, "late": (22, 0.18)},
        "STRAWBERRY": {"early": 0.0, "main": 0.34, "main_demand": 0.05, "min_day": 4},
        "TOMATO":     {"early": 0.15, "main": 0.20, "main_demand": 0.05, "late_mul": (21, 0.7)},
    },
    "seed_cap": 40,
    "seed_lookahead": 4,
})
