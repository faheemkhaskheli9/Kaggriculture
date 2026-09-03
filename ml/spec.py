"""Search space for the Kaggriculture engine.

The optimiser only ever sees a **flat dict of named scalars** (``params``).
``params_to_config`` expands that into the nested ``ml/engine.py`` config.
``to_unit`` / ``from_unit`` map params <-> a normalised [0,1] vector for CMA-ES.

Add a knob = one row in ``PARAM_SPACE`` + wiring in ``params_to_config``.
"""
from __future__ import annotations

# name -> (low, high, default, is_int)
PARAM_SPACE: dict[str, tuple[float, float, float, bool]] = {
    # land / labour
    "quadrant_target":       (2, 4, 4, True),
    "land_day_ne":           (2, 12, 4, True),
    "land_day_sw":           (4, 18, 8, True),
    "land_day_se":           (6, 24, 11, True),
    "land_fill_ne":          (0.2, 0.9, 0.50, False),
    "land_fill_sw":          (0.2, 0.9, 0.55, False),
    "land_fill_se":          (0.2, 0.9, 0.62, False),
    "hire_a":                (0.0, 12.0, 6.0, False),
    "hire_b":                (0.0, 1.0, 0.35, False),
    "hire_cap":              (6, 18, 13, True),
    # crop weights per phase (early d0-6, mid d7-19, late d20+)
    "w_early_WHEAT":         (0.0, 1.0, 0.50, False),
    "w_early_CARROT":        (0.0, 1.0, 0.28, False),
    "w_early_TOMATO":        (0.0, 1.0, 0.16, False),
    "w_early_STRAWBERRY":    (0.0, 1.0, 0.06, False),
    "w_early_MELON":         (0.0, 1.0, 0.00, False),
    "w_mid_WHEAT":           (0.0, 1.0, 0.20, False),
    "w_mid_CARROT":          (0.0, 1.0, 0.06, False),
    "w_mid_TOMATO":          (0.0, 1.0, 0.30, False),
    "w_mid_STRAWBERRY":      (0.0, 1.0, 0.32, False),
    "w_mid_MELON":           (0.0, 1.0, 0.12, False),
    "w_late_WHEAT":          (0.0, 1.0, 0.45, False),
    "w_late_CARROT":         (0.0, 1.0, 0.10, False),
    "w_late_TOMATO":         (0.0, 1.0, 0.30, False),
    "w_late_STRAWBERRY":     (0.0, 1.0, 0.15, False),
    "w_late_MELON":          (0.0, 1.0, 0.00, False),
    "melon_cap":             (0, 12, 5, True),
    "plant_room_per_unit":   (10, 30, 18, True),
    "reserve":               (0, 600, 150, True),
    # animals
    "a_COW":                 (0, 16, 10, True),
    "a_GOOSE":               (0, 6, 3, True),
    "a_SHEEP":               (0, 8, 2, True),
    "ac_COW":                (0, 8, 3, True),
    "ac_GOOSE":              (0, 6, 3, True),
    "ac_SHEEP":              (0, 6, 0, True),
    "opp_animal_thresh":     (2, 10, 4, True),
    "opp_animal_by_day":     (3, 14, 7, True),
    "animal_freeze_day":     (10, 29, 17, True),
    # selling
    "sell_grow_staple":      (0.4, 1.0, 0.72, False),
    "sell_grow_premium":     (0.5, 1.1, 0.80, False),
    "sell_hardcap":          (10, 120, 60, True),
    "contested_cap":         (2, 30, 8, True),
    "contested_floor_frac":  (0.0, 0.9, 0.5, False),
    # endgame
    "endgame_liquidate_hour": (0, 23, 12, True),
    "endgame_dropA_hour":    (0, 23, 16, True),
    "endgame_dropB_hour":    (0, 23, 19, True),
    # assignment priority weights
    "w_on_tile":             (500, 8000, 4000, False),
    "w_in_zone":             (0, 3000, 600, False),
    "w_dist":                (0, 200, 55, False),
    "pr_plant":              (500, 5000, 1500, False),
    "pr_weed":               (0, 4000, 800, False),
    "pr_collect_fert":       (500, 5000, 2600, False),
    "pr_care":               (0, 5000, 2400, False),
    "pr_feed":               (3000, 9000, 7000, False),
}

