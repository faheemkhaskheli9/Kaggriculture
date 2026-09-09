"""lateswing -- turtle for the first half of the season (1 quadrant, ~2 hands,
fat reserve, patient premium block), then swing hard after day 15: open to 4
quadrants, hire a full crew, and liquidate aggressively through the endgame.
Models the opponent our LEAD_AWARE_RISK work is aimed at -- one that is behind
on visible state at mid-game but surges late. Stresses whether an early coin
lead of ours actually survives to step 718.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "lateswing",
    "quadrant_target": lambda day: 1 if day < 13 else (3 if day < 18 else 4),
    "land_fill_gate": 0.55,
    "land_day_gate": 13,
    "hire_target": lambda day, nq, n: (
        2 if day < 13 else (13 if day < 28 else 4)),
    "crops": lambda day: (
        {"WHEAT": 0.4, "STRAWBERRY": 0.6} if day < 13
        else {"WHEAT": 0.2, "TOMATO": 0.4, "STRAWBERRY": 0.4}),
    "crop_cap": {},
    "animals": {"COW": 6, "SHEEP": 4},
    "animals_per_turn": 2,
    "animal_buffer_base": 200,
    "animal_buffer_per_head": 50,
    "animal_min_quadrants": 1,
    "sell_cap": 22,
    "premium_sell_cap": 8,      # patient while turtling
    "sell_floor_frac": 0.45,    # hold premium for the scarcity ceiling until the swing
    "plant_fill": True,
    "reserve": 500,             # deep buffer early; the swing spends it
})
