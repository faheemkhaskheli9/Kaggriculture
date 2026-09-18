"""ENABLE_FERT_WATER_PRIORITY: water a fertilized ongoing plant first on the
day its tick resolves (the fertilizer +1 is only paid on a watered day)."""
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


def plant(crop, planted_day, fert_until=-1, yield_units=0, watered=False, cu=0):
    return {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
            "fertilized_until_day": fert_until, "yield_units": yield_units,
            "consecutive_unwatered": cu, "watered_today": watered,
            "max_lifespan_step": -1}


def observation(day=12, hour=5):
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


def water_priority(obs, pos):
    tasks, _ = main.build_tasks(obs, obs["farms"][0], obs["private"])
    pri = [t[0] for t in tasks if t[1] == pos and t[2] == ["WATER"]]
    return pri[0] if pri else None


class FertWaterPriorityTests(unittest.TestCase):
    def setUp(self):
        self._flags = (main.ENABLE_FERT_WATER_PRIORITY, main.ENABLE_CROP_FERTILIZE)
        main.ENABLE_FERT_WATER_PRIORITY = True
        main.ENABLE_CROP_FERTILIZE = True

    def tearDown(self):
        main.ENABLE_FERT_WATER_PRIORITY, main.ENABLE_CROP_FERTILIZE = self._flags

    def test_tick_tonight_matches_engine_refresh(self):
        # An ongoing plant gains a unit at tonight's refresh exactly on the
        # ages the helper reports (planted day 0, watered, unfertilized).
        for crop in ("STRAWBERRY", "TOMATO"):
            for age in range(0, 22):
                f = farm()
                t = engine._new_plant(crop, 0, 24)
                t["watered_today"] = True
                t["yield_units"] = 0
                f["tiles"][2][2] = t
                engine._daily_refresh_plants(f, age, 24)
                gained = f["tiles"][2][2].get("yield_units", 0) > 0
                self.assertEqual(gained, main._fert_tick_tonight(crop, age),
                                 f"{crop} age {age}")

    def test_fertilized_tick_eve_water_is_promoted(self):
        obs = observation(day=15)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 6, fert_until=15)  # age 9 -> tick 10 tonight
        self.assertEqual(water_priority(obs, (3, 3)), main.FERT_WATER_PRIORITY)

    def test_off_path_keeps_comfort_water(self):
        main.ENABLE_FERT_WATER_PRIORITY = False
        obs = observation(day=15)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 6, fert_until=15)
        self.assertEqual(water_priority(obs, (3, 3)), 2600)
        obs["hour"] = 21
        self.assertEqual(water_priority(obs, (3, 3)), 3000)

    def test_no_tick_tonight_stays_comfort(self):
        obs = observation(day=15)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 5, fert_until=15)  # age 10 -> tick 11: none
        self.assertEqual(water_priority(obs, (3, 3)), 2600)

    def test_unfertilized_tick_eve_stays_comfort(self):
        obs = observation(day=15)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 6, fert_until=14)  # expired yesterday
        self.assertEqual(water_priority(obs, (3, 3)), 2600)

    def test_survival_water_still_dominates(self):
        obs = observation(day=15, hour=6)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 6, fert_until=15, cu=1)
        self.assertEqual(water_priority(obs, (3, 3)), 10000 + 5 * 6)

    def test_already_watered_emits_nothing(self):
        obs = observation(day=15)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 6, fert_until=15, watered=True)
        self.assertIsNone(water_priority(obs, (3, 3)))

    def test_tomato_tick_eve_and_one_time_crops(self):
        obs = observation(day=15)
        obs["farms"][0]["tiles"][3][3] = plant("TOMATO", 8, fert_until=16)     # age 7 -> tick 8
        obs["farms"][0]["tiles"][4][4] = plant("WHEAT", 14, fert_until=16)     # one-time: unaffected
        self.assertEqual(water_priority(obs, (3, 3)), main.FERT_WATER_PRIORITY)
        self.assertEqual(water_priority(obs, (4, 4)), 2600)

    def test_priority_sits_between_routine_harvest_and_animal_harvest(self):
        self.assertGreater(main.FERT_WATER_PRIORITY, 3200)   # routine ongoing harvest
        self.assertLess(main.FERT_WATER_PRIORITY, 4800)      # animal-produce harvest


if __name__ == "__main__":
    unittest.main()
