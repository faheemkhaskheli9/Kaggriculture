"""Diversified generalist archetype (not from a specific ladder read — fills a
gap in the local pool: every existing bot commits hard to one resource curve
(wheat flood, melon glut, strawberry hold, animal factory). This one spreads
across 4 crops + a light mixed herd instead, so beating it can't just mean
"exploit the one thing they over-produce" — it has to mean out-executing a
balanced opponent on efficiency.

3 quadrants by mid-game, WHEAT/TOMATO/STRAWBERRY/CARROT all planted (CARROT
capped -- it crashes on the slightest oversupply), a small COW/GOOSE/SHEEP
herd for steady fertilizer + product income, moderate sell caps with a mild
price floor (patient but not a hoarder).
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "diversified",
    "quadrant_target": lambda day: 2 if day < 10 else 3,
    "land_fill_gate": 0.5,
    "land_day_gate": 12,
    "hire_target": lambda day, nq, n: 4 if day < 3 else (9 if day < 27 else 4),
    "crops": {"WHEAT": 0.35, "TOMATO": 0.30, "STRAWBERRY": 0.20, "CARROT": 0.15},
    "crop_cap": {"CARROT": 6},
    "animals": {"COW": 4, "GOOSE": 2, "SHEEP": 2},
    "animals_per_turn": 1,
    "animal_buffer_base": 300,
    "animal_buffer_per_head": 80,
    "animal_min_quadrants": 2,
    "sell_cap": 14,
    "premium_sell_cap": 10,
    "sell_floor_frac": 0.15,
    "plant_fill": True,
    "reserve": 180,
})
