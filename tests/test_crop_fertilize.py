"""ENABLE_CROP_FERTILIZE (Lever H3): value-gated FERTILIZE on ongoing crops."""
import copy
import unittest

from kaggle_environments.envs.kaggriculture import kaggriculture as engine

import main


def farm(hands=()):
    return {
        "money": 5000,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [list(h) for h in hands],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def plant(crop, planted_day, fert_until=-1, yield_units=0):
    return {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
            "fertilized_until_day": fert_until, "yield_units": yield_units,
            "consecutive_unwatered": 0, "watered_today": True}


def observation(day=12, hour=5, shed=None, inventories=None, hands=()):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(hands=hands), farm()],
        "private": {"shed": dict(shed or {}), "seeds": {},
                    "inventories": [dict(i) for i in (inventories or [{}])]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }


def fert_tasks(obs):
    tasks, _ = main.build_tasks(obs, obs["farms"][0], obs["private"])
    return sorted(t[1] for t in tasks if t[2] == ["FERTILIZE"])


class CropFertilizeTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_CROP_FERTILIZE
        main.ENABLE_CROP_FERTILIZE = True

    def tearDown(self):
        main.ENABLE_CROP_FERTILIZE = self._flag

    def test_tick_coverage_matches_engine_schedule(self):
        self.assertEqual(main._fert_ticks_covered("TOMATO", 7), 3)     # ticks 8, 9, 10
        self.assertEqual(main._fert_ticks_covered("TOMATO", 10), 1)    # tick 11
        self.assertEqual(main._fert_ticks_covered("STRAWBERRY", 9), 2)  # ticks 10, 12
        self.assertEqual(main._fert_ticks_covered("STRAWBERRY", 13), 2)  # ticks 14, 16
        self.assertEqual(main._fert_ticks_covered("STRAWBERRY", 17), 0)

    def test_task_emitted_only_when_worth_it(self):
        obs = observation(day=12)
        tiles = obs["farms"][0]["tiles"]
        tiles[0][0] = plant("STRAWBERRY", 3)            # age 9 -> 2 ticks, wanted
        tiles[0][1] = plant("STRAWBERRY", 3, fert_until=12)   # already fertilized
        tiles[0][2] = plant("WHEAT", 10)                # one-time crop: never
        tiles[0][3] = plant("TOMATO", 2)                # age 10 -> 1 tick x $60 < 1.5 x $100
        tiles[0][4] = plant("TOMATO", 5)                # age 7 -> 3 ticks, wanted
        self.assertEqual(fert_tasks(obs), [(0, 0), (4, 0)])
        obs["day"] = 28
        self.assertEqual(fert_tasks(obs), [])

    def test_off_flag_emits_nothing(self):
        main.ENABLE_CROP_FERTILIZE = False
        obs = observation(day=12)
        obs["farms"][0]["tiles"][0][0] = plant("STRAWBERRY", 3)
        self.assertEqual(fert_tasks(obs), [])

    def test_assign_requires_fertilizer_in_hand_and_stocks_up_at_dawn(self):
        obs = observation(day=12, hour=5, hands=[(0, 0)], inventories=[{}, {}])
        obs["farms"][0]["tiles"][0][0] = plant("STRAWBERRY", 3)
        me = obs["farms"][0]
        zones = [set(), {(0, 0)}]
        tasks = [(main.CROP_FERT_PRIORITY, (0, 0), ["FERTILIZE"])]
        self.assertNotEqual(main.assign(obs, me, obs["private"], tasks, zones, {})[1], ["FERTILIZE"])
        obs["private"]["inventories"][1] = {"FERTILIZER": 1}
        self.assertEqual(main.assign(obs, me, obs["private"], tasks, zones, {})[1], ["FERTILIZE"])
        for hour in (0, 1):     # farmer spawns at hour 0, the day's hires at hour 1
            dawn = observation(day=12, hour=hour, shed={"FERTILIZER": 5}, hands=[(5, 4)],
                               inventories=[{}, {}])
            self.assertEqual(main.assign(dawn, dawn["farms"][0], dawn["private"], tasks, zones, {})[1],
                             ["PICKUP", "FERTILIZER", 1])
        noon = observation(day=12, hour=2, shed={"FERTILIZER": 5}, hands=[(5, 4)], inventories=[{}, {}])
        self.assertNotEqual(main.assign(noon, noon["farms"][0], noon["private"], tasks, zones, {})[1],
                            ["PICKUP", "FERTILIZER", 1])

    def test_sell_holds_back_two_days_of_demand(self):
        obs = observation(day=12, hour=5, shed={"FERTILIZER": 6})
        tiles = obs["farms"][0]["tiles"]
        tiles[0][0] = plant("STRAWBERRY", 3)     # wanted today
        tiles[0][1] = plant("TOMATO", 6)         # age 6 today, 7 tomorrow -> wanted tomorrow
        orders = main.market_orders(obs, obs["farms"][0], obs["private"], {}, 1)
        fert = [o for o in orders if o[0] == "SELL" and o[1] == "FERTILIZER"]
        self.assertEqual(fert[0][2], 4)

    def test_engine_pays_two_units_on_a_fertilized_tick(self):
        cfg = {"turnsPerDay": 24}
        tile = engine._new_plant("STRAWBERRY", 0, 24) if hasattr(engine, "_new_plant") else None
        if tile is None:
            self.skipTest("engine helper not exposed")
        tile["planted_day"] = 0
        tile["watered_today"] = True
        tile["fertilized_until_day"] = 9
        farm_state = {"tiles": [[tile]]}
        engine._daily_refresh_plants(farm_state, 9, 24)
        self.assertEqual(tile["yield_units"], 2)


if __name__ == "__main__":
    unittest.main()
