"""v78 hunks: ENABLE_FERT_TICK_FIRST, ENABLE_SHEEP_OPENING, ENABLE_HERD_STEP_D6,
ENABLE_GOOSE_ON_NO_MILK. Each test pins one rule of the hunk; the OFF path is
checked to keep the incumbent behaviour."""
import unittest

import main


def farm(quadrants=("NW",), money=5000):
    return {
        "money": money,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": list(quadrants),
        "hires_today": 0,
    }


def plant(crop, planted_day, fert_until=-1, yield_units=0, watered=False, cu=0):
    return {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
            "fertilized_until_day": fert_until, "yield_units": yield_units,
            "consecutive_unwatered": cu, "watered_today": watered,
            "max_lifespan_step": -1}


def observation(day=12, hour=5, shops=(), quadrants=("NW",), money=5000):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(quadrants, money), farm()],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": list(shops)},
    }


FLAGS = ("ENABLE_FERT_TICK_FIRST", "ENABLE_SHEEP_OPENING", "ENABLE_HERD_STEP_D6",
         "ENABLE_GOOSE_ON_NO_MILK", "ENABLE_CROP_FERTILIZE", "ENABLE_WATER_ON_NEED",
         "ENABLE_FERT_WATER_PRIORITY")


class FlagCase(unittest.TestCase):
    def setUp(self):
        self._saved = {f: getattr(main, f) for f in FLAGS}
        main.ENABLE_CROP_FERTILIZE = True

    def tearDown(self):
        for f, v in self._saved.items():
            setattr(main, f, v)

    def tasks_at(self, obs, pos, op):
        tasks, _ = main.build_tasks(obs, obs["farms"][0], obs["private"])
        return [t[0] for t in tasks if t[1] == pos and t[2] == [op]]


class FertTickFirstTests(FlagCase):
    def test_fertilize_only_on_tick_eve(self):
        main.ENABLE_FERT_TICK_FIRST = True
        for age, expect in ((7, False), (8, False), (9, True), (10, False),
                            (11, True), (13, True), (15, True), (16, False)):
            obs = observation(day=20)
            # ladder-typical scarcity (STRAWBERRY ~204): the value gate
            # (covered ticks >= 1.5x the fertilizer price) passes for one tick.
            obs["market"]["inventory"]["STRAWBERRY"] = 9900
            obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 20 - age)
            got = self.tasks_at(obs, (2, 2), "FERTILIZE")
            self.assertEqual(bool(got), expect, f"age {age}")
            if got:
                self.assertEqual(got[0], main.FERT_TICK_FIRST_PRIORITY)

    def test_off_path_keeps_early_application_and_low_tier(self):
        main.ENABLE_FERT_TICK_FIRST = False
        obs = observation(day=20)
        obs["market"]["inventory"]["STRAWBERRY"] = 9900
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 20 - 8)
        self.assertEqual(self.tasks_at(obs, (2, 2), "FERTILIZE"), [main.CROP_FERT_PRIORITY])

    def test_covered_plant_is_not_refertilized(self):
        main.ENABLE_FERT_TICK_FIRST = True
        obs = observation(day=20)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 20 - 11, fert_until=20)
        self.assertEqual(self.tasks_at(obs, (2, 2), "FERTILIZE"), [])

    def test_fertilized_tick_night_water_outranks_survival_water(self):
        main.ENABLE_FERT_TICK_FIRST = True
        main.ENABLE_WATER_ON_NEED = True
        obs = observation(day=20, hour=5)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 20 - 9, fert_until=22)
        obs["farms"][0]["tiles"][3][3] = plant("STRAWBERRY", 20 - 4, cu=1)
        self.assertEqual(self.tasks_at(obs, (2, 2), "WATER"), [main.FERT_TICK_FIRST_WATER_PRIORITY])
        self.assertLess(self.tasks_at(obs, (3, 3), "WATER")[0], main.FERT_TICK_FIRST_WATER_PRIORITY)

    def test_overflow_harvest_is_urgent(self):
        main.ENABLE_FERT_TICK_FIRST = True
        obs = observation(day=20)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 20 - 11, fert_until=20, yield_units=3)
        self.assertEqual(self.tasks_at(obs, (2, 2), "HARVEST"), [main.FERT_TICK_FIRST_HARVEST_PRIORITY])

    def test_day_28_application_allowed(self):
        main.ENABLE_FERT_TICK_FIRST = True
        obs = observation(day=28)
        obs["farms"][0]["tiles"][2][2] = plant("STRAWBERRY", 28 - 13)
        self.assertTrue(self.tasks_at(obs, (2, 2), "FERTILIZE"))
        main.ENABLE_FERT_TICK_FIRST = False
        self.assertEqual(self.tasks_at(obs, (2, 2), "FERTILIZE"), [])

    def test_unexecutable_fertilize_does_not_hide_the_survival_water(self):
        # (f): nobody holds fertilizer -> the FERTILIZE task is dropped and the
        # plant's survival WATER is what the hand is sent to do.
        main.ENABLE_FERT_TICK_FIRST = True
        obs = observation(day=20, hour=5)
        me = obs["farms"][0]
        me["farmer"] = [2, 2]
        me["tiles"][2][2] = plant("STRAWBERRY", 20 - 9, cu=1)
        tasks, counts = main.build_tasks(obs, me, obs["private"])
        zones = main.make_zones(main.unlocked_cells(me), 1)
        acts = main.assign(obs, me, obs["private"], tasks, zones)
        self.assertEqual(acts[0], ["WATER"])

    def test_carrier_fertilizes_before_watering(self):
        main.ENABLE_FERT_TICK_FIRST = True
        obs = observation(day=20, hour=5)
        me = obs["farms"][0]
        me["farmer"] = [2, 2]
        me["tiles"][2][2] = plant("STRAWBERRY", 20 - 9, cu=1)
        obs["private"]["inventories"] = [{"FERTILIZER": 1}]
        tasks, counts = main.build_tasks(obs, me, obs["private"])
        zones = main.make_zones(main.unlocked_cells(me), 1)
        acts = main.assign(obs, me, obs["private"], tasks, zones)
        self.assertEqual(acts[0], ["FERTILIZE"])


