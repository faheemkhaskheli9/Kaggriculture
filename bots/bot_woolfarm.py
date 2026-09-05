"""Sheep/wool herd archetype (not from a specific ladder read — fills a gap:
bot_animalfarm/bot_animalfactory_v2 are both COW/GOOSE-led. WOOL (base 200)
and free fertilizer from a SHEEP-heavy herd are a distinct income shape, and
CLAUDE.md flags "don't over-crash WOOL" as a live sell-cadence concern this
pool never actually pressure-tests.

2-3 quadrants, WHEAT-heavy field purely as feed stock, a 10-SHEEP/4-GOOSE
herd bought in pairs from day 1, steady uncapped selling of WOOL/EGG/
FERTILIZER.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "woolfarm",
    "quadrant_target": lambda day: 2 if day < 8 else 3,
    "land_fill_gate": 0.45,
    "land_day_gate": 10,
    "hire_target": lambda day, nq, n: 5 if day < 3 else (11 if day < 27 else 6),
    "crops": {"WHEAT": 0.9, "CARROT": 0.1},
    "crop_cap": {},
    "animals": {"SHEEP": 10, "GOOSE": 4},
    "animals_per_turn": 2,
    "animal_buffer_base": 250,
    "animal_buffer_per_head": 50,
    "animal_min_quadrants": 1,
    "sell_cap": 16,
    "premium_sell_cap": 12,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 180,
})
