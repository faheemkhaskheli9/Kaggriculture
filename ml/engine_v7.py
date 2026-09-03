"""Parameterised fork of ``main.py`` v7 (the promoted zoned multi-unit agent).

PLAN_ML_IMPROVE.md Lever A1. Unlike ``ml/engine.py`` (which forks the weaker
``bots/_kagri_botlib.py`` and loses 0-4 to ``main.py``), this is a *faithful*
fork of the agent we actually ship: the engine math -- zones, task priorities,
greedy ``assign``, ``animal_crew_actions``, the price curve -- is copied
line-for-line from ``main.py``. The only change is that the magic numbers in the
six decision functions (``choose_crops``, ``animal_targets``, ``build_tasks``,
``add_plant_tasks``, ``assign``, ``market_orders``) are read from a ``cfg`` dict.

**Every knob defaults to v7's current hard-coded value**, so
``build_agent_v7(DEFAULT_CONFIG_V7)`` reproduces ``main.py`` exactly. That
equivalence is the gate before any optimisation run -- see
``python -m ml.evaluate --engine v7 --default --league gate``.

If you change a *mechanic* in ``main.py``, mirror it here. If you only want a
number searchable, add it to ``DEFAULT_CONFIG_V7`` + ``ml/spec_v7.py``.
"""
from __future__ import annotations

import math
from collections import Counter

# ------------------------------------------------------------------ constants --
# Copied verbatim from main.py. These are env economics, not tunables.
CROPS = {
    "WHEAT":      (10, 2, 4, False, 26),
    "CARROT":     (20, 2, 3, False, 26),
    "TOMATO":     (50, 8, 8, True, 20),
    "STRAWBERRY": (100, 10, 10, True, 13),
    "MELON":      (80, 10, 12, False, 18),
}
ONE_TIME = {"WHEAT", "CARROT", "MELON"}

BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
        "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}

