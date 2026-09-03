"""Parameterised strong engine for Kaggriculture contender agents.

A fork of `main.py` v5 (zoned multi-unit core + animal crew + throughput bundle +
sharp endgame) exposed as ``make_agent(config)``. A config with **no overrides**
reproduces `main.py` v5 behaviour exactly -- see `contenders/c_v5clone.py`, which
is the neutrality check. Each real contender is ``make_agent({...})`` with a few
policy knobs changed; the core mechanics (zones, task priorities, assignment,
price curve, endgame) are shared and unchanged.

See `PLAN_CONTENDERS.md` for the roster this feeds (C1 wheat-flood, C2 animal
factory, C3 premium, C4 monopolist, ...).

Config knobs (all optional; omitted key => the v5 default in parentheses):

  name                 str, for debugging                              ("engine")
  use_animals          bool -- run the animal crew at all              (True)
  hire_fn(day, nq)     -> desired hand count                           (v5 ramp)
  land_ok_fn(nth, day, fill, money, cost) -> bool                      (v5 gates)
                       nth 0/1 => quadrant 2/3, nth 2 => the $4k quadrant 4
  animal_target_fn(obs, me) -> {animal: count}          (v5 opp-conditional herd)
  crop_cfg             {CROP: {...}} -- crops absent are NEVER planted  (v5 mix)
                       per-crop keys: early, main, main_demand,
                       late=(day, +share), late_mul=(day, xshare),
                       val_gate (min price/base to plant at all), min_day
  crop_caps_fn(day, early) -> {CROP: max_tiles}                        (v5 caps)
  plant_water_slack    int -- per-unit unwatered-plant budget          (22)
  reserve_early/late   cash kept unspent before day 25 / from day 25   (200 / 60)
  sell_keep_prem       keep selling premium while marginal >= x*base   (0.80)
  sell_keep_staple     same, staples                                   (0.72)
  sell_cap_prem/staple/contested   per-turn per-line unit cap      (6 / 16 / 8)
  sell_cap_override    {ITEM: cap}   -- overrides the class cap         ({})
  sell_keep_override   {ITEM: frac}  -- overrides the class keep-frac   ({})
  contested_skip_frac  skip a contested line when p0 < x*base          (0.5)
  seed_cap             max seeds held per crop after a buy             (12)
  seed_lookahead       seed-buy target ~= n_units * this               (2)
"""
import math
from collections import Counter

# seed cost, first_yield_day, max_yield_day, ongoing, plant-by day
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

# base, I0, T, below_func, below_target, above_func, above_target
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

# cost, structure, build_op, first_yield_day, interval, product
ANIMALS = {
    "COW":   (400, "PASTURE", "BUILD_PASTURE", 8, 2, "MILK"),
    "SHEEP": (500, "PASTURE", "BUILD_PASTURE", 6, 3, "WOOL"),
    "GOOSE": (300, "COOP",    "BUILD_COOP",    4, 1, "EGG"),
}


# --------------------------------------------------------------------------- #
#  Pure helpers (identical to main.py v5)                                     #
# --------------------------------------------------------------------------- #
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
        key = str(shop).strip().upper().replace(" ", "_").replace("-", "_")
        for item in SHOPS.get(key, []):
            d[item] += 1
    return d


def _placed_animal_counts(me):
    c = Counter()
    for row in me["tiles"]:
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                c[t["animal"]] += 1
    return c


# --------------------------------------------------------------------------- #
#  Default policy functions (v5 behaviour)                                    #
# --------------------------------------------------------------------------- #
def _default_hire_fn(day, nq):
    if day < 3:
        return 6
    if day < 27:
        return {1: 7, 2: 10}.get(nq, 13)
    if day < 29:
        return 8
    return 0


def _default_land_ok_fn(nth, day, fill, money, cost):
    if nth < 2:
        return day <= 18 and fill >= 0.55 and money >= cost + 400 + 200 * nth
    return 8 <= day <= 20 and fill >= 0.62 and money >= cost + 2500


