"""pricecrash -- flood the shared market with the two crops whose price curves
collapse hardest on glut (CARROT: few consumers; MELON: square curve) and dump
every turn with no floor. A denial archetype: it is not trying to maximise its
own coins so much as to keep the shared premium/base prices suppressed so our
agent's produce sells for less. Stresses our market resilience and whether we
over-rely on scarcity-ceiling pricing that a hostile opponent can deny.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "pricecrash",
    "quadrant_target": lambda day: 2 if day < 6 else 3,
    "land_fill_gate": 0.45,
    "land_day_gate": 10,
    "hire_target": lambda day, nq, n: 4 if day < 3 else (11 if day < 27 else 4),
    "crops": {"CARROT": 0.5, "MELON": 0.5},
    "crop_cap": {},
    "animals": {},
    "sell_cap": 40,          # dump hard every turn
    "premium_sell_cap": 30,
    "sell_floor_frac": 0.0,  # never hold for a better price -- the point is the crash
    "plant_fill": True,
    "reserve": 100,
})