class HerdTests(FlagCase):
    def test_sheep_opening_targets_on_one_quadrant(self):
        main.ENABLE_SHEEP_OPENING = True
        obs = observation(day=0, hour=0)
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(tgt, {"SHEEP": 2, "COW": 2})
        self.assertEqual(list(tgt)[0], "SHEEP")          # bought first

    def test_sheep_opening_off_keeps_three_cows(self):
        main.ENABLE_SHEEP_OPENING = False
        obs = observation(day=0, hour=0)
        self.assertEqual(main.animal_targets(obs, obs["farms"][0]), {"COW": 3})

    def test_sheep_opening_is_inert_after_quadrant_two(self):
        obs = observation(day=8, hour=0, quadrants=("NW", "NE"))
        main.ENABLE_SHEEP_OPENING = False
        off = main.animal_targets(obs, obs["farms"][0])
        main.ENABLE_SHEEP_OPENING = True
        self.assertEqual(main.animal_targets(obs, obs["farms"][0]), off)

    def test_goose_mix_only_without_a_milk_shop(self):
        def targets(shops):
            obs = observation(day=12, hour=0, shops=shops, quadrants=("NW", "NE", "SW"))
            for i in range(5):                       # opponent runs a herd
                obs["farms"][1]["tiles"][0][i] = {"kind": "PASTURE", "animal": "COW"}
            return main.animal_targets(obs, obs["farms"][0])
        main.ENABLE_GOOSE_ON_NO_MILK = True
        self.assertEqual(targets([]).get("GOOSE"), 5)
        self.assertEqual(targets(["PIZZA_SHOP"]).get("GOOSE"), 2)
        self.assertEqual(targets(["PIZZA_SHOP"]).get("COW"), 9)
        main.ENABLE_GOOSE_ON_NO_MILK = False
        self.assertEqual(targets(["PIZZA_SHOP"]).get("GOOSE"), 5)

    def _buys(self, flag, day, quadrants, money):
        main.ENABLE_HERD_STEP_D6 = flag
        obs = observation(day=day, hour=2, quadrants=quadrants, money=money)
        me = obs["farms"][0]
        for i in range(4):
            me["tiles"][4][i] = {"kind": "PASTURE", "animal": "COW", "fed_today": True}
        obs["private"]["shed"] = {"WHEAT": 40}
        orders = main.market_orders(obs, me, obs["private"], main.Counter(), 8)
        return [o for o in orders if o and o[0] == "BUY_ANIMAL"]

    def test_herd_step_buys_after_quadrant_two_on_thin_cash(self):
        self.assertEqual(self._buys(False, 7, ("NW", "NE"), 1100), [])
        self.assertTrue(self._buys(True, 7, ("NW", "NE"), 1100))

    def test_herd_step_needs_quadrant_two_and_its_window(self):
        self.assertEqual(self._buys(True, 7, ("NW",), 1100), [])
        self.assertEqual(self._buys(True, 12, ("NW", "NE"), 1100),
                         self._buys(False, 12, ("NW", "NE"), 1100))


if __name__ == "__main__":
    unittest.main()
