"""Melon monoculture archetype (ladder eps 104601612, 104706502, opp in 104605023).

One or two quadrants, ~19 melon on a tight replant loop, few hands, sell in
10-15 unit batches. Beat our Gen A 30k-37k vs 12k-23k. Tests our response to a
single-product glut (melon crashes below 50 on any oversupply).
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "melonmono",
    "quadrant_target": lambda day: 1 if day < 6 else 2,
    "land_fill_gate": 0.7,
    "land_day_gate": 14,
    "hire_target": lambda day, nq, n: 5 if day < 26 else 2,
    "crops": {"MELON": 1.0},
    "crop_cap": {},
    "animals": {},
    "sell_cap": 13,           # batches, not a flood
    "premium_sell_cap": 13,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 120,
})
