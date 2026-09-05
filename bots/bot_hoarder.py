"""Cash-hoarder / passive-banker archetype (not from a specific ladder read —
fills a gap: every existing bot is at least moderately active. This one tests
whether our early-game spend (land, hires, herd buys — the recurring
"day-2 cash-crater" symptom in TASKS.md/PLAN_RATING_IMPROVEMENT.md) actually
buys enough of an edge, or whether a nearly-inactive opponent that just sits
on cash and only sells into strong prices can win on attrition.

Stays at 1 quadrant essentially forever (quadrant_target never rises), a
skeleton crew (1-2 hands), a small WHEAT/STRAWBERRY patch, no animals, a very
high reserve, and a high sell-price floor (0.6x base) so it rarely dumps
into a soft market. Low throughput, low risk, low labour cost.
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "hoarder",
    "quadrant_target": lambda day: 1,
    "land_fill_gate": 0.9,
    "land_day_gate": 30,
    "hire_target": lambda day, nq, n: 1 if day < 20 else 2,
    "crops": {"WHEAT": 0.6, "STRAWBERRY": 0.4},
    "crop_cap": {"STRAWBERRY": 10},
    "animals": {},
    "sell_cap": 6,
    "premium_sell_cap": 6,
    "sell_floor_frac": 0.6,
    "plant_fill": True,
    "reserve": 400,
})
