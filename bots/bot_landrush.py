"""landrush -- grab all 4 quadrants as fast as cash allows, then spread a big
generic field thin across them. Models a ladder opponent that out-scales on
land rather than herd or premium focus; stresses our coverage/labour ceiling
when the opponent is contesting the whole 10x10 board.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "landrush",
    # 2nd quad almost immediately, 3rd by ~day 5, 4th by ~day 9, on a very low
    # fill gate -- buy land the moment it is barely affordable.
    "quadrant_target": lambda day: 2 if day < 3 else (3 if day < 6 else 4),
    "land_fill_gate": 0.20,
    "land_day_gate": 5,
    "hire_target": lambda day, nq, n: 4 if day < 3 else (12 if day < 27 else 5),
    "crops": {"WHEAT": 0.45, "TOMATO": 0.30, "STRAWBERRY": 0.25},
    "crop_cap": {},
    "animals": {"COW": 3, "GOOSE": 2},
    "animals_per_turn": 1,
    "animal_buffer_base": 250,
    "animal_buffer_per_head": 70,
    "animal_min_quadrants": 2,
    "sell_cap": 18,
    "premium_sell_cap": 10,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 120,
})
