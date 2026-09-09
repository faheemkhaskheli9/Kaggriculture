"""gooserush -- lean on GOOSE/EGG for the fastest possible animal cash flow
(EGG first-yields day 4, vs day 8 for COW milk), pair it with an early TOMATO
block, and keep a compact 2-quadrant field. A different economic tempo from
the cow/sheep-heavy herd bots: money comes in early and steadily rather than
after a day-8 milk ramp. Stresses our early-game vs an opponent that is
liquid and buying land/hands sooner than the animal_factory shape.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "gooserush",
    "quadrant_target": lambda day: 1 if day < 4 else 2,
    "land_fill_gate": 0.6,
    "land_day_gate": 12,
    "hire_target": lambda day, nq, n: 3 if day < 3 else (10 if day < 27 else 4),
    "crops": lambda day: (
        {"WHEAT": 1.0} if day < 4 else {"WHEAT": 0.35, "TOMATO": 0.65}),
    "crop_cap": {},
    "animals": {"GOOSE": 10, "COW": 2},
    "animals_per_turn": 2,
    "animal_buffer_base": 150,
    "animal_buffer_per_head": 40,
    "animal_min_quadrants": 1,
    "sell_cap": 16,
    "premium_sell_cap": 12,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 130,
})
