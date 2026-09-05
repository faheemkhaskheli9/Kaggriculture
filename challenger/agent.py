"""Replacement-policy challenger -- entry point (IMPACT plan Sec. 8, Workstream B).

Three layers:
  1. strategic controller  -- ``challenger.strategy`` (replay-derived herd +
     quadrant + hand schedule mined from top-10 ladder replays).
  2. safety controller     -- ``main.build_tasks`` / ``main.animal_crew_actions``
     / the endgame overrides inside ``main.assign`` (verbatim incumbent).
  3. execution controller  -- ``main.assign`` Hungarian routing (verbatim
     incumbent).

Only layer 1 differs from the promoted ``main.py``. This module never imports
into or mutates ``main`` -- the incumbent and challenger stay independently
runnable, per the plan.
"""

import os
import sys

# When kaggle-environments / compete.py exec this file, __file__ may be unset and
# cwd is the repo root. Put both the repo root and this file's dir on sys.path so
# `import main` and `import strategy` resolve in every load path.
_here = (os.path.dirname(os.path.abspath(__file__))
         if "__file__" in globals() else os.path.join(os.getcwd(), "challenger"))
for _p in (_here, os.path.dirname(_here), os.getcwd()):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

import main  # noqa: E402

try:
    from challenger import strategy  # noqa: E402
except ImportError:  # loaded as a bare file (compete.py / kaggle get_last_callable)
    import strategy  # type: ignore  # noqa: E402


def agent(obs):
    """Incumbent policy/market/executor with a replay-derived strategic layer."""
    try:
        player = int(obs.get("player", 0))
        farms = obs.get("farms", [])
        if len(farms) < 2:
            return {"farmer": ["PASS"], "hands": [], "market": []}
        me = farms[player]
        private = obs.get("private") or {}
        n_units = 1 + len(me.get("hands", []))
        cells = main.unlocked_cells(me)

        intent = strategy.strategic_intent(obs, me)

        # Layer 1: herd size/species come from the mined day+quadrant schedule,
        # replacing main.animal_targets. Tile reservation + crew logic unchanged.
        if main.USE_ANIMALS:
            if strategy.ENABLE_HERD_SCHEDULE:
                targets = strategy.herd_target(obs, me)
            else:
                targets = main.animal_targets(obs, me)
            reserved = main.animal_tiles(me, targets)
        else:
            reserved = []

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
                forced = main.animal_crew_actions(
                    obs, me, private, reserved, crew_idx, positions, invs
                )

        zones = main.make_zones(cells, max(1, n_units - n_crew))
        zones += [set() for _ in range(n_units - len(zones))]
        tasks, counts = main.build_tasks(obs, me, private)
        main.add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved,
                             intent=intent)
        unit_actions = main.assign(obs, me, private, tasks, zones, forced=forced)
        market = main.market_orders(obs, me, private, counts, n_units, intent=intent)
        return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market}
    except Exception:
        try:
            n_hands = len(obs["farms"][obs["player"]].get("hands", []))
        except Exception:
            n_hands = 0
        return {"farmer": ["PASS"],
                "hands": [["PASS"] for _ in range(n_hands)], "market": []}


if __name__ == "__main__":
    print("Kaggriculture replacement-policy challenger v0 "
          "(main.py executor + replay-derived strategic controller)")
