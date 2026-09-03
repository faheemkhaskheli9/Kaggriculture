"""Strawberry / premium concentration archetype (ladder eps 104599091, 104605846,
104673501 -- our *closest* losses).

10-17 STRAWBERRY planted once and held (ongoing crop), 0-2 hands, minimal
actions, ride the 250-330 price. Near-zero labour still out-earned our
labour-heavy plan in the close games. Tests whether we actually beat a lazy
premium plan.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "premium",
    "quadrant_target": lambda day: 1 if day < 10 else 2,
    "land_fill_gate": 0.85,
    "land_day_gate": 16,
    "hire_target": lambda day, nq, n: 2,
    "crops": {"STRAWBERRY": 0.75, "TOMATO": 0.25},
    "crop_cap": {"STRAWBERRY": 22, "TOMATO": 8},
    "animals": {},
    "sell_cap": 10,
    "premium_sell_cap": 8,
    "sell_floor_frac": 0.5,   # patient: won't dump strawberry into a dip
    "plant_fill": True,
    "reserve": 200,
})