# Phase 1 = the cheap, highest-signal subset (the PLAN_ML_MODELS "M1/M4" levers).
PHASE1_NAMES = [
    "land_day_ne", "land_day_sw", "land_day_se", "hire_a", "hire_b", "hire_cap",
    "sell_grow_staple", "sell_grow_premium", "sell_hardcap",
    "contested_cap", "contested_floor_frac", "a_COW", "a_GOOSE", "a_SHEEP",
]
PHASE2_NAMES = list(PARAM_SPACE)


def default_params() -> dict[str, float]:
    return {k: v[2] for k, v in PARAM_SPACE.items()}


def clamp_params(p: dict) -> dict:
    out = {}
    for k, (lo, hi, dflt, is_int) in PARAM_SPACE.items():
        v = float(p.get(k, dflt))
        v = min(hi, max(lo, v))
        out[k] = int(round(v)) if is_int else v
    return out


def params_to_config(p: dict) -> dict:
    p = clamp_params(p)

    def phase(pre):
        return {c: p[f"w_{pre}_{c}"] for c in
                ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
                if p[f"w_{pre}_{c}"] > 1e-4}

    return {
        "quadrant_target": p["quadrant_target"],
        "land_day": [p["land_day_ne"], p["land_day_sw"], p["land_day_se"]],
        "land_fill": [p["land_fill_ne"], p["land_fill_sw"], p["land_fill_se"]],
        "hire_a": p["hire_a"], "hire_b": p["hire_b"], "hire_cap": p["hire_cap"],
        "crop_schedule": [[0, phase("early")], [7, phase("mid")], [20, phase("late")]],
        "crop_cap": {"MELON": p["melon_cap"]},
        "plant_room_per_unit": p["plant_room_per_unit"],
        "reserve": p["reserve"],
        "animals": {"COW": p["a_COW"], "GOOSE": p["a_GOOSE"], "SHEEP": p["a_SHEEP"]},
        "animals_contested": {"COW": p["ac_COW"], "GOOSE": p["ac_GOOSE"], "SHEEP": p["ac_SHEEP"]},
        "opp_animal_thresh": p["opp_animal_thresh"],
        "opp_animal_by_day": p["opp_animal_by_day"],
        "animal_freeze_day": p["animal_freeze_day"],
        "sell_grow_staple": p["sell_grow_staple"],
        "sell_grow_premium": p["sell_grow_premium"],
        "sell_hardcap": p["sell_hardcap"],
        "contested_items": ["MILK", "WOOL", "FERTILIZER"],
        "contested_cap": p["contested_cap"],
        "contested_floor_frac": p["contested_floor_frac"],
        "endgame_liquidate_hour": p["endgame_liquidate_hour"],
        "endgame_dropA_day": 29, "endgame_dropA_hour": p["endgame_dropA_hour"],
        "endgame_dropB_day": 28, "endgame_dropB_hour": p["endgame_dropB_hour"],
        "w_on_tile": p["w_on_tile"], "w_in_zone": p["w_in_zone"], "w_dist": p["w_dist"],
        "pr_plant": p["pr_plant"], "pr_weed": p["pr_weed"],
        "pr_collect_fert": p["pr_collect_fert"], "pr_care": p["pr_care"],
        "pr_feed": p["pr_feed"],
    }


def to_unit(p: dict, names: list[str]):
    x = []
    for k in names:
        lo, hi, _, _ = PARAM_SPACE[k]
        x.append((float(p[k]) - lo) / (hi - lo) if hi > lo else 0.0)
    return x


def from_unit(x, names: list[str], base: dict | None = None) -> dict:
    out = dict(base or default_params())
    for k, xi in zip(names, x):
        lo, hi, _, is_int = PARAM_SPACE[k]
        v = lo + min(1.0, max(0.0, float(xi))) * (hi - lo)
        out[k] = int(round(v)) if is_int else v
    return out
