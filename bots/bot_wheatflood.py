"""Wheat-flood archetype (ladder eps 104708217, 104707373, Crop Dusta).

Every quadrant, ~100% wheat, sell wheat to the order cap every single turn,
600-1600 wheat sold per season, terminal spike. Beat our Gen A/B agents.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "wheatflood",
    "quadrant_target": lambda day: 4,
    "land_fill_gate": 0.45,
    "land_day_gate": 12,
    "hire_target": lambda day, nq, n: 3 if day < 2 else (10 if day < 27 else 4),
    "crops": {"WHEAT": 1.0},
    "crop_cap": {},
    "animals": {},
    "sell_cap": 40,          # dump wheat hard, every turn
    "premium_sell_cap": 20,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 80,
})
