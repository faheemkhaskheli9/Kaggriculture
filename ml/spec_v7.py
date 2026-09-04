"""Search space for ``ml/engine_v7.py`` (the faithful ``main.py`` v7 fork).

PLAN_ML_IMPROVE.md Lever A1 + B. The v7 engine config is already a **flat**
dict, so ``params_to_config_v7`` is just clamp-and-passthrough -- the optimiser's
flat param dict *is* the engine config. Every default here equals the v7
hard-coded value, so ``default_params_v7()`` reproduces ``main.py`` exactly.

``PHASE1_V7`` = the L1-L5 economy levers from ``docs/PLAN_LADDER_ECON.md`` (the
matchup that decides the ladder). ``PHASE2_V7`` = every searchable knob.
"""
from __future__ import annotations

from ml.engine_v7 import DEFAULT_CONFIG_V7

# name -> (low, high, default, is_int).  default MUST match DEFAULT_CONFIG_V7.
PARAM_SPACE_V7: dict[str, tuple[float, float, float, bool]] = {
    # --- L1: working-capital reserve curve ---
    "reserve_ramp_base":   (0, 800, 200, True),
    "reserve_ramp_slope":  (0, 400, 150, True),
    "reserve_ramp_cap":    (400, 3000, 1400, True),
    "reserve_ramp_cutday": (8, 24, 16, True),
    "reserve_mid":         (0, 800, 200, True),
    "reserve_late":        (0, 300, 60, True),
    "seed_cap_early":      (100, 1200, 400, True),
    "seed_cap_late":       (200, 2000, 800, True),
    "seed_cap_splitday":   (4, 20, 10, True),
    # --- L1/L4: hiring (labour ceiling) ---
    "hire_early":          (2, 10, 6, True),
    "hire_q1":             (3, 12, 7, True),
    "hire_q2":             (5, 14, 10, True),
    "hire_full":           (8, 16, 13, True),
    "hire_winddown_day":   (22, 29, 27, True),
    "hire_winddown":       (0, 13, 8, True),
    # --- M1: land gates ---
    "land_fill_23":        (0.2, 0.9, 0.55, False),
    "land_fill_4":         (0.3, 0.95, 0.62, False),
    "land_day_23_max":     (8, 26, 18, True),
    "land_day_4_min":      (4, 16, 8, True),
    "land_day_4_max":      (12, 28, 20, True),
    "land_cash_23_base":   (0, 1500, 400, True),
    "land_cash_4_extra":   (500, 5000, 2500, True),
    # --- L2: herd pacing ---
    "animal_buf_base":     (0, 1500, 300, True),
    "animal_buf_per_head": (0, 400, 150, True),
    "animal_freeze_day":   (10, 29, 17, True),
    "opp_animal_thresh":   (2, 12, 4, True),
    "opp_animal_by_day":   (3, 16, 7, True),
    "a_COW":               (0, 18, 9, True),
    "a_GOOSE":             (0, 8, 2, True),
    "a_SHEEP_wool":        (0, 8, 2, True),
    "ac_COW":              (0, 12, 3, True),
    "ac_GOOSE":            (0, 8, 3, True),
    "ac_SHEEP":            (0, 8, 0, True),
    "animal_cap_q1":       (0, 8, 3, True),
    "animal_cap_q2":       (2, 14, 8, True),
    "animal_cap_full":     (6, 24, 13, True),
    "animal_cap_contested": (2, 12, 6, True),
    # --- L3/M4: sell cadence ---
    "sell_keep_premium":   (0.5, 1.1, 0.80, False),
    "sell_keep_staple":    (0.4, 1.0, 0.72, False),
    "sell_cap_premium":    (2, 30, 6, True),
    "sell_cap_staple":     (6, 60, 16, True),
    "sell_cap_contested":  (2, 40, 8, True),
    "sell_glut_thresh":    (1.0, 2.5, 1.4, False),
    "sell_glut_mult_max":  (1.5, 8.0, 4.0, False),
    "contested_floor_frac": (0.0, 0.9, 0.5, False),
    "sell_min_frac":       (0.2, 0.9, 0.55, False),
    "full_dump_day":       (24, 29, 28, True),
    # --- crop schedule ---
    "early_day":           (3, 12, 7, True),
    "w_e_WHEAT":           (0.0, 1.0, 0.50, False),
    "w_e_CARROT":          (0.0, 1.0, 0.28, False),
    "w_e_TOMATO":          (0.0, 1.0, 0.16, False),
    "w_e_STRAWBERRY":      (0.0, 1.0, 0.12, False),
    "w_m_WHEAT":           (0.0, 1.0, 0.24, False),
    "w_m_TOMATO":          (0.0, 1.0, 0.44, False),
    "w_m_STRAWBERRY":      (0.0, 1.0, 0.30, False),
    "w_m_MELON":           (0.0, 0.6, 0.10, False),
    "late_carrot_bonus":   (0.0, 0.6, 0.22, False),
    "tomato_late_mult":    (0.3, 1.0, 0.7, False),
    "cap_MELON":           (0, 12, 5, True),
    "cap_CARROT":          (0, 20, 10, True),
    # --- L4: field-fill / weed discipline priorities ---
    "pr_water_comfort":    (1500, 4000, 2600, False),
    "pr_weed":             (0, 4000, 2200, False),
    "pr_plant":            (500, 5000, 2400, False),
    "plant_room_per_unit": (10, 34, 22, True),
    "plant_stop_day":      (22, 29, 27, True),
}

