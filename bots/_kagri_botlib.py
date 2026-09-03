"""Shared engine for the Kaggriculture benchmark bots.

These are *opponent models*, not competition entries: each one reproduces a
strategy that beats our agent on the real ladder (see PLAN_3000_v4.md section 2.1)
so `test.py` can measure candidate changes against a competent opponent instead of
only `starter`/self-play.

`make_agent(config)` returns an `agent(obs)` callable. Every bot file is
`agent = make_agent({...})` plus its archetype config.
"""
from collections import Counter

MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]

CROPS = {  # seed, first_yield_day, max_yield_day, ongoing, interval
    "WHEAT":      (10, 2, 4, False, 0),
    "CARROT":     (20, 2, 3, False, 0),
    "TOMATO":     (50, 8, 8, True, 1),
    "STRAWBERRY": (100, 10, 10, True, 2),
    "MELON":      (80, 10, 12, False, 0),
}
ANIMALS = {  # cost, structure, build_op, first_yield_day, product
    "GOOSE": (300, "COOP", "BUILD_COOP", 4, "EGG"),
    "COW":   (400, "PASTURE", "BUILD_PASTURE", 8, "MILK"),
    "SHEEP": (500, "PASTURE", "BUILD_PASTURE", 6, "WOOL"),
}
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
        "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
SHED_TILES = [(4, 4), (5, 4), (4, 5), (5, 5)]


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step(a, b):
    if a[0] < b[0]:
        return ["EAST"]
    if a[0] > b[0]:
        return ["WEST"]
    if a[1] < b[1]:
        return ["SOUTH"]
    if a[1] > b[1]:
        return ["NORTH"]
    return ["PASS"]


def _to_shed(p):
    return _step(p, min(SHED_TILES, key=lambda q: _dist(p, q)))


def _cells(me):
    out = []
    for y, row in enumerate(me["tiles"]):
        for x, t in enumerate(row):
            if t != "LOCKED":
                out.append((x, y))
    return out


