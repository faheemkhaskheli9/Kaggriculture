"""C3 -- premium concentration contender (PLAN_CONTENDERS.md section 4).

Mirrors the lazy premium agent that won our *closest* ladder losses (13k-23k
coins vs our 12k-14k): ~40% STRAWBERRY + ~30% TOMATO planted once and held (both
ongoing crops, so they keep firing yield ticks with no reseed labour), ~5 hired
hands, only 2 quadrants, minimal movement, and ride the $200-330 scarcity price
on strawberry / the runaway ceiling on tomato. A small wheat/carrot block funds
week 1.

The engine's default sell logic already sells premium lines in thin price-aware
slices (cap 6/turn, keep while marginal >= 0.80x base), which is exactly the
"don't glut the scarcity price" behaviour this archetype relies on -- no sell
overrides. No animals, so no animal crew; every hand works crops.

The bet under test (PLAN_CONTENDERS section 4): whether our labour-heavy plans
actually out-earn a near-zero-labour premium hold. In the close losses they did
not. C3 is also a brutal regression opponent for coin-flip games.

    python test.py --games 30 --candidate contenders/c_premium.py \
        --incumbent main.py --opponents starter main_v5.py bots/bot_wheatflood.py
"""
from _engine import make_agent


def _hire_fn(day, nq):
    if day < 3:
        return 4
    if day < 27:
        return 5                       # 6 units total -- deliberately lean
    if day < 29:
        return 3
    return 0


def _land_ok_fn(nth, day, fill, money, cost):
    # quadrant 2 only; never buy quadrant 3 or 4 -- keep the farm small and quiet.
    return nth == 0 and day <= 12 and fill >= 0.5 and money >= cost + 700


agent = make_agent({
    "name": "premium",
    "use_animals": False,
    "hire_fn": _hire_fn,
    "land_ok_fn": _land_ok_fn,
    "crop_cfg": {
        "WHEAT":      {"early": 0.55, "main": 0.15},
        "CARROT":     {"early": 0.35, "main_demand": 0.04},
        "STRAWBERRY": {"early": 0.10, "main": 0.46, "main_demand": 0.05, "min_day": 4},
        "TOMATO":     {"early": 0.0, "main": 0.34, "main_demand": 0.05, "late_mul": (21, 0.7)},
    },
    "crop_caps_fn": lambda day, early: {"MELON": 0, "CARROT": 12 if early else 4},
    "plant_water_slack": 16,           # small field, few hands -- keep it modest
})
