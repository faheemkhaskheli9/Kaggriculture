"""Strong animal + fertilizer factory -- the ladder archetype that actually
beats us (60k-110k+), not the deliberately-soft ``bot_animalfarm`` (~20-35k).

From ``knowledge-base/06 s2`` + ``docs/PLAN_LADDER_ECON.md s4.1``:

* 3 quadrants opened fast (by ~day 8), field filled with WHEAT as feed + cash,
* WHEAT sold every turn from ~day 2 -- that cash flow *funds* the herd instead
  of the $3000 start draining on day 1,
* 2 animals/turn in the dawn window from ~day 3 to a ~16-18 head herd
  (COW 12 / GOOSE 3 / SHEEP 3) placed and producing by ~day 10,
* FERTILIZER (1/head/day, free) + MILK + WOOL + EGG sold every turn, no floor,
* 13 hands held through the season so the herd + wheat field stay covered.

This is the gate opponent for every ``main.py`` economy change (PLAN_LADDER_ECON
s4). If a candidate can't hold >= 45% score-rate against *this*, it won't climb
the real ladder -- the local ``starter`` / self-play gate has been wrong about
economy changes for the whole 333->477 score history.

    python test.py --games 40 --gate --candidate main.py
    python compete.py --games 20 --opponent bots/bot_animalfactory_v2.py
"""
from _kagri_botlib import make_agent

agent = make_agent({
    "name": "animalfactory_v2",
    # --- land: 3 quadrants fast, expand on a low fill gate ---
    #  NOTE: _kagri_botlib reserves ALL target-herd tiles upfront, so on the
    #  1-quadrant early field the plantable count is tiny -- the herd MUST be
    #  allowed to buy from day 1 (animal_min_quadrants: 1) or the whole engine
    #  deadlocks (land fill-gate never reached, animals never bought). Tuning
    #  min_quadrants up or the herd target down both starve it. This config is
    #  the stable envelope: ~42k vs starter, faithful archetype shape.
    "quadrant_target": lambda day: 2 if day < 5 else 3,
    "land_fill_gate": 0.40,
    "land_day_gate": 8,
    # --- labour: full crew through the productive season ---
    "hire_target": lambda day, nq, n: 6 if day < 3 else (
        13 if day < 27 else (8 if day < 29 else 0)),
    # --- crops: wheat is feed + the working-capital engine; a held premium block ---
    "crops": {"WHEAT": 0.80, "STRAWBERRY": 0.20},
    "crop_cap": {"STRAWBERRY": 12},
    # --- herd: buy from day 1 in pairs, thin running-cost buffer (see NOTE) ---
    "animals": {"COW": 12, "GOOSE": 3, "SHEEP": 3},
    "animals_per_turn": 2,
    "animal_buffer_base": 200,
    "animal_buffer_per_head": 40,
    "animal_min_quadrants": 1,
    # --- selling: steady dump every turn, no price floor (the archetype's shape) ---
    "sell_cap": 20,
    "premium_sell_cap": 10,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 150,
})