def make_agent(config):
    cfg = {
        "quadrant_target": 3,
        "land_fill_gate": 0.55,
        "land_day_gate": 18,
        "hire_target": 8,
        "crops": {"WHEAT": 1.0},
        "crop_cap": {},
        "animals": {},
        "sell_cap": 16,
        "premium_sell_cap": 8,
        "sell_floor_frac": 0.0,
        "plant_fill": True,
        "reserve": 150,
        # herd-buy pacing. Defaults reproduce the original hardcoded behaviour
        # (one animal/turn, a fat running-cost buffer, wait for 2 quadrants).
        # bot_animalfactory_v2 turns these up to model the strong ladder herd.
        "animals_per_turn": 1,
        "animal_buffer_base": 500,
        "animal_buffer_per_head": 120,
        "animal_min_quadrants": None,   # None -> min(2, quad_target(day))
    }
    cfg.update(config)

    def _hire_target(day, nq, n_units):
        h = cfg["hire_target"]
        return h(day, nq, n_units) if callable(h) else h

    def _quad_target(day):
        q = cfg["quadrant_target"]
        return q(day) if callable(q) else q

    def _want_counts(me, n_slots):
        """Target planting picks given weights + caps, filling toward capacity."""
        cur = Counter()
        for row in me["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("kind") == "PLANT":
                    cur[t["crop"]] += 1
        weights = cfg["crops"]
        if not weights:
            return []
        cap_tiles = len(_cells(me))
        wsum = sum(weights.values())
        target = {c: w / wsum * cap_tiles for c, w in weights.items()}
        picks = []
        for _ in range(n_slots):
            best, bestgap = None, -1e9
            for c, w in target.items():
                lim = cfg["crop_cap"].get(c)
                if lim is not None and cur[c] >= lim:
                    continue
                gap = w - cur[c]
                if gap > bestgap:
                    best, bestgap = c, gap
            if best is None:
                break
            picks.append(best)
            cur[best] += 1
        return picks

    def agent(obs):
        try:
            return _act(obs)
        except Exception:
            try:
                n = len(obs["farms"][obs["player"]].get("hands", []))
            except Exception:
                n = 0
            return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}

    def _act(obs):
        player = int(obs.get("player", 0))
        me = obs["farms"][player]
        priv = obs.get("private") or {}
        day = int(obs.get("day", 0))
        hour = int(obs.get("hour", 0))
        tiles = me["tiles"]
        shed = dict(priv.get("shed") or {})
        seeds = dict(priv.get("seeds") or {})
        invs = list(priv.get("inventories") or [{}])
        money = float(me.get("money", 0))
        mkt_inv = ((obs.get("market") or {}).get("inventory") or {})
        mkt_prices = ((obs.get("market") or {}).get("prices") or {})

        units = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
        n = len(units)
        while len(invs) < n:
            invs.append({})

        liquidate = day >= 29 and hour >= 12
        placed_animals = [((x, y), t) for y, row in enumerate(tiles)
                          for x, t in enumerate(row)
                          if isinstance(t, dict) and t.get("animal")]

        # persistent contiguous per-unit zones (kills movement thrash)
        swept = []
        for yy, row in enumerate(tiles):
            xs = range(len(row)) if yy % 2 == 0 else range(len(row) - 1, -1, -1)
            for xx in xs:
                if row[xx] != "LOCKED":
                    swept.append((xx, yy))
        nz = max(1, n)
        per = len(swept) / nz if swept else 0
        zones = [set(swept[int(round(i * per)):int(round((i + 1) * per))]) for i in range(nz)]
        for i in range(nz):
            if not zones[i] and swept:
                zones[i].add(swept[min(i, len(swept) - 1)])

        # ---------- build task list ----------
        want_animal_tiles = _animal_reservation(me, cfg["animals"])
        reserved = set(want_animal_tiles) - {p for p, _ in placed_animals}
        # only open as many new PLANT tasks as the crew can actually keep watered
        # (unwatered backlog throttle -- without this the field over-plants, crops
        # never reach their yield window, and empty-ish tiles turn to weeds)
        unwatered_now = sum(
            1 for row in tiles for t in row
            if isinstance(t, dict) and t.get("kind") == "PLANT"
            and not t.get("watered_today"))
        room = max(0, n * 18 - unwatered_now)
        picks = _want_counts(me, min(n * 2, room)) if (
            cfg["plant_fill"] and not liquidate and day < 27 and hour < 22) else []
        seed_budget = Counter({c: int(seeds.get(c, 0)) for c in CROPS})
        pick_i = [0]

        def next_plant():
            while pick_i[0] < len(picks):
                c = picks[pick_i[0]]
                pick_i[0] += 1
                if seed_budget[c] > 0:
                    seed_budget[c] -= 1
                    return c
            return None

        tasks = []  # (priority, (x,y), action)
        for y, row in enumerate(tiles):
            for x, t in enumerate(row):
                pos = (x, y)
                if not isinstance(t, dict):
                    if (t is None and pos not in reserved and picks
                            and pick_i[0] < len(picks)):
                        c = next_plant()
                        if c:
                            tasks.append((1500, pos, ["PLANT", c]))
                    continue
                kind = t.get("kind")
                if kind == "PLANT":
                    crop = t["crop"]
                    fy, my, ongoing = CROPS[crop][1], CROPS[crop][2], CROPS[crop][3]
                    age = day - t.get("planted_day", day)
                    yu = t.get("yield_units", 0)
                    if liquidate:
                        if yu > 0 and age >= fy:
                            tasks.append((6000, pos, ["HARVEST"]))
                        continue
                    in_window = (not ongoing) and (my + 1) // 2 <= age <= my
                    if not t.get("watered_today", False):
                        if t.get("consecutive_unwatered", 0) >= 1:
                            tasks.append((9000 + hour, pos, ["WATER"]))
                        elif in_window:
                            tasks.append((6000 + age, pos, ["WATER"]))  # grows yield
                        else:
                            tasks.append((2500, pos, ["WATER"]))
                    if yu > 0 and age >= fy:
                        if not ongoing:
                            # let it fatten: harvest only once past its yield window
                            tasks.append((5200 if age >= my else 1000, pos, ["HARVEST"]))
                        else:
                            tasks.append((5200 if yu >= 4 else 3000, pos, ["HARVEST"]))
                elif kind in ("COOP", "PASTURE") and t.get("animal"):
                    if t.get("yield_units", 0) > 0:
                        tasks.append((5000, pos, ["HARVEST"]))
                    if t.get("fertilizer_available", False) and not liquidate:
                        tasks.append((2600, pos, ["COLLECT_FERTILIZER"]))
                    if not liquidate and not t.get("fed_today", False):
                        tasks.append((7000, pos, ["FEED"]))       # needs wheat in inv
                    if (not liquidate and t.get("fed_today", False)
                            and not t.get("cared_today", False)):
                        tasks.append((2400, pos, ["CARE"]))
                elif kind == "WEED":
                    tasks.append((800 if not liquidate else 0, pos, ["DIG"]))

        # place bought animals sitting in the shed onto matching empty structures
        # (survival-tier: a paid-for animal doing nothing is pure waste)
        empty_struct = [((x, y), t.get("kind")) for y, row in enumerate(tiles)
                        for x, t in enumerate(row)
                        if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE")
                        and not t.get("animal")]
        shed_animals = [a for a in ANIMALS if int(shed.get(a, 0)) > 0]
        struct_kinds = {k for _, k in empty_struct}
        for (pos, k) in empty_struct:
            a = next((a for a in shed_animals if ANIMALS[a][1] == k), None)
            if a:
                tasks.append((9500, pos, ["PLACE", a]))
        # build a structure ahead of the animals we still intend to buy
        need_a = _first_needed_animal(me, shed, cfg["animals"])
        if need_a and ANIMALS[need_a][1] not in struct_kinds:
            for (x, y) in reserved:
                if tiles[y][x] is None:
                    tasks.append((9200, (x, y), [ANIMALS[need_a][2]]))
                    break

        # ---------- assign units greedily ----------
        actions = [["PASS"]] * n
        claimed = set()
        order = sorted(tasks, key=lambda z: -z[0])

        if day >= 29 and hour >= 16:
            # final drop run
            for i, p in enumerate(units):
                if sum(int(v) for v in (invs[i] or {}).values()) > 0:
                    actions[i] = ["DROP"] if tuple(p) in SHED_TILES else _to_shed(p)
                else:
                    actions[i] = ["PASS"]
            mk = _market(obs, me, priv, cfg, _hire_target, _quad_target,
                         _want_counts, money, shed, seeds, mkt_inv, mkt_prices,
                         day, hour, n, placed_animals, liquidate)
            return {"farmer": actions[0], "hands": actions[1:], "market": mk}

        done = [False] * n

        def _resolve(i, p, act, tgt, inv):
            if act[0] == "PLACE" and int(inv.get(act[1], 0)) <= 0:
                if tuple(p) in SHED_TILES:
                    shed[act[1]] = max(0, int(shed.get(act[1], 0)) - 1)
                    return ["PICKUP", act[1], 1]
                return _to_shed(p)
            if tuple(p) == tgt:
                return act
            return _step(p, tgt)

        def _pick(i, allow_global):
            p = units[i]
            inv = invs[i] or {}
            best = None
            for pr, tgt, act in order:
                if tgt in claimed:
                    continue
                if act[0] == "FEED" and int(inv.get("WHEAT", 0)) <= 0:
                    continue
                in_zone = tgt in zones[i]
                if not allow_global and not in_zone and pr < 9000:
                    continue
                d = _dist(p, tgt)
                eff = pr + (4000 if d == 0 else 0) + (600 if in_zone else 0) - 55 * d
                if best is None or eff > best[0]:
                    best = (eff, tgt, act)
            if best is None:
                return False
            _, tgt, act = best
            claimed.add(tgt)
            actions[i] = _resolve(i, p, act, tgt, inv)
            done[i] = True
            return True

        # pass 0: survival work (dying plant / hungry animal) -> globally nearest idle unit
        for pr, tgt, act in order:
            if pr < 9000 or tgt in claimed:
                continue
            cand = sorted((_dist(units[i], tgt), i) for i in range(n)
                          if not done[i] and not (act[0] == "FEED"
                          and int((invs[i] or {}).get("WHEAT", 0)) <= 0))
            if cand:
                i = cand[0][1]
                claimed.add(tgt)
                actions[i] = _resolve(i, units[i], act, tgt, invs[i] or {})
                done[i] = True

        for i in range(n):
            if not done[i]:
                _pick(i, allow_global=False)
        for i in range(n):
            if not done[i]:
                _pick(i, allow_global=True)

        # still idle: fetch feed wheat, else creep toward own zone's pending work
        pend = [t[1] for t in order]
        for i in range(n):
            if done[i]:
                continue
            p = units[i]
            inv = invs[i] or {}
            if placed_animals and int(inv.get("WHEAT", 0)) == 0 and int(shed.get("WHEAT", 0)) > 0:
                if tuple(p) in SHED_TILES:
                    actions[i] = ["PICKUP", "WHEAT", min(6, int(shed.get("WHEAT", 0)))]
                    shed["WHEAT"] = int(shed.get("WHEAT", 0)) - 6
                else:
                    actions[i] = _to_shed(p)
                continue
            targets_pool = [c for c in pend if c in zones[i]] or list(zones[i]) or pend
            if targets_pool:
                tgt = min(targets_pool, key=lambda c: _dist(p, c))
                if tgt != tuple(p):
                    actions[i] = _step(p, tgt)

        mk = _market(obs, me, priv, cfg, _hire_target, _quad_target, _want_counts,
                     money, shed, seeds, mkt_inv, mkt_prices, day, hour, n,
                     placed_animals, liquidate)
        return {"farmer": actions[0], "hands": actions[1:], "market": mk}

    return agent


