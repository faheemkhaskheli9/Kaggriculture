"""Kaggriculture v12 experimental executor.

Keeps v11's economy, crop selection, animal crew, safety priorities, and market
logic. Replaces only the generic crop-task allocator with:

* maximum-weight joint unit/task assignment (Hungarian algorithm),
* deadline-slack penalties for work that cannot be reached before day end,
* a bounded second-stop route bonus, and
* soft route commitment within a day.

This file intentionally imports ``main.py`` so v11 remains untouched and is an
easy rollback. A Kaggle submission must bundle both files, or be flattened after
promotion.
"""

from collections import defaultdict

import main as v11


# (player, day, unit index) -> (primary target, suggested next target)
_ROUTE_MEMORY = {}
_IMPOSSIBLE = -10**9


def _hungarian_max(weights):
    """Return one distinct column per row, maximizing total integer weight.

    Rectangular Hungarian implementation for rows <= columns. Forbidden edges
    use _IMPOSSIBLE. Every caller supplies at least one private idle column per
    row, so a feasible complete matching always exists.
    """
    n = len(weights)
    if not n:
        return []
    m = len(weights[0])
    if n > m:
        raise ValueError("Hungarian assignment requires rows <= columns")

    max_w = max(max(row) for row in weights)
    # Standard 1-indexed minimization algorithm. Transform max weight to cost.
    costs = [[max_w - w for w in row] for row in weights]
    u = [0] * (n + 1)
    v = [0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)
    inf = 10**18

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = costs[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    result = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            result[p[j] - 1] = j - 1
    return result


def _unique_tasks(tasks):
    """Match v11's claimed-tile semantics: retain best operation per tile."""
    best = {}
    for priority, target, action in tasks:
        old = best.get(target)
        if old is None or priority > old[0]:
            best[target] = (priority, target, action)
    return sorted(best.values(), key=lambda task: (-task[0], task[1]))


def _deadline_penalty(obs, priority, action, travel):
    """Penalty for a route whose first operation risks missing today's reset."""
    remaining = max(0, 24 - int(obs.get("hour", 0)))
    required = travel + 1  # move turns followed by the on-tile operation
    late = max(0, required - remaining)
    if not late:
        return 0
    if priority >= 9000:       # dies/escapes at this end-of-day boundary
        # Preserve the safety task's dominance while steering the *closest*
        # available unit toward it. A catastrophic penalty would perversely
        # make an already-late rescue less attractive than a local harvest.
        return 500 * late
    if action and action[0] in {"WATER", "FEED"}:
        return 700 * late
    return 80 * late


def _followup_bonus(position, primary, tasks, zone):
    """Small two-stop insertion value; deliberately cannot dominate priority."""
    best = 0
    best_target = None
    for priority, target, action in tasks:
        if target == primary:
            continue
        if action == ["DIG"] and target not in zone:
            continue
        leg = v11.dist(primary, target)
        # Cap the bonus: it should break close assignment ties, not defer safety.
        value = min(220, priority // 25) - 18 * leg
        if target in zone:
            value += 30
        if value > best:
            best = value
            best_target = target
    return max(0, best), best_target


def assign(obs, me, private, tasks, zones, forced=None):
    """Joint deadline-aware assignment with v11-compatible safety/endgame."""
    positions = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
    n = len(positions)
    invs = list(private.get("inventories", []))
    while len(invs) < n:
        invs.append({})
    actions = [["PASS"] for _ in range(n)]
    busy = [False] * n
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    player = int(obs.get("player", 0))

    # A true game start (day 0, hour 0) must not inherit route suggestions from
    # a previous game's map when this module stays loaded across many games in
    # one process (test.py is always single-process; compete.py reuses worker
    # processes across their assigned games). The per-call staleness prune below
    # only drops entries whose *day* differs from the current one, so a leftover
    # day-0 entry for this player from the last game would otherwise survive
    # into the next game's very first assignment call.
    if day == 0 and hour == 0:
        for key in [k for k in _ROUTE_MEMORY if k[0] == player]:
            _ROUTE_MEMORY.pop(key, None)

    for idx, action in (forced or {}).items():
        if 0 <= idx < n and action:
            actions[idx] = action
            busy[idx] = True

    # Preserve v11's hard final-day delivery override.
    if day >= 29 and hour >= 15:
        for i, position in enumerate(positions):
            if v11.inv_total(invs[i]) > 0:
                shed = min(v11.SHED_TILES, key=lambda q: v11.dist(position, q))
                actions[i] = (["DROP"] if position in v11.SHED_TILES
                              else v11.step_toward(position, shed))
                busy[i] = True

    available = [i for i in range(n) if not busy[i]]
    candidates = _unique_tasks(tasks)
    chosen_followups = {}

    if available and candidates:
        weights = []
        followups = {}
        for row, i in enumerate(available):
            position = positions[i]
            zone = zones[i] if i < len(zones) else set()
            remembered = _ROUTE_MEMORY.get((player, day, i))
            has_zone_task = any(target in zone for _, target, _ in candidates)
            row_weights = []
            for col, (priority, target, action) in enumerate(candidates):
                in_zone = target in zone
                if action == ["DIG"] and not in_zone:
                    row_weights.append(_IMPOSSIBLE)
                    continue
                # v11's strongest routing invariant is zone-first allocation.
                # Keep that invariant for routine work; only true survival
                # tasks may pull a unit across the farm while its zone is busy.
                if priority < 9000 and has_zone_task and not in_zone:
                    row_weights.append(_IMPOSSIBLE)
                    continue
                travel = v11.dist(position, target)
                step_cost = 25 if in_zone else 40
                value = priority + (2000 if travel == 0 else 0)
                value += 150 if in_zone else 0
                value -= step_cost * travel
                value -= _deadline_penalty(obs, priority, action, travel)

                # Soft commitment: primary target gets more credit than the
                # previously suggested second stop. Both remain easy to override.
                if remembered:
                    if target == remembered[0]:
                        value += 90
                    elif target == remembered[1]:
                        value += 55

                bonus, next_target = _followup_bonus(position, target, candidates, zone)
                value += bonus
                followups[(row, col)] = next_target
                row_weights.append(value)

            # Private idle columns make the matrix feasible and prevent two rows
            # from competing for the same generic idle option.
            for idle_owner in range(len(available)):
                row_weights.append(0 if idle_owner == row else _IMPOSSIBLE)
            weights.append(row_weights)

        assignment = _hungarian_max(weights)
        for row, col in enumerate(assignment):
            i = available[row]
            if 0 <= col < len(candidates) and weights[row][col] > 0:
                _, target, action = candidates[col]
                actions[i] = (action if positions[i] == target
                              else v11.step_toward(positions[i], target))
                busy[i] = True
                chosen_followups[i] = (target, followups.get((row, col)))

    # Preserve v11's endgame shed staging for unassigned units.
    endgame_drop = (day >= 29 and hour >= 7) or (day >= 28 and hour >= 19)
    if endgame_drop:
        for i, position in enumerate(positions):
            if busy[i]:
                continue
            shed = min(v11.SHED_TILES, key=lambda q: v11.dist(position, q))
            if v11.inv_total(invs[i]) > 0:
                actions[i] = (["DROP"] if position in v11.SHED_TILES
                              else v11.step_toward(position, shed))
                busy[i] = True
            elif day >= 29:
                if position != shed:
                    actions[i] = v11.step_toward(position, shed)
                busy[i] = True

    # Idle repositioning follows v11: prefer own-zone pending work/cells.
    if not (day >= 29 and hour >= 15):
        task_tiles = [task[1] for task in candidates]
        all_pending = task_tiles + [cell for zone in zones for cell in zone]
        for i, position in enumerate(positions):
            if busy[i]:
                continue
            zone = zones[i] if i < len(zones) else set()
            own = [target for target in task_tiles if target in zone] or list(zone)
            pending = own or all_pending
            if pending:
                target = min(pending, key=lambda cell: v11.dist(position, cell))
                if target != position:
                    actions[i] = v11.step_toward(position, target)

    # Drop stale days and remember this turn's short route suggestion.
    stale = [key for key in _ROUTE_MEMORY if key[0] == player and key[1] != day]
    for key in stale:
        _ROUTE_MEMORY.pop(key, None)
    for i, route in chosen_followups.items():
        _ROUTE_MEMORY[(player, day, i)] = route
    return actions


def agent(obs):
    """v11 policy and market logic with the v12 executor."""
    try:
        player = int(obs.get("player", 0))
        farms = obs.get("farms", [])
        if len(farms) < 2:
            return {"farmer": ["PASS"], "hands": [], "market": []}
        me = farms[player]
        private = obs.get("private") or {}
        n_units = 1 + len(me.get("hands", []))
        cells = v11.unlocked_cells(me)

        reserved = (v11.animal_tiles(me, v11.animal_targets(obs, me))
                    if v11.USE_ANIMALS else [])
        forced = {}
        n_crew = 0
        if reserved and obs.get("day", 0) < 29:
            n_animals = sum(
                1 for row in me["tiles"] for tile in row
                if isinstance(tile, dict) and tile.get("animal")
            )
            n_crew = min(4, max(0, n_units - 6),
                         1 + max(n_animals, len(reserved)) // 5)
            if n_crew > 0:
                crew_idx = list(range(n_units - n_crew, n_units))
                positions = ([tuple(me["farmer"])]
                             + [tuple(p) for p in me.get("hands", [])])
                invs = private.get("inventories", []) or []
                forced = v11.animal_crew_actions(
                    obs, me, private, reserved, crew_idx, positions, invs
                )

        zones = v11.make_zones(cells, max(1, n_units - n_crew))
        zones += [set() for _ in range(n_units - len(zones))]
        tasks, counts = v11.build_tasks(obs, me, private)
        v11.add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved)
        unit_actions = assign(obs, me, private, tasks, zones, forced=forced)
        market = v11.market_orders(obs, me, private, counts, n_units)
        return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market}
    except Exception:
        try:
            n_hands = len(obs["farms"][obs["player"]].get("hands", []))
        except Exception:
            n_hands = 0
        return {"farmer": ["PASS"],
                "hands": [["PASS"] for _ in range(n_hands)], "market": []}


if __name__ == "__main__":
    print("Kaggriculture Agent v12 (v11 + joint deadline-aware route assignment)")
