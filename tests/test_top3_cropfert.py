"""Engine-backed checks for the isolated crop-fertilizer experiment."""
import copy
import importlib.util
from pathlib import Path
import unittest

from kaggle_environments.envs.kaggriculture import kaggriculture as engine

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = load("cropfert_candidate", "experiments/candidate_top3_cropfert.py")
baseline = load("cropfert_baseline", "research/baseline_main_20260912.py")


def observation(crop="WHEAT", day=8, planted=6):
    farm = engine._new_farm(10, 0)
    farm["tiles"][4][4] = engine._new_plant(crop, planted, 24)
    private = engine._new_private()
    private["inventories"][0] = {"FERTILIZER": 1}
    market = engine._new_market()
    market["inventory"]["FERTILIZER"] = 10500
    engine._refresh_prices(market)
    return {"player": 0, "day": day, "hour": 4, "step": day * 24 + 4,
            "farms": [farm, copy.deepcopy(farm)], "private": private,
            "market": market, "town": {"unlocked_shops": []}}


def apply(obs, action):
    engine._apply_unit_action(obs["farms"][0], obs["private"], 0, action,
                              10, obs["day"], 24)


class CropFertilizerTests(unittest.TestCase):
    def setUp(self):
        candidate.ENABLE_SELECTIVE_CROP_FERTILIZER = True
        candidate._ROUTE_MEMORY.clear()
        baseline._ROUTE_MEMORY.clear()

    def test_live_agent_fertilizes_before_water_and_gains_one_wheat(self):
        obs = observation()
        before = copy.deepcopy(obs)
        self.assertEqual(["FERTILIZE"], candidate.agent(obs)["farmer"])
        apply(obs, ["FERTILIZE"])
        self.assertEqual(["WATER"], candidate.agent(obs)["farmer"])
        apply(obs, ["WATER"])
        apply(before, ["WATER"])
        apply(obs, ["HARVEST"])
        apply(before, ["HARVEST"])
        self.assertEqual(before["private"]["inventories"][0]["WHEAT"] + 1,
                         obs["private"]["inventories"][0]["WHEAT"])
        self.assertNotIn("FERTILIZER", obs["private"]["inventories"][0])

    def test_one_time_rejects_outside_window_watered_active_and_full(self):
        for fields in ({"planted_day": 7}, {"planted_day": 3},
                       {"watered_today": True}, {"fertilized_until_day": 8},
                       {"yield_units": 5}):
            obs = observation()
            tile = obs["farms"][0]["tiles"][4][4]
            tile.update(fields)
            with self.subTest(fields=fields):
                self.assertEqual(0, candidate._cropfert_profit(obs, tile))

    def test_strawberry_bonus_occurs_on_first_actual_tick(self):
        obs = observation("STRAWBERRY", day=9, planted=0)
        before = copy.deepcopy(obs)
        tile = obs["farms"][0]["tiles"][4][4]
        self.assertGreater(candidate._cropfert_profit(obs, tile), 0)
        apply(obs, ["FERTILIZE"])
        apply(obs, ["WATER"])
        apply(before, ["WATER"])
        engine._daily_refresh_plants(obs["farms"][0], 9, 24)
        engine._daily_refresh_plants(before["farms"][0], 9, 24)
        self.assertEqual(2, tile["yield_units"])
        self.assertEqual(1, before["farms"][0]["tiles"][4][4]["yield_units"])

    def test_ongoing_uses_tick_count_not_harvested_lifetime_units(self):
        obs = observation("STRAWBERRY", day=15, planted=0)
        tile = obs["farms"][0]["tiles"][4][4]
        self.assertGreater(candidate._cropfert_profit(obs, tile), 0)
        for day in (10, 17):  # no production tonight; then beyond fourth tick
            obs["day"] = day
            self.assertEqual(0, candidate._cropfert_profit(obs, tile))

    def test_cost_and_terminal_guards(self):
        obs = observation()
        tile = obs["farms"][0]["tiles"][4][4]
        obs["market"]["prices"]["FERTILIZER"] = 100
        self.assertEqual(0, candidate._cropfert_profit(obs, tile))
        obs["market"]["prices"]["FERTILIZER"] = 1
        obs["hour"] = 21
        self.assertEqual(0, candidate._cropfert_profit(obs, tile))
        obs["hour"], obs["day"] = 0, 29
        self.assertEqual(0, candidate._cropfert_profit(obs, tile))

    def test_pickups_share_existing_shed_stock(self):
        obs = observation()
        farm, private = obs["farms"][0], obs["private"]
        farm["hands"] = [[4, 4], [4, 4]]
        private["inventories"] = [{}, {}, {}]
        private["shed"]["FERTILIZER"] = 1
        obs["hour"] = 1
        tasks, _ = candidate.build_tasks(obs, farm, private)
        actions = candidate.assign(obs, farm, private, tasks, [{(4, 4)}] * 3)
        self.assertEqual(1, sum(a[-1] for a in actions if a[:2] == ["PICKUP", "FERTILIZER"]))

    def test_same_tile_harvest_is_not_assigned_during_fertilize(self):
        obs = observation()
        farm, private = obs["farms"][0], obs["private"]
        farm["hands"] = [[4, 4]]
        private["inventories"].append({})
        tasks, _ = candidate.build_tasks(obs, farm, private)
        actions = candidate.assign(obs, farm, private, tasks, [{(4, 4)}] * 2)
        self.assertEqual(["FERTILIZE"], actions[0])
        self.assertNotIn(actions[1], [["HARVEST"], ["WATER"]])

    def test_disabled_and_final_day_preserve_baseline(self):
        for enabled, day in ((False, 8), (True, 29)):
            obs = observation(day=day)
            candidate.ENABLE_SELECTIVE_CROP_FERTILIZER = enabled
            self.assertEqual(baseline.agent(copy.deepcopy(obs)),
                             candidate.agent(copy.deepcopy(obs)))


if __name__ == "__main__":
    unittest.main()