def _animal_reservation(me, targets):
    if not targets:
        return []
    tiles = me["tiles"]
    existing = [(x, y) for y, row in enumerate(tiles) for x, t in enumerate(row)
                if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE")]
    k = sum(targets.values())
    if k <= len(existing):
        return existing
    taken = set(existing)
    free = sorted(((x, y) for y, row in enumerate(tiles) for x, t in enumerate(row)
                   if t != "LOCKED" and (x, y) not in SHED_TILES and (x, y) not in taken
                   and not (isinstance(t, dict) and "animal" in t)),
                  key=lambda c: (abs(c[0] - 4.5) + abs(c[1] - 4.5), c))
    return existing + free[:k - len(existing)]


def _placed(me):
    c = Counter()
    for row in me["tiles"]:
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                c[t["animal"]] += 1
    return c


def _first_needed_animal(me, shed, targets):
    have = _placed(me)
    for a, want in targets.items():
        if have[a] + int(shed.get(a, 0)) < want:
            return a
    return None


def _market(obs, me, priv, cfg, hire_target, quad_target, want_counts, money,
            shed, seeds, mkt_inv, mkt_prices, day, hour, n_units, placed_animals,
            liquidate):
    out = []
    reserve = cfg["reserve"]
    nq = len(me.get("unlocked_quadrants", []))

    # hiring
    if hour <= 1:
        want = hire_target(day, nq, n_units)
        for _ in range(max(0, want - int(me.get("hires_today", 0)))):
            out.append(["HIRE"])

    # land
    if hour <= 3 and nq < quad_target(day) and nq - 1 < len(LAND_PRICES):
        cost = LAND_PRICES[nq - 1]
        planted = sum(1 for row in me["tiles"] for t in row
                      if isinstance(t, dict) and t.get("kind") == "PLANT")
        cap = len(_cells(me))
        fill = planted / max(1, cap)
        if (fill >= cfg["land_fill_gate"] or day >= cfg["land_day_gate"]) and money >= cost + 200:
            out.append(["BUY_LAND"])
            money -= cost

    # animals: one per turn at dawn, but only once land expansion is under way and
    # with a running-cost buffer that grows with the herd (avoids cash collapse)
    amq = cfg["animal_min_quadrants"]
    gate_q = min(2, quad_target(day)) if amq is None else amq
    if cfg["animals"] and hour <= 6 and nq >= gate_q:
        have = _placed(me)
        herd = sum(have.values()) + sum(int(shed.get(a, 0)) for a in ANIMALS)
        bought = 0
        for a, want in cfg["animals"].items():
            if bought >= cfg["animals_per_turn"]:
                break
            cur = have[a] + int(shed.get(a, 0))
            while (cur < want and bought < cfg["animals_per_turn"]
                   and money >= ANIMALS[a][0] + cfg["animal_buffer_base"]
                   + cfg["animal_buffer_per_head"] * herd):
                out.append(["BUY_ANIMAL", a, 1])
                money -= ANIMALS[a][0]
                cur += 1
                herd += 1
                bought += 1

    # wheat for feed
    if placed_animals and hour <= 4:
        need = 2 * len(placed_animals) + 4
        have_w = int(shed.get("WHEAT", 0))
        if have_w < need:
            wp = max(1, int(mkt_prices.get("WHEAT", 25)))
            b = min(need - have_w, 10, int(max(0, money - reserve) // wp))
            if b > 0:
                out.append(["BUY_PRODUCT", "WHEAT", b])
                money -= b * wp

    # selling
    sells = []
    for item, qty in list(shed.items()):
        qty = int(qty)
        if item not in BASE or qty <= 0:
            continue
        if placed_animals and item == "WHEAT":
            qty -= 2 * len(placed_animals) + 4
        if qty <= 0:
            continue
        price = int(mkt_prices.get(item, BASE[item]))
        if not liquidate and cfg["sell_floor_frac"] and price < cfg["sell_floor_frac"] * BASE[item]:
            continue
        prem = item in ("STRAWBERRY", "MELON", "MILK", "WOOL")
        cap = cfg["premium_sell_cap"] if prem else cfg["sell_cap"]
        amount = qty if liquidate else min(qty, cap)
        if amount > 0:
            sells.append((price * amount, ["SELL", item, amount]))
    sells.sort(key=lambda s: -s[0])

    # seeds
    seed_buys = []
    if day < 27 and cfg["crops"]:
        need = Counter(want_counts(me, n_units * 2))
        for crop in sorted(need, key=lambda c: -need[c]):
            have = int(seeds.get(crop, 0))
            tgt = min(need[crop] + 4, 14)
            cost = CROPS[crop][0]
            b = min(max(0, tgt - have), int(max(0, money - reserve) // max(1, cost)))
            if b > 0:
                seed_buys.append(["BUY_SEED", crop, b])
                money -= b * cost

    out = out + [s[1] for s in sells[:4]] + seed_buys + [s[1] for s in sells[4:]]
    return out[:10]
