"""ENABLE_SPENT_NO_WATER: an ongoing plant that has banked its final yield
tick (engine sets max_lifespan_step) gets no WATER task -- only its HARVEST."""
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


def plant(crop, planted_day, mls=-1, yield_units=0, watered=False, cu=0):
    return {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
            "fertilized_until_day": -1, "yield_units": yield_units,
            "consecutive_unwatered": cu, "watered_today": watered,
            "max_lifespan_step": mls}


def observation(day=26, hour=5):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(), farm()],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }


def tasks_at(obs, pos):
    tasks, _ = main.build_tasks(obs, obs["farms"][0], obs["private"])
    return {tuple(t[2]): t[0] for t in tasks if t[1] == pos}


def grow_to_final_tick(crop):
    """Water + harvest a plant every day until the engine stamps its
    max_lifespan_step; returns (farm, day_of_stamp, units_gained_after)."""
    f = farm()
    t = engine._new_plant(crop, 0, 24)
    f["tiles"][2][2] = t
    stamp_day = None
    gained_after = 0
    for day in range(0, 29):
        tile = f["tiles"][2][2]
        tile["watered_today"] = True
        before = tile["yield_units"]
        engine._daily_refresh_plants(f, day, 24)
        tile = f["tiles"][2][2]
        if stamp_day is not None:
            gained_after += tile["yield_units"] - before
        if stamp_day is None and tile["max_lifespan_step"] >= 0:
            stamp_day = day
    return f, stamp_day, gained_after


class SpentNoWaterTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_SPENT_NO_WATER
        main.ENABLE_SPENT_NO_WATER = True

    def tearDown(self):
        main.ENABLE_SPENT_NO_WATER = self._flag

    # ---- engine facts the flag relies on ----
    def test_engine_no_tick_after_stamp(self):
        for crop in ("STRAWBERRY", "TOMATO"):
            f, stamp_day, gained_after = grow_to_final_tick(crop)
            self.assertIsNotNone(stamp_day, crop)
            self.assertEqual(gained_after, 0, crop)
            self.assertEqual(f["tiles"][2][2]["max_lifespan_step"],
                             (stamp_day + 2) * 24, crop)

    def test_engine_spent_plant_is_weed_by_decay_day_watered_or_not(self):
        # watered + harvested: WEED at the first decay step
        f, stamp_day, _ = grow_to_final_tick("STRAWBERRY")
        mls = f["tiles"][2][2]["max_lifespan_step"]
        f["tiles"][2][2]["yield_units"] = 0
        f["tiles"][2][2]["watered_today"] = True
        engine._daily_refresh_plants(f, stamp_day + 1, 24)
        self.assertEqual(f["tiles"][2][2]["kind"], "PLANT")
        engine._decay_plants(f, mls)
        self.assertEqual(f["tiles"][2][2]["kind"], "WEED")
        # unwatered twice, units still on it: WEED at the day boundary
        f2, stamp_day2, _ = grow_to_final_tick("STRAWBERRY")
        f2["tiles"][2][2]["consecutive_unwatered"] = 1
        f2["tiles"][2][2]["watered_today"] = False
        engine._daily_refresh_plants(f2, stamp_day2 + 1, 24)
        self.assertEqual(f2["tiles"][2][2]["kind"], "WEED")

    # ---- task emission ----
    def test_spent_plant_gets_harvest_not_survival_water(self):
        obs = observation(day=26, hour=5)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 10, mls=27 * 24,
                                               yield_units=3, cu=1)
        ops = tasks_at(obs, (2, 2))
        self.assertNotIn(("WATER",), ops)
        self.assertEqual(ops.get(("HARVEST",)), 5000)

    def test_spent_empty_plant_gets_nothing(self):
        obs = observation(day=26, hour=5)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 10, mls=27 * 24,
                                               yield_units=0, cu=0)
        self.assertEqual(tasks_at(obs, (2, 2)), {})

    def test_off_path_keeps_survival_water(self):
        main.ENABLE_SPENT_NO_WATER = False
        obs = observation(day=26, hour=5)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 10, mls=27 * 24,
                                               yield_units=3, cu=1)
        ops = tasks_at(obs, (2, 2))
        self.assertEqual(ops.get(("WATER",)), 10000 + 5 * 5)
        self.assertEqual(ops.get(("HARVEST",)), 5000)

    def test_unspent_ongoing_plant_unchanged(self):
        obs = observation(day=14, hour=5)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 2, mls=-1,
                                               yield_units=1, cu=1)
        ops = tasks_at(obs, (2, 2))
        self.assertEqual(ops.get(("WATER",)), 10000 + 5 * 5)

    def test_one_time_crop_unchanged(self):
        # one-time crops carry max_lifespan_step from planting; not "spent".
        obs = observation(day=3, hour=5)
        obs["farms"][0]["tiles"][2][2] = plant("WHEAT", 1, mls=(1 + 4 + 1) * 24,
                                               yield_units=0, cu=1)
        ops = tasks_at(obs, (2, 2))
        self.assertEqual(ops.get(("WATER",)), 10000 + 5 * 5)

    def test_tomato_spent_same(self):
        obs = observation(day=20, hour=21)
        obs["farms"][0]["tiles"][2][2] = plant("TOMATO", 8, mls=21 * 24,
                                               yield_units=2, cu=0)
        ops = tasks_at(obs, (2, 2))
        self.assertNotIn(("WATER",), ops)
        self.assertEqual(ops.get(("HARVEST",)), 5000)

    def test_helper_requires_ongoing(self):
        self.assertTrue(main._spent_plant({"max_lifespan_step": 0}, True))
        self.assertFalse(main._spent_plant({"max_lifespan_step": 0}, False))
        self.assertFalse(main._spent_plant({"max_lifespan_step": -1}, True))
        self.assertFalse(main._spent_plant({}, True))


if __name__ == "__main__":
    unittest.main()
