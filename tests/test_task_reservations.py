"""Prove the reservation repair reaches agent() and preserves executed service."""
import copy
import importlib.util
from pathlib import Path
import unittest

from kaggle_environments.envs.kaggriculture import kaggriculture as engine


ROOT = Path(__file__).resolve().parents[1]


def load_agent(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


baseline = load_agent("reservations_baseline", "main.py")
candidate = load_agent("reservations_candidate", "experiments/candidate_task_reservations.py")


def observation(n_units=2, yield_units=3, fertilizer=True):
    tiles = [["LOCKED" for _ in range(10)] for _ in range(10)]
    for y in range(5):
        for x in range(5):
            tiles[y][x] = engine._new_plant("STRAWBERRY", 10, 24)
            tiles[y][x]["watered_today"] = True
    animal = engine._new_animal("COW", 5)
    animal.update(yield_units=yield_units, fertilizer_available=fertilizer,
                  fed_today=True, cared_today=True)
    tiles[3][4] = animal
    farm = {"money": 0, "tiles": tiles, "farmer": [4, 3],
            "hands": [[4, 3] for _ in range(n_units - 1)],
            "unlocked_quadrants": ["NW"], "hires_today": n_units - 1}
    return {"player": 0, "step": 250, "day": 10, "hour": 10,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"shed": {}, "seeds": {},
                        "inventories": [{} for _ in range(n_units)]},
            "market": {"prices": dict(candidate.BASE),
                       "inventory": {item: 10000 for item in candidate.BASE}},
            "town": {"unlocked_shops": []}}


def assign(module, obs, forced, tasks=None):
    module._ROUTE_MEMORY.clear()
    farm, private = obs["farms"][0], obs["private"]
    if tasks is None:
        tasks, _ = module.build_tasks(obs, farm, private)
    zones = [{(4, 3)} for _ in private["inventories"]]
    return module.assign(obs, farm, private, tasks, zones, forced)


def execute(obs, actions):
    obs = copy.deepcopy(obs)
    for idx, action in enumerate(actions):
        engine._apply_unit_action(obs["farms"][0], obs["private"], idx, action,
                                  10, obs["day"], 24)
    return obs


def item_total(obs, item):
    return sum(inv.get(item, 0) for inv in obs["private"]["inventories"])


class ServiceReservationTests(unittest.TestCase):
    def test_live_agent_harvest_trigger_frees_a_worker_for_fertilizer(self):
        obs = observation(n_units=7)
        baseline._ROUTE_MEMORY.clear()
        candidate._ROUTE_MEMORY.clear()
        before, after = baseline.agent(copy.deepcopy(obs)), candidate.agent(copy.deepcopy(obs))
        before_actions = [before["farmer"], *before["hands"]]
        after_actions = [after["farmer"], *after["hands"]]
        self.assertEqual(2, before_actions.count(["HARVEST"]))
        self.assertEqual(1, after_actions.count(["HARVEST"]))
        self.assertEqual(1, after_actions.count(["COLLECT_FERTILIZER"]))
        realized = execute(obs, after_actions)
        self.assertEqual(3, item_total(realized, "MILK"))
        self.assertEqual(1, item_total(realized, "FERTILIZER"))

    def test_live_agent_fertilizer_trigger_eliminates_duplicate(self):
        obs = observation(n_units=7, yield_units=0)
        baseline._ROUTE_MEMORY.clear()
        candidate._ROUTE_MEMORY.clear()
        before, after = baseline.agent(copy.deepcopy(obs)), candidate.agent(copy.deepcopy(obs))
        self.assertEqual(2, [before["farmer"], *before["hands"]].count(["COLLECT_FERTILIZER"]))
        actions = [after["farmer"], *after["hands"]]
        self.assertEqual(1, actions.count(["COLLECT_FERTILIZER"]))
        self.assertEqual(1, item_total(execute(obs, actions), "FERTILIZER"))

    def test_distinct_services_execute_in_either_unit_order(self):
        for forced_idx in (0, 1):
            for forced_op in ("HARVEST", "COLLECT_FERTILIZER"):
                with self.subTest(forced_idx=forced_idx, forced_op=forced_op):
                    obs = observation()
                    actions = assign(candidate, obs, {forced_idx: [forced_op]})
                    self.assertCountEqual([["HARVEST"], ["COLLECT_FERTILIZER"]], actions)
                    realized = execute(obs, actions)
                    self.assertEqual(3, item_total(realized, "MILK"))
                    self.assertEqual(1, item_total(realized, "FERTILIZER"))

    def test_feeding_preserves_independent_harvest_in_either_order(self):
        for forced_idx in (0, 1):
            with self.subTest(forced_idx=forced_idx):
                obs = observation(fertilizer=False)
                obs["farms"][0]["tiles"][3][4]["fed_today"] = False
                obs["private"]["inventories"][forced_idx] = {"WHEAT": 1}
                actions = assign(candidate, obs, {forced_idx: ["FEED"]})
                self.assertCountEqual([["HARVEST"], ["FEED"]], actions)
                realized = execute(obs, actions)
                self.assertTrue(realized["farms"][0]["tiles"][3][4]["fed_today"])
                self.assertEqual(3, item_total(realized, "MILK"))
                self.assertEqual(0, item_total(realized, "WHEAT"))

    def test_care_preserves_independent_fertilizer_collection(self):
        obs = observation(yield_units=0)
        obs["farms"][0]["tiles"][3][4]["cared_today"] = False
        actions = assign(candidate, obs, {1: ["CARE"]})
        realized = execute(obs, actions)
        self.assertTrue(realized["farms"][0]["tiles"][3][4]["cared_today"])
        self.assertEqual(1, item_total(realized, "FERTILIZER"))

    def test_forced_movement_does_not_reserve_destination(self):
        obs = observation(fertilizer=False)
        obs["farms"][0]["hands"][0] = [3, 3]
        actions = assign(candidate, obs, {1: ["EAST"]})
        self.assertEqual([["HARVEST"], ["EAST"]], actions)
        self.assertEqual(3, item_total(execute(obs, actions), "MILK"))

    def test_invalid_forced_unit_cannot_reserve_a_task(self):
        obs = observation(fertilizer=False)
        actions = assign(candidate, obs, {-1: ["HARVEST"], 2: ["HARVEST"]})
        self.assertEqual(1, actions.count(["HARVEST"]))

    def test_delivery_override_releases_replaced_forced_service(self):
        obs = observation(fertilizer=False)
        obs.update(day=29, hour=15)
        obs["private"]["inventories"][1] = {"MILK": 2}
        actions = assign(candidate, obs, {1: ["HARVEST"]})
        self.assertEqual([["HARVEST"], ["SOUTH"]], actions)

    def test_no_forced_service_preserves_baseline_actions(self):
        for forced in (None, {1: ["PASS"]}, {1: ["NORTH"]}):
            with self.subTest(forced=forced):
                obs = observation()
                self.assertEqual(assign(baseline, obs, forced), assign(candidate, obs, forced))


if __name__ == "__main__":
    unittest.main()