def _default_animal_targets(obs, me, use_animals):
    """How many of each animal we want (v5 opponent-conditional herd)."""
    if not use_animals:
        return {}
    day = obs.get("day", 0)
    have = _placed_animal_counts(me)
    if day > 17:
        return dict(have)                       # freeze; no new reservations
    nq = len(me.get("unlocked_quadrants", []))
    cap = {1: 3, 2: 8}.get(nq, 13)
    dem = demand_counts(obs)
    opp_farm = obs["farms"][1 - obs["player"]]
    opp_animals = sum(1 for row in opp_farm.get("tiles", []) for t in row
                      if isinstance(t, dict) and t.get("animal"))
    if day >= 7 and opp_animals >= 4:
        want = {"COW": 3, "GOOSE": 3, "SHEEP": 0}
        cap = min(cap, 6)
    else:
        want = {"COW": 9, "GOOSE": 2, "SHEEP": 2 if dem["WOOL"] else 1}
    out, tot = {}, 0
    for a in ("COW", "GOOSE", "SHEEP"):
        take = max(have[a], min(want[a], cap - tot))
        if take:
            out[a] = take
            tot += take
    return out


_DEFAULT_CROP_CFG = {
    "WHEAT":      {"early": 0.50, "main": 0.24},
    "CARROT":     {"early": 0.28, "main_demand": 0.05, "late": (22, 0.22)},
    "TOMATO":     {"early": 0.16, "main": 0.44, "main_demand": 0.06, "late_mul": (21, 0.7)},
    "STRAWBERRY": {"early": 0.12, "main": 0.30, "main_demand": 0.05, "min_day": 4},
    "MELON":      {"main": 0.10, "val_gate": 0.85},
}


def _default_caps_fn(day, early):
    caps = {"MELON": 5, "CARROT": 18 if early else 10}
    if day > 22:
        caps.pop("CARROT", None)
    return caps


# --------------------------------------------------------------------------- #
#  Animal tiles + crew (config-independent, identical to v5)                  #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
#  Task generation + assignment (config-independent, identical to v5)        #
# --------------------------------------------------------------------------- #
def build_tasks(obs, me, private):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    tiles = me["tiles"]
    tasks = []
    counts = Counter()
    liquidate = day >= 29
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
                        tasks.append((10000 + 5 * hour, pos, ["WATER"]))
                    elif not ongoing and (my + 1) // 2 <= age <= my:
                        tasks.append((6200 + age, pos, ["WATER"]))
                    else:
                        tasks.append((2600, pos, ["WATER"]))
                if yu > 0 and age >= fy:
                    if not ongoing:
                        pr = 5200 if age > my else 3500 + age
                        tasks.append((pr, pos, ["HARVEST"]))
                    else:
                        mls = t.get("max_lifespan_step", -1)
                        decaying = mls >= 0 and (day + 1) * 24 >= mls
                        near_cap = yu >= 4
                        tasks.append((5000 if (decaying or near_cap) else 3200, pos, ["HARVEST"]))
            elif kind in {"COOP", "PASTURE"} and t.get("animal"):
                if t.get("yield_units", 0) > 0:
                    tasks.append((5000 if liquidate else 4800, pos, ["HARVEST"]))
                if not liquidate and t.get("fertilizer_available", False):
                    tasks.append((2700, pos, ["COLLECT_FERTILIZER"]))
            elif kind == "WEED":
                tasks.append((1500 if not liquidate else 0, pos, ["DIG"]))
    return tasks, counts


def assign(obs, me, private, tasks, zones, forced=None):
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

    if day >= 29 and hour >= 15:
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
            d = dist(pos[i], tgt)
            eff = pr + (2000 if d == 0 else 0) + (150 if in_zone else 0) - 25 * d
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

    endgame_drop = (day >= 29 and hour >= 7) or (day >= 28 and hour >= 19)
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

    if not (day >= 29 and hour >= 15):
        pend = [t[1] for t in ordered] + [c for z in zones for c in z]
        for i in range(n):
            if busy[i] or not pend:
                continue
            tgt = min(pend, key=lambda c: dist(pos[i], c))
            if tgt != pos[i]:
                actions[i] = step_toward(pos[i], tgt)
    return actions


