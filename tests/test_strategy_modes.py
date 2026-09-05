import copy
import unittest

import main


def empty_farm(money=3000):
    return {
        "money": money,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [0, 0],
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def observation(day=0, hour=0):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [empty_farm(), empty_farm()],
        "private": {
            "shed": {},
            "seeds": {},
            "inventories": [{}],
        },
        "market": {
            "inventory": {item: 10000 for item in main.BASE},
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": []},
    }


class StrategyIntentTests(unittest.TestCase):
    def test_default_mode_is_enabled_adaptive_policy(self):
        intent = main.strategy_intent()
        self.assertEqual("ADAPTIVE_ECONOMY", intent["mode"])
        self.assertTrue(intent["config"]["ENABLED"])

    def test_invalid_and_disabled_modes_fail_closed(self):
        for mode in ("UNKNOWN", "FRONTIER_SCHEDULE", "MULTI_ROUTE"):
            with self.subTest(mode=mode):
                self.assertEqual("ADAPTIVE_ECONOMY", main.strategy_intent(mode)["mode"])

    def test_livestock_limits_resolve_from_its_config(self):
        intent = main.strategy_intent("LIVESTOCK_ENGINE")
        self.assertEqual("LIVESTOCK_ENGINE", intent["mode"])
        self.assertEqual(2, intent["max_quadrants"])
        self.assertEqual(11, intent["max_hands"])
        self.assertEqual(3, intent["feed_stock_days"])

    def test_all_mode_configs_have_boolean_enabled_toggle(self):
        for mode in main.SUPPORTED_STRATEGY_MODES:
            with self.subTest(mode=mode):
                self.assertIsInstance(main.STRATEGY_CONFIG[mode].get("ENABLED"), bool)

    def test_numeric_operating_limits_are_positive(self):
        for mode in ("ADAPTIVE_ECONOMY", "LIVESTOCK_ENGINE", "ANTI_META"):
            intent = main.strategy_intent(mode)
            with self.subTest(mode=mode):
                self.assertGreaterEqual(intent["max_quadrants"], 1)
                self.assertLessEqual(intent["max_quadrants"], 4)
                self.assertGreaterEqual(intent["max_hands"], 0)
                self.assertGreaterEqual(intent["feed_stock_days"], 1)


class LivestockPolicyTests(unittest.TestCase):
    def setUp(self):
        self.intent = main.strategy_intent("LIVESTOCK_ENGINE")

    def test_herd_target_is_staged_until_second_quadrant(self):
        obs = observation(day=5)
        self.assertEqual({"COW": 4},
                         main.animal_targets(obs, obs["farms"][0], self.intent))

        obs["farms"][0]["unlocked_quadrants"].append("NE")
        actual = main.animal_targets(obs, obs["farms"][0], self.intent)
        expected = {animal: qty for animal, qty in self.intent["config"]["HERD_TARGET"].items()
                    if qty > 0}
        self.assertEqual(expected, actual)

    def test_crop_picker_honors_absolute_targets(self):
        obs = observation(day=5)
        picks = main.choose_crops(obs, obs["farms"][0], obs["private"], {}, 30, self.intent)
        self.assertEqual(14, picks.count("WHEAT"))
        self.assertEqual(16, picks.count("STRAWBERRY"))

    def test_pre_strawberry_bootstrap_is_wheat_only(self):
        obs = observation(day=2)
        picks = main.choose_crops(obs, obs["farms"][0], obs["private"], {}, 8, self.intent)
        self.assertEqual(["WHEAT"] * 8, picks)


class AntiMetaPolicyTests(unittest.TestCase):
    def setUp(self):
        self.intent = main.strategy_intent("ANTI_META")

    def test_mode_is_opt_in_and_preserves_adaptive_operating_limits(self):
        self.assertEqual("ANTI_META", self.intent["mode"])
        self.assertEqual(4, self.intent["max_quadrants"])
        self.assertEqual(13, self.intent["max_hands"])

    def test_high_live_wool_value_shifts_target_to_sheep(self):
        obs = observation(day=5)
        obs["market"]["prices"]["WOOL"] = 1200
        targets = main.animal_targets(obs, obs["farms"][0], self.intent)
        self.assertGreater(targets.get("SHEEP", 0), targets.get("COW", 0))

    def test_visible_species_crowding_reduces_that_species(self):
        obs = observation(day=5)
        uncrowded = main.animal_targets(obs, obs["farms"][0], self.intent)
        for x in range(5):
            obs["farms"][1]["tiles"][0][x] = {"kind": "PASTURE", "animal": "COW"}
        crowded = main.animal_targets(obs, obs["farms"][0], self.intent)
        self.assertLess(crowded.get("COW", 0), uncrowded.get("COW", 0))

class DispatcherSafetyTests(unittest.TestCase):
    def test_default_dispatch_matches_explicit_adaptive_entry(self):
        obs = observation()
        self.assertEqual(main._adaptive_economy_agent(copy.deepcopy(obs)),
                         main.agent(copy.deepcopy(obs)))

    def test_invalid_global_selection_falls_back_without_raising(self):
        obs = observation()
        original = main.STRATEGY_MODE
        try:
            main.STRATEGY_MODE = "NOT_A_MODE"
            self.assertEqual(main._adaptive_economy_agent(copy.deepcopy(obs)),
                             main.agent(copy.deepcopy(obs)))
        finally:
            main.STRATEGY_MODE = original


if __name__ == "__main__":
    unittest.main()
