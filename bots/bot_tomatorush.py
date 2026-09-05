"""Tomato-ongoing rush archetype (not from a specific ladder read — fills a
gap: bot_wheatflood floods a non-ongoing crop, bot_premium holds an ongoing
crop lazily with 2 hands. Nobody in the pool runs an ongoing crop at
wheatflood-style throughput. TOMATO is cheap to seed (50), yields every day
once mature (interval 1) and sells 60-500+ under scarcity — this tests our
response to sustained mid-tier ongoing production instead of a crash-prone
batch crop or a lazy premium hold.

WHEAT-bootstrapped like bot_animalfactory_v2: TOMATO's first yield is day 8,
so going TOMATO-only from turn 0 at wheatflood-level hire/land spend just
bankrupts the bot before it ever harvests (hands reset to 0 every day in this
engine -- rehiring is the recurring cost, and with $0 on hand it can't even
afford one hire, a death spiral confirmed in local testing: money hit $0 by
day 4 and stayed there past day 20). WHEAT carries cash flow through the
first week, then the field pivots almost entirely to TOMATO once quadrant 2
is up, at full wheatflood-style throughput and no price floor.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "tomatorush",
    "quadrant_target": lambda day: 1 if day < 5 else (2 if day < 10 else 3),
    "land_fill_gate": 0.5,
    "land_day_gate": 14,
    "hire_target": lambda day, nq, n: 3 if day < 2 else (
        6 if day < 8 else (11 if day < 27 else 5)),
    "crops": lambda day: {"WHEAT": 1.0} if day < 6 else {"WHEAT": 0.2, "TOMATO": 0.8},
    "crop_cap": {},
    "animals": {},
    "sell_cap": 18,
    "premium_sell_cap": 18,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 150,
})
