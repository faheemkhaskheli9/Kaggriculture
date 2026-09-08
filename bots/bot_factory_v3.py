"""bot_factory_v3 -- animal/fertilizer factory rebuilt from the REAL ladder
opponents that beat main.py, not the archetype sketch in bot_animalfactory_v2.

Mined from the 12 animal_factory losses on sub 56029879
(scratchpad/mine_factory_opp.py). The winning opponent trajectory (median):

    day   money  quads  herd  plants
      1      95    1.0   4.0    15      <- 4 animals bought by day 1, cash ~$20-95
      8     379    2.0   6.0    25
     10    1602    2.0   8.0    30
     12    9168    2.0  10.0    37      <- breakout at day 10-12
     15    6918    3.0  14.0    45
     20   26615    3.0  16.0    48
     29   90036    3.0  16.0    15
    opp movement 41-52% (vs our 63%), weeds left to pile up late.

Key differences from bot_animalfactory_v2 (which goes 0-15 vs main.py because it
deadlocks -- reserves ~all tiles on 1 quadrant, then a fat animal buffer stalls
the herd once cash craters on day 1):

  * near-zero cash buffer for animal buys -- the real opp buys down to ~$0,
  * 2 animals/turn from day 0, herd target ~16, from quadrant 1,
  * animal_reserve_leave_plantable=8 so the field still plants on 1 quadrant,
  * MELON-heavy early field for fast cash, shift to WHEAT+STRAWBERRY once the
    herd income is compounding,
  * 3-4 quadrants, low fill-gate, ~13 hands, steady no-floor selling.

Purpose: an "unsaturated" local factory opponent for Gate B -- main.py should
NOT go ~100% against this (TASKS.md EVAL-FACTORY-1). Provenance above; re-mine
if top-of-ladder factory play shifts.

    python compete.py --games 20 --opponent bots/bot_factory_v3.py
"""
from _kagri_botlib import make_agent


def _crops(day):
    if day < 8:
        return {"MELON": 0.45, "WHEAT": 0.55}
    if day < 16:
        return {"WHEAT": 0.55, "STRAWBERRY": 0.30, "MELON": 0.15}
    return {"WHEAT": 0.60, "STRAWBERRY": 0.40}


agent = make_agent({
    "name": "factory_v3",
    # --- land: 2 quads fast, 3 by ~day 12, 4 later; expand on a low fill gate ---
    "quadrant_target": lambda day: 2 if day < 5 else (3 if day < 13 else 4),
    "land_fill_gate": 0.35,
    "land_day_gate": 7,
    # --- labour: full crew through the productive season ---
    "hire_target": lambda day, nq, n: 6 if day < 3 else (
        13 if day < 27 else (8 if day < 29 else 0)),
    # --- crops: melon-heavy early cash -> wheat feed + held strawberry block ---
    "crops": _crops,
    "crop_cap": {"MELON": 12, "STRAWBERRY": 18},
    # --- herd: ~14 head, 2/turn from day 1, thin survival buffer. A literal
    #     $0 buffer (the raw mined shape) bankrupts the botlib into a feed-miss
    #     escape spiral -- the engine isn't a real 2850 agent and can't ride
    #     out $20 cash the way the ladder opponent does. This is the tuned
    #     envelope: aggressive but solvent. ---
    "animals": {"COW": 9, "SHEEP": 3, "GOOSE": 2},
    "animals_per_turn": 2,
    "animal_buffer_base": 120,
    "animal_buffer_per_head": 25,
    "animal_min_quadrants": 1,
    "animal_reserve_leave_plantable": 8,
    # --- selling: steady dump every turn, no price floor ---
    "sell_cap": 20,
    "premium_sell_cap": 10,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 60,
})