# --------------------------------------------------------------------------- #
#  The factory                                                               #
# --------------------------------------------------------------------------- #
def make_agent(config=None):
    cfg = {
        "name": "engine",
        "use_animals": True,
        "hire_fn": _default_hire_fn,
        "land_ok_fn": _default_land_ok_fn,
        "animal_target_fn": None,          # bound to the v5 default below
        "crop_cfg": _DEFAULT_CROP_CFG,
        "crop_caps_fn": _default_caps_fn,
        "plant_water_slack": 22,
        "reserve_early": 200,
        "reserve_late": 60,
        "sell_keep_prem": 0.80,
        "sell_keep_staple": 0.72,
        "sell_cap_prem": 6,
        "sell_cap_staple": 16,
        "sell_cap_contested": 8,
        "contested_skip_frac": 0.5,
        "sell_cap_override": {},
        "sell_keep_override": {},
        "seed_cap": 12,
        "seed_lookahead": 2,
    }
    cfg.update(config or {})
    if cfg["animal_target_fn"] is None:
        _use = cfg["use_animals"]
        cfg["animal_target_fn"] = lambda obs, me: _default_animal_targets(obs, me, _use)

    def choose_crops(obs, me, private, counts, plant_slots):
        day = obs.get("day", 0)
        prices = (obs.get("market") or {}).get("prices", {})
        demand = demand_counts(obs)
        opp = field_counts(obs["farms"][1 - obs["player"]])
        total = max(1, sum(counts.values()) + plant_slots)
        early = day < 7
        targets = {}
        for crop, cc in cfg["crop_cfg"].items():
            spec = CROPS.get(crop)
            if spec is None or day > spec[4]:
                continue
            if "min_day" in cc and day < cc["min_day"]:
                continue
            pr = prices.get(crop, BASE[crop])
            val = pr / BASE[crop]
            if early:
                share = cc.get("early", 0.0)
            else:
                share = cc.get("main", 0.0) + cc.get("main_demand", 0.0) * demand[crop]
                lt = cc.get("late")
                if lt and day > lt[0]:
                    share += lt[1]
                lm = cc.get("late_mul")
                if lm and day > lm[0]:
                    share *= lm[1]
                vg = cc.get("val_gate")
                if vg is not None and val < vg:
                    share = 0.0
            share *= max(0.30, min(2.0, val))
            share *= max(0.35, 1.0 - 0.18 * opp[crop])
            if share > 0:
                targets[crop] = share
        if not targets:
            return []
        ssum = sum(targets.values())
        want = {c: s / ssum * total for c, s in targets.items()}
        caps = cfg["crop_caps_fn"](day, early)
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

    def add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved=()):
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        if day >= 27 or hour >= 22:
            return
        reserved = set(reserved)
        tiles = me["tiles"]
        planted = sum(counts.values())
        capacity = len(unlocked_cells(me))
        unwatered = sum(
            1 for row in tiles for t in row
            if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today")
        )
        room = min(capacity - planted,
                   max(0, n_units * cfg["plant_water_slack"] - unwatered))
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
        picks = choose_crops(obs, me, private, counts, min(room, len(empty), n_units * 2))
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
            tasks.append((1800, (x, y), ["PLANT", crop]))

    def market_orders(obs, me, private, counts, n_units):
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        money = float(me.get("money", 0))
        shed = private.get("shed", {}) or {}
        seeds = private.get("seeds", {}) or {}
        mkt_inv = ((obs.get("market") or {}).get("inventory", {})) or {}
        reserve = cfg["reserve_early"] if day < 25 else cfg["reserve_late"]

        hires, sells, buys_hi, buys_lo = [], [], [], []

        if hour <= 1:
            nq = len(me.get("unlocked_quadrants", []))
            desired = cfg["hire_fn"](day, nq)
            for _ in range(max(0, desired - int(me.get("hires_today", 0)))):
                hires.append(["HIRE"])

        n_placed = sum(1 for row in me["tiles"] for t in row
                       if isinstance(t, dict) and t.get("animal"))
        wheat_floor = (2 * n_placed + 4) if (cfg["use_animals"] and n_placed and day < 28) else 0
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
            if day >= 28:
                amount = qty
            elif contested and p0 < cfg["contested_skip_frac"] * base:
                amount = 0
            else:
                prem = item in PREMIUM
                keep_frac = cfg["sell_keep_override"].get(
                    item, cfg["sell_keep_prem"] if prem else cfg["sell_keep_staple"])
                keep = keep_frac * base
                if item in cfg["sell_cap_override"]:
                    cap = cfg["sell_cap_override"][item]
                else:
                    cap = cfg["sell_cap_prem"] if prem else cfg["sell_cap_staple"]
                    if contested:
                        cap = cfg["sell_cap_contested"]
                if p0 >= 1.4 * base:
                    cap = int(cap * min(4.0, p0 / base))
                amount = 0
                while amount < min(qty, cap) and price_at(item, inv0 + 2 * amount) >= keep:
                    amount += 1
                if amount == 0 and p0 >= 0.55 * base and not contested:
                    amount = 1
            if amount > 0:
                sells.append((p0 * amount, ["SELL", item, amount]))
        sells.sort(key=lambda s: -s[0])
        sells = [s[1] for s in sells]

        unlocked = list(me.get("unlocked_quadrants", []))
        open_tiles = len(unlocked_cells(me))
        if hour <= 3 and len(unlocked) < 4:
            nth = len(unlocked) - 1                    # 0/1 -> quad 2/3, 2 -> quad 4
            cost = (1000, 2000, 4000)[nth]
            fill = sum(counts.values()) / max(1, open_tiles)
            if cfg["land_ok_fn"](nth, day, fill, money, cost):
                buys_hi.append(["BUY_LAND"])

        if cfg["use_animals"]:
            have = Counter()
            for row in me["tiles"]:
                for t in row:
                    if isinstance(t, dict) and t.get("animal"):
                        have[t["animal"]] += 1
            placed_total = sum(have.values())
            pending = int(sum(v for k, v in shed.items() if k in ANIMALS))
            if hour <= 6:
                for a, want in cfg["animal_target_fn"](obs, me).items():
                    cur = have[a] + int(shed.get(a, 0))
                    if cur < want and money >= ANIMALS[a][0] + 300 + 150 * placed_total:
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
            need = Counter(choose_crops(obs, me, private, counts,
                                        n_units * cfg["seed_lookahead"]))
            buf = 3 if n_units <= 4 else 4
            for crop in sorted(need, key=lambda c: -need[c]):
                have = int(seeds.get(crop, 0))
                target = min(need[crop] + buf, cfg["seed_cap"])
                cost = CROPS[crop][0]
                b = min(max(0, target - have), int(max(0, money - reserve) // max(1, cost)))
                if b > 0:
                    buys_lo.append(["BUY_SEED", crop, b])
                    money -= b * cost

        if day >= 29:
            out = sells + hires + buys_hi + buys_lo
        else:
            out = hires + sells[:3] + buys_hi + buys_lo + sells[3:]
        return out[:10]

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

            reserved = (animal_tiles(me, cfg["animal_target_fn"](obs, me))
                        if cfg["use_animals"] else [])
            forced = {}
            n_crew = 0
            if reserved and obs.get("day", 0) < 29:
                n_animals = sum(1 for row in me["tiles"] for t in row
                                if isinstance(t, dict) and t.get("animal"))
                n_crew = min(4, max(0, n_units - 6),
                             1 + max(n_animals, len(reserved)) // 5)
                if n_crew > 0:
                    crew_idx = list(range(n_units - n_crew, n_units))
                    positions = ([tuple(me["farmer"])]
                                 + [tuple(p) for p in me.get("hands", [])])
                    invs = private.get("inventories", []) or []
                    forced = animal_crew_actions(obs, me, private, reserved,
                                                 crew_idx, positions, invs)

            zones = make_zones(cells, max(1, n_units - n_crew))
            zones += [set() for _ in range(n_units - len(zones))]

            tasks, counts = build_tasks(obs, me, private)
            add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved)
            actions = assign(obs, me, private, tasks, zones, forced=forced)

            market = market_orders(obs, me, private, counts, n_units)
            return {"farmer": actions[0], "hands": actions[1:], "market": market}
        except Exception:
            try:
                n = len(obs["farms"][obs["player"]].get("hands", []))
            except Exception:
                n = 0
            return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(n)], "market": []}

    return agent
