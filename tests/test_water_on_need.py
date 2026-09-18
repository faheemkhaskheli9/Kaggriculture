"""ENABLE_WATER_ON_NEED: a plant at consecutive_unwatered == 0 gets a WATER
task only when the water changes engine state (fertilizer +1 on tonight's
tick, or a growth unit inside a one-time crop's yield window)."""
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


def plant(crop, planted_day, mls=-1, yield_units=0, watered=False, cu=0,
          fert_until=-1):
    return {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
            "fertilized_until_day": fert_until, "yield_units": yield_units,
            "consecutive_unwatered": cu, "watered_today": watered,
            "max_lifespan_step": mls}


def observation(day=20, hour=5):
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


class Flagged(unittest.TestCase):
    def setUp(self):
        self._saved = main.ENABLE_WATER_ON_NEED

    def tearDown(self):
        main.ENABLE_WATER_ON_NEED = self._saved

    def obs_with(self, tile, day=20, hour=5):
        obs = observation(day, hour)
        obs["farms"][0]["tiles"][2][3] = tile
        return obs

    def test_off_is_incumbent_comfort_water(self):
        main.ENABLE_WATER_ON_NEED = False
        t = plant("STRAWBERRY", 9, yield_units=1)          # age 11, tick at 12
        got = tasks_at(self.obs_with(t), (3, 2))
        self.assertEqual(got.get(("WATER",)), 2600)
        self.assertIn(("HARVEST",), got)

    def test_on_skips_water_when_nothing_to_gain(self):
        main.ENABLE_WATER_ON_NEED = True
        t = plant("STRAWBERRY", 9, yield_units=1)          # cu 0, unfertilized
        got = tasks_at(self.obs_with(t), (3, 2))
        self.assertNotIn(("WATER",), got)
        self.assertIn(("HARVEST",), got)                   # harvest untouched

    def test_on_keeps_survival_water(self):
        main.ENABLE_WATER_ON_NEED = True
        t = plant("STRAWBERRY", 9, cu=1)
        got = tasks_at(self.obs_with(t, hour=7), (3, 2))
        self.assertEqual(got.get(("WATER",)), 10000 + 5 * 7)

    def test_on_waters_fertilized_plant_on_tick_night(self):
        main.ENABLE_WATER_ON_NEED = True
        t = plant("STRAWBERRY", 9, fert_until=25)          # age 11 -> tick 12
        self.assertTrue(main._fert_tick_tonight("STRAWBERRY", 11))
        got = tasks_at(self.obs_with(t), (3, 2))
        self.assertEqual(got.get(("WATER",)), 2600)
        got = tasks_at(self.obs_with(t, hour=21), (3, 2))
        self.assertEqual(got.get(("WATER",)), 3000)        # P1w evening tier kept

    def test_on_skips_fertilized_plant_off_tick_night(self):
        main.ENABLE_WATER_ON_NEED = True
        t = plant("STRAWBERRY", 10, fert_until=25)         # age 10 -> no tick at 11
        self.assertFalse(main._fert_tick_tonight("STRAWBERRY", 10))
        got = tasks_at(self.obs_with(t), (3, 2))
        self.assertNotIn(("WATER",), got)

    def test_on_one_time_crop_window_only(self):
        main.ENABLE_WATER_ON_NEED = True
        young = plant("WHEAT", 19, yield_units=1)          # age 1: before window
        self.assertNotIn(("WATER",), tasks_at(self.obs_with(young), (3, 2)))
        grown = plant("WHEAT", 18, yield_units=1)          # age 2: in window
        self.assertEqual(tasks_at(self.obs_with(grown), (3, 2)).get(("WATER",)), 6200 + 2)

    def test_on_alternate_day_water_matches_engine_yield(self):
        """Engine parity: watering only on cu == 1 days (what the flag leaves
        to the survival tier) never kills the plant and banks the same
        units as watering every day."""
        def run(daily):
            f = farm()
            f["tiles"][2][2] = engine._new_plant("STRAWBERRY", 0, 24)
            banked = 0
            for day in range(0, 28):
                t = f["tiles"][2][2]
                if t.get("kind") != "PLANT":
                    return None
                if daily or t["consecutive_unwatered"] >= 1:
                    t["watered_today"] = True
                engine._daily_refresh_plants(f, day, 24)
                t = f["tiles"][2][2]
                if t.get("kind") == "PLANT":
                    banked += t["yield_units"]; t["yield_units"] = 0
            return banked
        self.assertEqual(run(True), 4)
        self.assertEqual(run(False), 4)

    def test_on_fertilized_tick_night_water_keeps_bonus(self):
        """Engine parity: a fertilized plant watered only on cu == 1 days and
        tick nights banks the same +2 ticks as one watered daily."""
        def run(daily):
            f = farm()
            f["tiles"][2][2] = engine._new_plant("STRAWBERRY", 0, 24)
            f["tiles"][2][2]["fertilized_until_day"] = 30
            banked = 0
            for day in range(0, 28):
                t = f["tiles"][2][2]
                if t.get("kind") != "PLANT":
                    return None
                age = day - t["planted_day"]
                if daily or t["consecutive_unwatered"] >= 1 or main._water_pays(
                        t, "STRAWBERRY", age, day, True, 10):
                    t["watered_today"] = True
                engine._daily_refresh_plants(f, day, 24)
                t = f["tiles"][2][2]
                if t.get("kind") == "PLANT":
                    banked += t["yield_units"]; t["yield_units"] = 0
            return banked
        self.assertEqual(run(True), 8)
        self.assertEqual(run(False), 8)


if __name__ == "__main__":
    unittest.main()