# quick self-check: every default matches the engine's hard-coded value
_MISMATCH = {k: (v[2], DEFAULT_CONFIG_V7.get(k))
             for k, v in PARAM_SPACE_V7.items()
             if k in DEFAULT_CONFIG_V7 and abs(float(v[2]) - float(DEFAULT_CONFIG_V7[k])) > 1e-9}
if _MISMATCH:  # pragma: no cover - guards against silent drift
    raise AssertionError(f"spec_v7 defaults disagree with engine_v7: {_MISMATCH}")

PHASE1_V7 = [
    "reserve_ramp_base", "reserve_ramp_slope", "reserve_ramp_cap", "reserve_mid",
    "seed_cap_early", "seed_cap_late",
    "hire_full", "land_fill_23", "land_fill_4",
    "animal_buf_base", "animal_buf_per_head", "a_COW",
    "sell_cap_staple", "sell_cap_contested", "sell_keep_staple", "contested_floor_frac",
]

# Focused response space for the ladder's dominant animal-factory matchup.
# Keep this deliberately smaller than PHASE2: it gives the optimiser enough
# control over herd tempo, species mix, feed liquidity, and contested sales
# without letting unrelated crop/field knobs hide the causal signal.
ANIMAL_V7 = [
    "reserve_ramp_base", "reserve_ramp_slope", "reserve_ramp_cap", "reserve_mid",
    "seed_cap_early", "seed_cap_late", "hire_q2", "hire_full",
    "animal_buf_base", "animal_buf_per_head", "animal_freeze_day",
    "opp_animal_thresh", "opp_animal_by_day",
    "a_COW", "a_GOOSE", "a_SHEEP_wool",
    "ac_COW", "ac_GOOSE", "ac_SHEEP",
    "animal_cap_q1", "animal_cap_q2", "animal_cap_full", "animal_cap_contested",
    "sell_cap_contested", "contested_floor_frac", "full_dump_day",
]
PHASE2_V7 = list(PARAM_SPACE_V7)


def default_params_v7() -> dict[str, float]:
    return {k: v[2] for k, v in PARAM_SPACE_V7.items()}


def clamp_params_v7(p: dict) -> dict:
    out = {}
    for k, (lo, hi, dflt, is_int) in PARAM_SPACE_V7.items():
        v = float(p.get(k, dflt))
        v = min(hi, max(lo, v))
        out[k] = int(round(v)) if is_int else v
    return out


def params_to_config_v7(p: dict) -> dict:
    """Flat param dict -> engine config. The v7 config is flat, so this is just
    a clamp; build_agent_v7 merges the result over DEFAULT_CONFIG_V7."""
    return clamp_params_v7(p)


def to_unit_v7(p: dict, names: list[str]):
    x = []
    for k in names:
        lo, hi, _, _ = PARAM_SPACE_V7[k]
        x.append((float(p[k]) - lo) / (hi - lo) if hi > lo else 0.0)
    return x


def from_unit_v7(x, names: list[str], base: dict | None = None) -> dict:
    out = dict(base or default_params_v7())
    for k, xi in zip(names, x):
        lo, hi, _, is_int = PARAM_SPACE_V7[k]
        v = lo + min(1.0, max(0.0, float(xi))) * (hi - lo)
        out[k] = int(round(v)) if is_int else v
    return out
