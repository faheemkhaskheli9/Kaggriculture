"""Hybrid action expander -- turns a learned per-unit *intent* + market scalars
into a legal Kaggriculture action dict, by reusing the deterministic task/zone/
assignment machinery from ``ml/engine.py``.

SCAFFOLD: the interface and the intent enum are fixed here so ``ml/rl/net.py``
and ``bc.py`` can be written against them; ``expand`` currently delegates to the
scripted engine (i.e. it ignores the intents) so it is always a legal no-op
baseline. Fill the ``TODO`` to actually bias task selection by intent.
"""
from __future__ import annotations

import enum

import main as teacher


class Intent(enum.IntEnum):
    IDLE = 0
    WATER = 1
    HARVEST = 2
    PLANT = 3
    PLACE_BUILD = 4
    FEED_CARE = 5
    MOVE_REGION = 6


N_INTENT = len(Intent)

# market head layout (indices into a flat float vector the policy emits)
SELL_FRAC_PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
                      "EGG", "MILK", "WOOL", "FERTILIZER"]
MARKET_TOGGLES = ["HIRE", "BUY_LAND", "BUY_COW", "BUY_GOOSE", "BUY_SHEEP"]
MARKET_VEC_LEN = len(SELL_FRAC_PRODUCTS) + len(MARKET_TOGGLES)

_SCRIPTED = teacher.agent


def _intent_matches(intent, action):
    op = action[0] if action else "PASS"
    groups = {
        Intent.IDLE: {"PASS"},
        Intent.WATER: {"WATER"},
        Intent.HARVEST: {"HARVEST", "DROP"},
        Intent.PLANT: {"PLANT", "DIG"},
        Intent.PLACE_BUILD: {"PLACE", "BUILD_COOP", "BUILD_PASTURE"},
        Intent.FEED_CARE: {"FEED", "CARE", "COLLECT_FERTILIZER", "PICKUP"},
        Intent.MOVE_REGION: {"NORTH", "SOUTH", "EAST", "WEST"},
    }
    try:
        return op in groups[Intent(int(intent))]
    except (ValueError, TypeError):
        return False


def _assign_with_intents(obs, me, private, tasks, zones, intents, forced=None):
    """Teacher assignment with a bounded intent bonus; emergencies remain global."""
    positions = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
    n = len(positions)
    invs = list(private.get("inventories", []))
    while len(invs) < n:
        invs.append({})
    actions, busy, claimed = [["PASS"] for _ in range(n)], [False] * n, set()
    day, hour = obs.get("day", 0), obs.get("hour", 0)
    for idx, act in (forced or {}).items():
        if 0 <= idx < n and act:
            actions[idx], busy[idx] = act, True
    if day >= 29 and hour >= 15:
        for i, pos in enumerate(positions):
            if teacher.inv_total(invs[i]) > 0:
                shed = min(teacher.SHED_TILES, key=lambda q: teacher.dist(pos, q))
                actions[i] = ["DROP"] if pos in teacher.SHED_TILES else teacher.step_toward(pos, shed)
                busy[i] = True
    ordered = sorted(tasks, key=lambda t: -t[0])

    def take(i, target, action):
        actions[i] = action if positions[i] == target else teacher.step_toward(positions[i], target)
        claimed.add(target)
        busy[i] = True

    for priority, target, action in ordered:
        if priority < 9000 or target in claimed:
            continue
        candidates = [(teacher.dist(positions[i], target), i) for i in range(n) if not busy[i]]
        if candidates:
            take(min(candidates)[1], target, action)

    def try_take(i, global_ok):
        best = None
        for priority, target, action in ordered:
            if target in claimed:
                continue
            in_zone = target in zones[i]
            if not global_ok and not in_zone:
                continue
            if action == ["DIG"] and not in_zone:
                continue
            distance = teacher.dist(positions[i], target)
            bonus = 900 if i < len(intents) and _intent_matches(intents[i], action) else 0
            score = priority + bonus + (2000 if distance == 0 else 0) + (150 if in_zone else 0) - 25 * distance
            if best is None or score > best[0]:
                best = score, target, action
        if best is not None:
            take(i, best[1], best[2])
            return True
        return False

    for i in range(n):
        if not busy[i]:
            try_take(i, False)
    for i in range(n):
        if not busy[i]:
            try_take(i, True)
    # Preserve the teacher's carefully tested endgame behavior for any idle unit.
    baseline = _SCRIPTED(obs)
    base_actions = [baseline.get("farmer", ["PASS"])] + list(baseline.get("hands", []))
    for i in range(n):
        if not busy[i] and i < len(base_actions):
            actions[i] = base_actions[i]
    return actions


def expand(obs: dict, intents=None, market_vec=None) -> dict:
    """intents: iterable[int] length == n_units (farmer first). market_vec:
    float vector length MARKET_VEC_LEN (sell fractions in [0,1], toggles as
    logits/probs). Either may be None -> pure scripted baseline."""
    if intents is None and market_vec is None:
        return _SCRIPTED(obs)
    player = int(obs.get("player", 0))
    me, private = obs["farms"][player], obs.get("private") or {}
    n_units = 1 + len(me.get("hands", []))
    intents = list(intents or [])[:n_units]
    intents += [int(Intent.IDLE)] * (n_units - len(intents))
    cells = teacher.unlocked_cells(me)
    reserved = teacher.animal_tiles(me, teacher.animal_targets(obs, me)) if teacher.USE_ANIMALS else []
    forced, n_crew = {}, 0
    if reserved and obs.get("day", 0) < 29:
        n_animals = sum(1 for row in me["tiles"] for t in row
                        if isinstance(t, dict) and t.get("animal"))
        n_crew = min(4, max(0, n_units - 6), 1 + max(n_animals, len(reserved)) // 5)
        if n_crew:
            crew_idx = list(range(n_units - n_crew, n_units))
            positions = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
            forced = teacher.animal_crew_actions(obs, me, private, reserved, crew_idx,
                                                 positions, private.get("inventories", []) or [])
    zones = teacher.make_zones(cells, max(1, n_units - n_crew))
    zones += [set() for _ in range(n_units - len(zones))]
    tasks, counts = teacher.build_tasks(obs, me, private)
    teacher.add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved)
    actions = _assign_with_intents(obs, me, private, tasks, zones, intents, forced)
    # Market learning stays disabled in v1; retain transactional/safety behavior.
    market = teacher.market_orders(obs, me, private, counts, n_units)
    return {"farmer": actions[0], "hands": actions[1:], "market": market}


def infer_intent(unit_action) -> int:
    """Reverse map a scripted primitive -> the intent label (for BC targets)."""
    if not unit_action:
        return int(Intent.IDLE)
    op = unit_action[0]
    if op in ("NORTH", "SOUTH", "EAST", "WEST"):
        return int(Intent.MOVE_REGION)
    if op == "WATER":
        return int(Intent.WATER)
    if op == "HARVEST":
        return int(Intent.HARVEST)
    if op in ("PLANT", "DIG"):
        return int(Intent.PLANT)
    if op in ("PLACE", "BUILD_COOP", "BUILD_PASTURE"):
        return int(Intent.PLACE_BUILD)
    if op in ("FEED", "CARE", "COLLECT_FERTILIZER", "PICKUP"):
        return int(Intent.FEED_CARE)
    if op == "DROP":
        return int(Intent.HARVEST)
    return int(Intent.IDLE)
