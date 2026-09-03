"""Vectorised Kaggriculture engine clone -- SCAFFOLD.

Steps ``B`` games in parallel with NumPy arrays. The math is transcribed from
``knowledge-base/04-engine-internals.md``; sections marked ``TODO(04-...)`` are
not implemented yet -- see ``ml/clone/README.md`` for the build order.

Fully-specified pieces that ARE implemented here: ``_shape`` / ``market_price``
(the price curve), ``town_consume``, ``decay_plants``. These are unit-tested in
``validate_clone.py`` against the installed env's own functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]
PIDX = {p: i for i, p in enumerate(PRODUCTS)}
I0 = 10000
PRICE_FLOOR = 1

# base, T, below_func, below_target, above_func, above_target   (spec: MARKET_PARAMS)
MARKET_PARAMS = {
    "WHEAT":      (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT":     (35, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO":     (60, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON":      (250, 300, "log", 0.20, "sq", 3.60),
    "EGG":        (50, 332, "hinge", 0.40, "log", 0.20),
    "MILK":       (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL":       (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}


def _shape(func, x, T):
    x = np.maximum(0.0, np.asarray(x, float))
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return np.sqrt(x)
    if func == "log":
        return np.log1p(x)
    if func == "log10":
        return np.log10(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * np.maximum(0.0, u - 1.0) ** 2
    return x


def market_price(item: str, inventory) -> np.ndarray:
    """Vectorised over an array of inventories. Matches spec §market_price."""
    base, T, bf, bt, af, at = MARKET_PARAMS[item]
    inv = np.asarray(inventory, float)
    below = inv < I0
    amp_b = bt * base / _shape(bf, T, T)
    amp_a = at * base / _shape(af, T, T)
    price = np.where(
        below,
        base + amp_b * _shape(bf, I0 - inv, T),
        base - amp_a * _shape(af, inv - I0, T),
    )
    return np.maximum(PRICE_FLOOR, np.round(price)).astype(np.int64)


@dataclass
class State:
    """Batched state for B games. Arrays are (B, ...) unless noted."""
    B: int
    step: int = 0
    seed: np.ndarray = None          # (B,) env seed, for weed/shop RNG
    money: np.ndarray = None         # (B, 2)
    market_inv: np.ndarray = None    # (B, 9)
    # board: tile-type code + per-field planes, per player
    tile_code: np.ndarray = None     # (B, 2, 10, 10) int  0 empty,1 locked,2 plant,3 weed,4 coop,5 pasture
    crop: np.ndarray = None          # (B,2,10,10) int  -1 or crop idx
    planted_day: np.ndarray = None
    watered_today: np.ndarray = None
    consec_unwatered: np.ndarray = None
    yield_units: np.ndarray = None
    fertilized_until: np.ndarray = None
    max_lifespan_step: np.ndarray = None
    animal: np.ndarray = None        # (B,2,10,10) int animal idx or -1
    placed_day: np.ndarray = None
    fed_today: np.ndarray = None
    consec_unfed: np.ndarray = None
    cared_today: np.ndarray = None
    fert_available: np.ndarray = None
    pending_care: np.ndarray = None
    # units
    farmer_xy: np.ndarray = None     # (B,2,2)
    hands_xy: np.ndarray = None      # (B,2,MAXH,2)  padded, -1 = absent
    n_hands: np.ndarray = None       # (B,2)
    unit_inv: np.ndarray = None      # (B,2,1+MAXH,9)
    shed: np.ndarray = None          # (B,2,9)
    seeds: np.ndarray = None         # (B,2,5)
    unlocked_quadrants: np.ndarray = None  # (B,2,4) bool  NW,NE,SW,SE
    hires_today: np.ndarray = None   # (B,2)
    shops: list = field(default_factory=list)  # per-game list of shop-name lists

    @classmethod
    def reset(cls, seeds, max_hands=16):
        raise NotImplementedError("TODO(04-'_initialize'): NW unlocked, $3000, "
                                  "market_inv=I0, farmer at (4,4), empty board.")


def town_consume(st: State, shop_products_by_game):
    """spec §_town_consume. shops every step%4==0 (single-product shops 2x),
    town centre every step%24==0 (all products but FERTILIZER)."""
    if st.step % 4 == 0:
        for b, shops in enumerate(shop_products_by_game):
            for prods in shops:
                mult = 2 if len(prods) == 1 else 1
                for p in prods:
                    st.market_inv[b, PIDX[p]] -= mult
    if st.step % 24 == 0:
        for p in PRODUCTS:
            if p != "FERTILIZER":
                st.market_inv[:, PIDX[p]] -= 1
    # prices are recomputed on demand via market_price(); nothing to refresh here.


def decay_plants(st: State):
    """spec §_decay_plants -- runs EVERY step. yield_units-1 every other step
    once past max_lifespan_step; ->WEED at 0."""
    is_plant = st.tile_code == 2
    has_life = st.max_lifespan_step >= 0
    due = st.step >= st.max_lifespan_step
    phase = ((st.step - st.max_lifespan_step) % 2) == 0
    hit = is_plant & has_life & due & phase
    st.yield_units[hit] -= 1
    weed = hit & (st.yield_units <= 0)
    st.tile_code[weed] = 3
    st.crop[weed] = -1


def apply_unit_actions(st: State, actions):
    raise NotImplementedError(
        "TODO(04-'_apply_unit_action'): vectorise by op type. Order of checks: "
        "move -> PASS -> DROP/PICKUP/PLACE (pre-LOCKED) -> LOCKED guard -> "
        "PLANT/WATER/HARVEST/FERTILIZE/DIG/BUILD_*/FEED/COLLECT_FERTILIZER/CARE. "
        "Remember the ATOMIC PLANT check (sum PLANT<crop> > seeds -> all PASS).")


def process_market(st: State, orders):
    raise NotImplementedError(
        "TODO(04-'_process_market'): slot-by-slot; HIRE/BUY_LAND once each in "
        "player order; then per-unit lockstep while-loop with both quotes on the "
        "same pre-commit inventory; _refresh_prices after each slot. "
        "SELL: inventory[item]+=1 only if price>1.")


def end_of_day(st: State):
    raise NotImplementedError(
        "TODO(04-'_end_of_day'): _daily_refresh_plants (consec_unwatered, ongoing "
        "tick at ages fy,fy+iv,...; max_lifespan on last tick), "
        "_daily_refresh_animals (escape at 2 unfed; production; care bank), "
        "_spawn_weeds (rng = seed*1_000_003 ^ day, p=0.005), "
        "_drop_inventories_to_shed (cap 100), reset farmer/hands, "
        "shop unlock at next_day%3==0 (sorted(SHOPS), uniform w/ replacement, cap 8).")


def step(st: State, actions, orders):
    """spec §interpreter per-step sequence."""
    apply_unit_actions(st, actions)
    process_market(st, orders)
    town_consume(st, [st.shops[b] for b in range(st.B)])
    decay_plants(st)
    if (st.step + 1) % 24 == 0:
        end_of_day(st)
    st.step += 1
    # reward locks at step 718 (spec): caller checks st.step >= episodeSteps-2.
    return st
