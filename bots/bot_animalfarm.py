"""Animal + fertilizer factory archetype (ladder eps 104596563, 104597389,
104598247, 104705712, 104604109).

3 quadrants, a cow/goose/sheep herd, wheat only for feed, sell FERTILIZER +
MILK + EGG + WOOL steadily, CARE daily. On the ladder this archetype beat us
40k-74k vs 13k-29k; this reproduction is deliberately conservative (~20-35k) but
faithful in shape -- animal-dominated, fertilizer-selling, low replant labour.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "animalfarm",
    "quadrant_target": lambda day: 2 if day < 11 else 3,
    "land_fill_gate": 0.5,
    "land_day_gate": 11,
    "hire_target": lambda day, nq, n: 3 if day < 3 else (5 if day < 26 else 2),
    "crops": {"WHEAT": 0.8, "STRAWBERRY": 0.2},
    "crop_cap": {"STRAWBERRY": 6},
    "animals": {"COW": 5, "GOOSE": 3},
    "sell_cap": 16,
    "premium_sell_cap": 10,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 250,
})