MKT = {
    "WHEAT":      (25, 10000, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT":     (35, 10000, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO":     (60, 10000, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON":      (250, 10000, 300, "log", 0.20, "sq", 3.60),
    "EGG":        (50, 10000, 332, "hinge", 0.40, "log", 0.20),
    "MILK":       (160, 10000, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL":       (200, 10000, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 10000, 200, "linear", 0.40, "linear", 0.40),
}

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
SHED_CENTER = (4.5, 4.5)
PREMIUM = {"STRAWBERRY", "MELON", "MILK", "WOOL"}

USE_ANIMALS = True
ANIMALS = {
    "COW":   (400, "PASTURE", "BUILD_PASTURE", 8, 2, "MILK"),
    "SHEEP": (500, "PASTURE", "BUILD_PASTURE", 6, 3, "WOOL"),
    "GOOSE": (300, "COOP",    "BUILD_COOP",    4, 1, "EGG"),
}

# ------------------------------------------------------------------- knobs -----
DEFAULT_CONFIG_V7 = {
    # --- working-capital reserve curve (market_orders) ---
    "reserve_late_day": 25, "reserve_late": 60,
    "reserve_ramp_cutday": 16, "reserve_ramp_base": 200, "reserve_ramp_slope": 150,
    "reserve_ramp_cap": 1400, "reserve_mid": 200,
    "seed_cap_early": 400, "seed_cap_late": 800, "seed_cap_splitday": 10,
    # --- hiring ---
    "hire_early_day": 3, "hire_early": 6,
    "hire_q1": 7, "hire_q2": 10, "hire_full": 13,
    "hire_winddown_day": 27, "hire_winddown": 8, "hire_stop_day": 29,
    # --- land gates ---
    "land_fill_23": 0.55, "land_fill_4": 0.62,
    "land_day_23_max": 18, "land_day_4_min": 8, "land_day_4_max": 20,
    "land_cash_23_base": 400, "land_cash_23_slope": 200, "land_cash_4_extra": 2500,
    # --- animals ---
    "animal_buf_base": 300, "animal_buf_per_head": 150,
    "animal_freeze_day": 17, "opp_animal_thresh": 4, "opp_animal_by_day": 7,
    "a_COW": 9, "a_GOOSE": 2, "a_SHEEP_wool": 2, "a_SHEEP_nowool": 1,
    "ac_COW": 3, "ac_GOOSE": 3, "ac_SHEEP": 0,
    "animal_cap_q1": 3, "animal_cap_q2": 8, "animal_cap_full": 13, "animal_cap_contested": 6,
    "wheat_feed_per_head": 2, "wheat_feed_base": 4,
    # --- selling cadence ---
    "sell_keep_premium": 0.80, "sell_keep_staple": 0.72,
    "sell_cap_premium": 6, "sell_cap_staple": 16, "sell_cap_contested": 8,
    "sell_glut_thresh": 1.4, "sell_glut_mult_max": 4.0,
    "contested_floor_frac": 0.5, "sell_min_frac": 0.55, "full_dump_day": 28,
    # --- crop schedule (choose_crops) ---
    "early_day": 7,
    "w_e_WHEAT": 0.50, "w_e_CARROT": 0.28, "w_e_TOMATO": 0.16,
    "w_e_STRAWBERRY": 0.12, "w_e_MELON": 0.0,
    "w_m_WHEAT": 0.24, "w_m_CARROT_dem": 0.05,
    "w_m_TOMATO": 0.44, "w_m_TOMATO_dem": 0.06,
    "w_m_STRAWBERRY": 0.30, "w_m_STRAWBERRY_dem": 0.05, "w_m_MELON": 0.10,
    "late_carrot_bonus": 0.22, "late_carrot_day": 22,
    "tomato_late_day": 21, "tomato_late_mult": 0.7,
    "strawberry_min_day": 4, "melon_val_min": 0.85,
    "cap_MELON": 5, "cap_CARROT_early": 18, "cap_CARROT": 10,
    # --- task priorities ---
    "pr_water_dying": 10000, "pr_water_dying_hourmul": 5,
    "pr_water_window": 6200, "pr_water_comfort": 2600,
    "pr_harv_1t_done": 5200, "pr_harv_1t_base": 3500,
    "pr_harv_ong_urgent": 5000, "pr_harv_ong": 3200,
    "pr_harv_animal": 4800, "pr_collect_fert": 2700,
    "pr_weed": 2200, "pr_plant": 2400,
    "plant_room_per_unit": 22, "plant_stop_day": 27,
    # --- assign ---
    "assign_on_tile": 2000, "assign_in_zone": 150, "assign_dist": 25,
    # --- endgame ---
    "eg_liquidate_day": 29, "eg_march_hour": 15,
    "eg_drop_hour": 7, "eg_drop_prev_hour": 19,
    # --- crew ---
    "crew_max": 4, "crew_min_crops": 6, "crew_per_animals": 5,
}


# ------------------------------------------------ byte-identical helpers -------
def _shape(func, x, T):
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price_at(item, inv):
    p = MKT.get(item)
    if not p:
        return BASE.get(item, 1)
    base, I0, T, bf, bt, af, at = p
    if inv < I0:
        amp = bt * base / _shape(bf, T, T)
        val = base + amp * _shape(bf, I0 - inv, T)
    else:
        amp = at * base / _shape(af, T, T)
        val = base - amp * _shape(af, inv - I0, T)
    return max(1, int(round(val)))


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(a, b):
    x, y = a
    X, Y = b
    if x < X:
        return ["EAST"]
    if x > X:
        return ["WEST"]
    if y < Y:
        return ["SOUTH"]
    if y > Y:
        return ["NORTH"]
    return ["PASS"]


def inv_total(inv):
    return sum(max(0, int(v)) for v in (inv or {}).values())


def unlocked_cells(me):
    tiles = me.get("tiles", [])
    cells = []
    for y, row in enumerate(tiles):
        xs = range(len(row)) if y % 2 == 0 else range(len(row) - 1, -1, -1)
        for x in xs:
            if row[x] != "LOCKED":
                cells.append((x, y))
    return cells


def make_zones(cells, n_units):
    n_units = max(1, n_units)
    if not cells:
        return [set() for _ in range(n_units)]
    per = len(cells) / n_units
    zones = []
    for i in range(n_units):
        lo = int(round(i * per))
        hi = int(round((i + 1) * per))
        zones.append(set(cells[lo:hi]))
    for i in range(n_units):
        if not zones[i] and cells:
            zones[i].add(cells[min(i, len(cells) - 1)])
    return zones


def field_counts(farm):
    c = Counter()
    for row in farm.get("tiles", []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                c[t.get("crop")] += 1
    return c


def demand_counts(obs):
    d = Counter()
    for shop in (obs.get("town") or {}).get("unlocked_shops", []):
        for item in SHOPS.get(str(shop).strip().upper().replace(" ", "_").replace("-", "_"), []):
            d[item] += 1
    return d


def _placed_animal_counts(me):
    c = Counter()
    for row in me["tiles"]:
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                c[t["animal"]] += 1
    return c


def animal_tiles(me, targets):
    tiles = me["tiles"]
    existing = [
        (x, y)
        for y, row in enumerate(tiles) for x, t in enumerate(row)
        if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE")
    ]
    k = sum(targets.values())
    if k <= len(existing):
        return existing
    taken = set(existing)
    free = sorted(
        ((x, y) for y, row in enumerate(tiles) for x, t in enumerate(row)
         if t is None and (x, y) not in SHED_TILES and (x, y) not in taken),
        key=lambda c: (abs(c[0] - 4.5) + abs(c[1] - 4.5), c),
    )
    return existing + free[: k - len(existing)]


def animal_crew_actions(obs, me, private, reserved, crew_idx, positions, invs):
    if not reserved or not crew_idx:
        return {}
    tiles = me["tiles"]
    shed = private.get("shed", {}) or {}

    placed, empty_struct, build_spots = [], [], []
    for (x, y) in reserved:
        t = tiles[y][x]
        if isinstance(t, dict) and t.get("animal"):
            placed.append(((x, y), t))
        elif isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE"):
            empty_struct.append(((x, y), t.get("kind")))
        elif t is None:
            build_spots.append((x, y))

    feedable = {p for p, t in placed if not t.get("fed_today", False)}
    care_spots = {p for p, t in placed
                  if t.get("fed_today", False) and not t.get("cared_today", False)}
    yield_or_fert = {p for p, t in placed
                     if t.get("yield_units", 0) > 0 or t.get("fertilizer_available", False)}
    in_shed_animals = [a for a in ANIMALS if int(shed.get(a, 0)) > 0]
    shed_wheat = int(shed.get("WHEAT", 0))
    by_pos = {p: t for p, t in placed}

    out, claimed = {}, set()
    for idx in crew_idx:
        if idx >= len(positions):
            continue
        pos = tuple(positions[idx])
        inv = invs[idx] if idx < len(invs) else {}
        wheat = int(inv.get("WHEAT", 0))
        shed_adj = pos in SHED_TILES
        to_shed = lambda p=pos: step_toward(p, min(SHED_TILES, key=lambda q: dist(p, q)))

        here = by_pos.get(pos)
        if here is not None and pos not in claimed:
            if pos in feedable and wheat > 0:
                out[idx] = ["FEED"]; claimed.add(pos); continue
            if here.get("yield_units", 0) > 0:
                out[idx] = ["HARVEST"]; claimed.add(pos); continue
            if here.get("fertilizer_available", False):
                out[idx] = ["COLLECT_FERTILIZER"]; claimed.add(pos); continue
            if pos in care_spots:
                out[idx] = ["CARE"]; claimed.add(pos); continue

        pending_feed = [p for p in feedable if p not in claimed]
        if pending_feed and wheat == 0 and shed_wheat > 0:
            if shed_adj:
                take = min(8, shed_wheat)
                shed_wheat -= take
                out[idx] = ["PICKUP", "WHEAT", take]
            else:
                out[idx] = to_shed()
            continue

        goals = [p for p in pending_feed if wheat > 0]
        goals += [p for p in yield_or_fert if p not in claimed]
        goals += [p for p in care_spots if p not in claimed]
        if goals:
            tgt = min(goals, key=lambda p: dist(pos, p))
            claimed.add(tgt)
            out[idx] = step_toward(pos, tgt) if tgt != pos else ["PASS"]
            continue

        if in_shed_animals and empty_struct:
            a = in_shed_animals[0]
            spot = next((p for p, k in empty_struct
                         if k == ANIMALS[a][1] and p not in claimed), None)
            if spot:
                if int(inv.get(a, 0)) > 0:
                    if pos == spot:
                        out[idx] = ["PLACE", a]; claimed.add(spot)
                    else:
                        out[idx] = step_toward(pos, spot)
                elif shed_adj:
                    out[idx] = ["PICKUP", a, 1]
                else:
                    out[idx] = to_shed()
                continue

        if in_shed_animals and build_spots:
            spot = min((s for s in build_spots if s not in claimed),
                       key=lambda p: dist(pos, p), default=None)
            if spot is not None:
                claimed.add(spot)
                out[idx] = [ANIMALS[in_shed_animals[0]][2]] if pos == spot \
                    else step_toward(pos, spot)
                continue

        if placed:
            tgt = min((p for p, _ in placed), key=lambda p: dist(pos, p))
            if tgt != pos:
                out[idx] = step_toward(pos, tgt)
    return out


# ------------------------------------------------ parameterised decisions -----
def animal_targets(obs, me, cfg):
    if not USE_ANIMALS:
        return {}
    day = obs.get("day", 0)
    have = _placed_animal_counts(me)
    if day > cfg["animal_freeze_day"]:
        return dict(have)
    nq = len(me.get("unlocked_quadrants", []))
    cap = {1: cfg["animal_cap_q1"], 2: cfg["animal_cap_q2"]}.get(nq, cfg["animal_cap_full"])
    dem = demand_counts(obs)
    opp_farm = obs["farms"][1 - obs["player"]]
    opp_animals = sum(1 for row in opp_farm.get("tiles", []) for t in row
                      if isinstance(t, dict) and t.get("animal"))
    if day >= cfg["opp_animal_by_day"] and opp_animals >= cfg["opp_animal_thresh"]:
        want = {"COW": cfg["ac_COW"], "GOOSE": cfg["ac_GOOSE"], "SHEEP": cfg["ac_SHEEP"]}
        cap = min(cap, cfg["animal_cap_contested"])
    else:
        want = {"COW": cfg["a_COW"], "GOOSE": cfg["a_GOOSE"],
                "SHEEP": cfg["a_SHEEP_wool"] if dem["WOOL"] else cfg["a_SHEEP_nowool"]}
    out, tot = {}, 0
    for a in ("COW", "GOOSE", "SHEEP"):
        take = max(have[a], min(want[a], cap - tot))
        if take:
            out[a] = take
            tot += take
    return out


def choose_crops(obs, me, private, counts, plant_slots, cfg):
    day = obs.get("day", 0)
    prices = (obs.get("market") or {}).get("prices", {})
    demand = demand_counts(obs)
    opp = field_counts(obs["farms"][1 - obs["player"]])
    total = max(1, sum(counts.values()) + plant_slots)

    early = day < cfg["early_day"]
    targets = {}
    for crop, (cost, fy, my, ongoing, plant_by) in CROPS.items():
        if day > plant_by:
            continue
        pr = prices.get(crop, BASE[crop])
        val = pr / BASE[crop]
        if crop == "WHEAT":
            share = cfg["w_e_WHEAT"] if early else cfg["w_m_WHEAT"]
        elif crop == "CARROT":
            share = cfg["w_e_CARROT"] if early else cfg["w_m_CARROT_dem"] * demand[crop]
            if day > cfg["late_carrot_day"]:
                share += cfg["late_carrot_bonus"]
        elif crop == "TOMATO":
            share = cfg["w_e_TOMATO"] if early else cfg["w_m_TOMATO"] + cfg["w_m_TOMATO_dem"] * demand[crop]
            if day > cfg["tomato_late_day"]:
                share *= cfg["tomato_late_mult"]
        elif crop == "STRAWBERRY":
            share = 0.0 if day < cfg["strawberry_min_day"] else (
                cfg["w_e_STRAWBERRY"] if early
                else cfg["w_m_STRAWBERRY"] + cfg["w_m_STRAWBERRY_dem"] * demand[crop])
        else:  # MELON
            share = cfg["w_e_MELON"] if early else (
                cfg["w_m_MELON"] if val >= cfg["melon_val_min"] else 0.0)
        share *= max(0.30, min(2.0, val))
        share *= max(0.35, 1.0 - 0.18 * opp[crop])
        if share > 0:
            targets[crop] = share

    if not targets:
        return []
    ssum = sum(targets.values())
    want = {c: s / ssum * total for c, s in targets.items()}
    caps = {"MELON": cfg["cap_MELON"],
            "CARROT": cfg["cap_CARROT_early"] if early else cfg["cap_CARROT"]}
    if day > 22:
        caps.pop("CARROT")
    picks = []
    cur = Counter(counts)
    for _ in range(plant_slots):
        best, bestgap = None, -1e9
        for c, w in want.items():
            if c in caps and cur[c] >= caps[c]:
                continue
            gap = w - cur[c]
            if gap > bestgap:
                best, bestgap = c, gap
        if best is None:
            break
        picks.append(best)
        cur[best] += 1
    return picks


def build_tasks(obs, me, private, cfg):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    tiles = me["tiles"]
    tasks = []
    counts = Counter()
    liquidate = day >= cfg["eg_liquidate_day"]
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            pos = (x, y)
            kind = t.get("kind")
            if kind == "PLANT":
                crop = t.get("crop")
                counts[crop] += 1
                if liquidate:
                    if t.get("yield_units", 0) > 0:
                        tasks.append((5000, pos, ["HARVEST"]))
                    continue
                fy, my, ongoing = CROPS[crop][1], CROPS[crop][2], CROPS[crop][3]
                age = day - t.get("planted_day", day)
                yu = t.get("yield_units", 0)
                cu = t.get("consecutive_unwatered", 0)
                watered = t.get("watered_today", False)
                if not watered:
                    if cu >= 1:
                        tasks.append((cfg["pr_water_dying"] + cfg["pr_water_dying_hourmul"] * hour,
                                      pos, ["WATER"]))
                    elif not ongoing and (my + 1) // 2 <= age <= my:
                        tasks.append((cfg["pr_water_window"] + age, pos, ["WATER"]))
                    else:
                        tasks.append((cfg["pr_water_comfort"], pos, ["WATER"]))
                if yu > 0 and age >= fy:
                    if not ongoing:
                        pr = cfg["pr_harv_1t_done"] if age > my else cfg["pr_harv_1t_base"] + age
                        tasks.append((pr, pos, ["HARVEST"]))
                    else:
                        mls = t.get("max_lifespan_step", -1)
                        decaying = mls >= 0 and (day + 1) * 24 >= mls
                        near_cap = yu >= 4
                        tasks.append((cfg["pr_harv_ong_urgent"] if (decaying or near_cap)
                                      else cfg["pr_harv_ong"], pos, ["HARVEST"]))
            elif kind in {"COOP", "PASTURE"} and t.get("animal"):
                if t.get("yield_units", 0) > 0:
                    tasks.append((5000 if liquidate else cfg["pr_harv_animal"], pos, ["HARVEST"]))
                if not liquidate and t.get("fertilizer_available", False):
                    tasks.append((cfg["pr_collect_fert"], pos, ["COLLECT_FERTILIZER"]))
            elif kind == "WEED":
                tasks.append((cfg["pr_weed"] if not liquidate else 0, pos, ["DIG"]))
    return tasks, counts


def add_plant_tasks(obs, me, private, counts, tasks, n_units, cfg, reserved=()):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if day >= cfg["plant_stop_day"] or hour >= 22:
        return
    reserved = set(reserved)
    tiles = me["tiles"]
    planted = sum(counts.values())
    capacity = len(unlocked_cells(me))
    unwatered = sum(
        1 for row in tiles for t in row
        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today")
    )
    room = min(capacity - planted, max(0, n_units * cfg["plant_room_per_unit"] - unwatered))
    if room <= 0:
        return
    empty = sorted(
        ((dist((x, y), (4, 4)), x, y)
         for y, row in enumerate(tiles) for x, t in enumerate(row)
         if t is None and (x, y) not in reserved),
        key=lambda e: e[0],
    )
    if not empty:
        return
    seeds = private.get("seeds", {})
    picks = choose_crops(obs, me, private, counts, min(room, len(empty), n_units * 2), cfg)
    seed_budget = Counter({c: int(seeds.get(c, 0)) for c in CROPS})
    pi = 0
    for _, x, y in empty:
        if pi >= len(picks):
            break
        crop = picks[pi]
        pi += 1
        if seed_budget[crop] <= 0:
            continue
        seed_budget[crop] -= 1
        tasks.append((cfg["pr_plant"], (x, y), ["PLANT", crop]))


def assign(obs, me, private, tasks, zones, cfg, forced=None):
    pos = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
    n = len(pos)
    invs = list(private.get("inventories", []))
    while len(invs) < n:
        invs.append({})
    actions = [["PASS"] for _ in range(n)]
    busy = [False] * n
    claimed = set()
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)

    for idx, act in (forced or {}).items():
        if 0 <= idx < n and act:
            actions[idx] = act
            busy[idx] = True

    if day >= 29 and hour >= cfg["eg_march_hour"]:
        for i, p in enumerate(pos):
            if inv_total(invs[i]) > 0:
                if p in SHED_TILES:
                    actions[i] = ["DROP"]
                else:
                    actions[i] = step_toward(p, min(SHED_TILES, key=lambda q: dist(p, q)))
                busy[i] = True

    ordered = sorted(tasks, key=lambda t: -t[0])

    def do(i, tgt, act):
        actions[i] = act if pos[i] == tgt else step_toward(pos[i], tgt)
        claimed.add(tgt)
        busy[i] = True

    for pr, tgt, act in ordered:
        if pr < 9000 or tgt in claimed:
            continue
        cand = [(dist(pos[i], tgt), i) for i in range(n) if not busy[i]]
        if cand:
            do(min(cand)[1], tgt, act)

    def try_assign(i, allow_global):
        best = None
        for pr, tgt, act in ordered:
            if tgt in claimed:
                continue
            in_zone = tgt in zones[i]
            if not allow_global and not in_zone:
                continue
            if act == ["DIG"] and not in_zone:
                continue
            d = dist(pos[i], tgt)
            eff = (pr + (cfg["assign_on_tile"] if d == 0 else 0)
                   + (cfg["assign_in_zone"] if in_zone else 0) - cfg["assign_dist"] * d)
            if best is None or eff > best[0]:
                best = (eff, tgt, act)
        if best is None:
            return False
        do(i, best[1], best[2])
        return True

    for i in range(n):
        if not busy[i]:
            try_assign(i, allow_global=False)
    for i in range(n):
        if not busy[i]:
            try_assign(i, allow_global=True)

    endgame_drop = (day >= 29 and hour >= cfg["eg_drop_hour"]) or \
                   (day >= 28 and hour >= cfg["eg_drop_prev_hour"])
    if endgame_drop:
        for i in range(n):
            if busy[i]:
                continue
            sp = min(SHED_TILES, key=lambda q: dist(pos[i], q))
            if inv_total(invs[i]) > 0:
                actions[i] = ["DROP"] if pos[i] in SHED_TILES else step_toward(pos[i], sp)
                busy[i] = True
            elif day >= 29:
                if pos[i] != sp:
                    actions[i] = step_toward(pos[i], sp)
                busy[i] = True

    if not (day >= 29 and hour >= cfg["eg_march_hour"]):
        pend = [t[1] for t in ordered] + [c for z in zones for c in z]
        for i in range(n):
            if busy[i] or not pend:
                continue
            tgt = min(pend, key=lambda c: dist(pos[i], c))
            if tgt != pos[i]:
                actions[i] = step_toward(pos[i], tgt)
    return actions


def market_orders(obs, me, private, counts, n_units, cfg):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    money = float(me.get("money", 0))
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    mkt_inv = ((obs.get("market") or {}).get("inventory", {})) or {}
    if day >= cfg["reserve_late_day"]:
        reserve = cfg["reserve_late"]
    elif day < cfg["reserve_ramp_cutday"]:
        reserve = min(cfg["reserve_ramp_cap"],
                      cfg["reserve_ramp_base"] + cfg["reserve_ramp_slope"] * day)
    else:
        reserve = cfg["reserve_mid"]
    seed_spend_cap = cfg["seed_cap_early"] if day < cfg["seed_cap_splitday"] else cfg["seed_cap_late"]

    hires, sells, buys_hi, buys_lo = [], [], [], []

    if hour <= 1:
        nq = len(me.get("unlocked_quadrants", []))
        if day < cfg["hire_early_day"]:
            desired = cfg["hire_early"]
        elif day < cfg["hire_winddown_day"]:
            desired = {1: cfg["hire_q1"], 2: cfg["hire_q2"]}.get(nq, cfg["hire_full"])
        elif day < cfg["hire_stop_day"]:
            desired = cfg["hire_winddown"]
        else:
            desired = 0
        for _ in range(max(0, desired - int(me.get("hires_today", 0)))):
            hires.append(["HIRE"])

    n_placed = sum(1 for row in me["tiles"] for t in row
                   if isinstance(t, dict) and t.get("animal"))
    wheat_floor = (cfg["wheat_feed_per_head"] * n_placed + cfg["wheat_feed_base"]) \
        if (USE_ANIMALS and n_placed and day < 28) else 0
    for item, qty in list(shed.items()):
        qty = int(qty)
        if item == "WHEAT":
            qty -= wheat_floor
        if qty <= 0 or item not in BASE:
            continue
        inv0 = mkt_inv.get(item, 10000)
        base = BASE[item]
        p0 = price_at(item, inv0)
        contested = item in ("MILK", "WOOL", "FERTILIZER")
        if day >= cfg["full_dump_day"]:
            amount = qty
        elif contested and p0 < cfg["contested_floor_frac"] * base:
            amount = 0
        else:
            prem = item in PREMIUM
            keep = (cfg["sell_keep_premium"] if prem else cfg["sell_keep_staple"]) * base
            cap = cfg["sell_cap_premium"] if prem else cfg["sell_cap_staple"]
            if contested:
                cap = cfg["sell_cap_contested"]
            if p0 >= cfg["sell_glut_thresh"] * base:
                cap = int(cap * min(cfg["sell_glut_mult_max"], p0 / base))
            amount = 0
            while amount < min(qty, cap) and price_at(item, inv0 + 2 * amount) >= keep:
                amount += 1
            if amount == 0 and p0 >= cfg["sell_min_frac"] * base and not contested:
                amount = 1
        if amount > 0:
            sells.append((p0 * amount, ["SELL", item, amount]))
    sells.sort(key=lambda s: -s[0])
    sells = [s[1] for s in sells]

    unlocked = list(me.get("unlocked_quadrants", []))
    open_tiles = len(unlocked_cells(me))
    if hour <= 3 and len(unlocked) < 4:
        nth = len(unlocked) - 1
        cost = (1000, 2000, 4000)[nth]
        fill = sum(counts.values()) / max(1, open_tiles)
        if nth < 2:
            ok = (day <= cfg["land_day_23_max"] and fill >= cfg["land_fill_23"]
                  and money >= cost + cfg["land_cash_23_base"] + cfg["land_cash_23_slope"] * nth)
        else:
            ok = (cfg["land_day_4_min"] <= day <= cfg["land_day_4_max"]
                  and fill >= cfg["land_fill_4"] and money >= cost + cfg["land_cash_4_extra"])
        if ok:
            buys_hi.append(["BUY_LAND"])

    if USE_ANIMALS:
        have = Counter()
        for row in me["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("animal"):
                    have[t["animal"]] += 1
        placed_total = sum(have.values())
        pending = int(sum(v for k, v in shed.items() if k in ANIMALS))
        if hour <= 6:
            for a, want in animal_targets(obs, me, cfg).items():
                cur = have[a] + int(shed.get(a, 0))
                if cur < want and money >= ANIMALS[a][0] + cfg["animal_buf_base"] \
                        + cfg["animal_buf_per_head"] * placed_total:
                    buys_hi.append(["BUY_ANIMAL", a, 1])
                    money -= ANIMALS[a][0]
                    break
        if (placed_total or pending) and hour <= 4:
            need_w = 2 * (placed_total + pending) + 4
            have_w = int(shed.get("WHEAT", 0))
            if have_w < need_w:
                wp = max(1, price_at("WHEAT", mkt_inv.get("WHEAT", 10000)))
                b = min(need_w - have_w, 10, int(max(0, money - reserve) // wp))
                if b > 0:
                    buys_hi.append(["BUY_PRODUCT", "WHEAT", b])
                    money -= b * wp

    if day < 27:
        need = Counter(choose_crops(obs, me, private, counts, n_units * 2, cfg))
        buf = 3 if n_units <= 4 else 4
        spent = 0
        for crop in sorted(need, key=lambda c: -need[c]):
            have = int(seeds.get(crop, 0))
            target = min(need[crop] + buf, 12)
            cost = CROPS[crop][0]
            budget = min(max(0, money - reserve), max(0, seed_spend_cap - spent))
            b = min(max(0, target - have), int(budget // max(1, cost)))
            if b > 0:
                buys_lo.append(["BUY_SEED", crop, b])
                money -= b * cost
                spent += b * cost

    if day >= 29:
        out = sells + hires + buys_hi + buys_lo
    else:
        out = hires + sells[:3] + buys_hi + buys_lo + sells[3:]
    return out[:10]


# --------------------------------------------------------------- factory ------
def build_agent_v7(config: dict | None = None):
    cfg = dict(DEFAULT_CONFIG_V7)
    if config:
        cfg.update(config)

    def agent(obs):
        try:
            player = int(obs.get("player", 0))
            farms = obs.get("farms", [])
            if len(farms) < 2:
                return {"farmer": ["PASS"], "hands": [], "market": []}
            me = farms[player]
            private = obs.get("private") or {}
            n_units = 1 + len(me.get("hands", []))

            cells = unlocked_cells(me)

            reserved = animal_tiles(me, animal_targets(obs, me, cfg)) if USE_ANIMALS else []
            forced = {}
            n_crew = 0
            if reserved and obs.get("day", 0) < 29:
                n_animals = sum(1 for row in me["tiles"] for t in row
                                if isinstance(t, dict) and t.get("animal"))
                n_crew = min(cfg["crew_max"], max(0, n_units - cfg["crew_min_crops"]),
                             1 + max(n_animals, len(reserved)) // cfg["crew_per_animals"])
                if n_crew > 0:
                    crew_idx = list(range(n_units - n_crew, n_units))
                    positions = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
                    invs = private.get("inventories", []) or []
                    forced = animal_crew_actions(obs, me, private, reserved,
                                                 crew_idx, positions, invs)

            zones = make_zones(cells, max(1, n_units - n_crew))
            zones += [set() for _ in range(n_units - len(zones))]

            tasks, counts = build_tasks(obs, me, private, cfg)
            add_plant_tasks(obs, me, private, counts, tasks, n_units, cfg, reserved)
            actions = assign(obs, me, private, tasks, zones, cfg, forced=forced)

            market = market_orders(obs, me, private, counts, n_units, cfg)
            return {"farmer": actions[0], "hands": actions[1:], "market": market}
        except Exception:
            try:
                n = len(obs["farms"][obs["player"]].get("hands", []))
            except Exception:
                n = 0
            return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(n)], "market": []}

    return agent
