"""ENABLE_SHOP_DEMAND_VALUE (Lever S1): crop value bounded by what the town's shops can eat."""
import unittest
from collections import Counter

import main


def farm(crops=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    i = 0
    for crop, n in (crops or {}).items():
        for _ in range(n):
            tiles[i // 10][i % 10] = {"kind": "PLANT", "crop": crop}
            i += 1
    return {"money": 15000, "tiles": tiles, "farmer": [4, 4], "hands": [[4, 5]] * 10,
            "unlocked_quadrants": ["NW", "NE", "SW"], "hires_today": 0}


def observation(day, mine, opp, inv_delta, shops):
    inventory = {item: 10000 + inv_delta.get(item, 0) for item in main.BASE}
    return {
        "player": 0, "day": day, "hour": 1,
        "farms": [farm(mine), farm(opp)],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": inventory,
                   "prices": {item: main.price_at(item, inventory[item]) for item in main.BASE}},
        "town": {"unlocked_shops": list(shops)},
    }


def picks(obs, flag):
    saved = main.ENABLE_SHOP_DEMAND_VALUE
    main.ENABLE_SHOP_DEMAND_VALUE = flag
    try:
        me = obs["farms"][0]
        return Counter(main.choose_crops(obs, me, obs["private"], main.field_counts(me), 24))
    finally:
        main.ENABLE_SHOP_DEMAND_VALUE = saved


# `109533084` day 11 hour 1: shops BRUNCH/BAKERY/PET_CAFE (one strawberry
# shop), we held 27 STRAWBERRY, the opponent 31; STRAWBERRY inventory -45.
LOW = dict(day=11, mine={"STRAWBERRY": 27, "MELON": 1},
           opp={"WHEAT": 13, "STRAWBERRY": 31, "MELON": 12},
           inv_delta={"STRAWBERRY": -45, "WHEAT": -60, "TOMATO": -20, "MELON": 90},
           shops=["BRUNCH_SPOT", "BAKERY", "PET_CAFE"])
# `109355960` day 12: SMOOTHIE/BRUNCH/PET_CAFE/ICE_CREAM (three strawberry shops).
HIGH = dict(day=12, mine={"STRAWBERRY": 36, "MELON": 5},
            opp={"STRAWBERRY": 10, "WHEAT": 5, "MELON": 2},
            inv_delta={"STRAWBERRY": -90, "WHEAT": -80, "MELON": 60},
            shops=["SMOOTHIE_SHOP", "BRUNCH_SPOT", "PET_CAFE", "ICE_CREAM_SHOP"])


class ShopDrainTests(unittest.TestCase):
    def test_drain_counts_shops_future_draws_and_town_centre(self):
        obs = observation(12, {}, {}, {}, ["YARN_STORE", "YARN_STORE", "BRUNCH_SPOT"])
        d = main._shop_drain(obs, 12)
        # 4 draws left (days 15/18/21/24); single-product shops count double
        self.assertAlmostEqual(d["WOOL"], 2 * 12 + 4 * 1.5 + 1)
        self.assertAlmostEqual(d["STRAWBERRY"], 6 + 4 * 3.0 + 1)
        self.assertAlmostEqual(d["EGG"], 6 + 4 * 1.5 + 1)
        self.assertAlmostEqual(d["CARROT"], 0 + 4 * 2.25 + 1)
        self.assertEqual(d["FERTILIZER"], 0)

    def test_no_future_draws_after_day_24(self):
        obs = observation(25, {}, {}, {}, ["PIZZA_SHOP"])
        d = main._shop_drain(obs, 25)
        self.assertAlmostEqual(d["MILK"], 6 + 1)
        self.assertAlmostEqual(d["WOOL"], 1)

    def test_supply_rates(self):
        self.assertAlmostEqual(main._crop_supply_rate("STRAWBERRY", 10, 10, True), 0.5)
        self.assertAlmostEqual(main._crop_supply_rate("TOMATO", 8, 8, True), 1.0)
        self.assertAlmostEqual(main._crop_supply_rate("WHEAT", 2, 4, False), 3 / 5)

    def test_marginal_price(self):
        # nobody else producing, plenty of drain -> full price
        self.assertAlmostEqual(main._absorbed_price("STRAWBERRY", 180, 1, 19, 0, 7, 10, 10, True), 180)
        # 70 tiles already saturate a 19/day drain -> this tile sells at the floor
        self.assertAlmostEqual(main._absorbed_price("STRAWBERRY", 180, 70, 19, 0, 7, 10, 10, True), 1.0)
        # a below-I0 buffer spread over the window adds room
        self.assertGreater(main._absorbed_price("STRAWBERRY", 180, 70, 19, 140, 7, 10, 10, True), 1.0)


class ShopDemandValueTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(main.ENABLE_LEVER2_CROP_MIX)

    def test_low_strawberry_drain_stops_strawberry(self):
        off, on = picks(observation(**LOW), False), picks(observation(**LOW), True)
        self.assertGreaterEqual(off["STRAWBERRY"], 20, off)
        self.assertLessEqual(on["STRAWBERRY"], 2, on)
        self.assertEqual(sum(on.values()), 24, on)

    def test_high_strawberry_drain_unchanged(self):
        self.assertEqual(picks(observation(**HIGH), True), picks(observation(**HIGH), False))

    def test_early_bootstrap_unchanged(self):
        kw = dict(LOW, day=5)
        self.assertEqual(picks(observation(**kw), True), picks(observation(**kw), False))

    def test_shop_names_are_normalised(self):
        kw = dict(LOW, shops=["brunch spot", "Bakery", "pet-cafe"])
        self.assertEqual(picks(observation(**kw), True), picks(observation(**LOW), True))


if __name__ == "__main__":
    unittest.main()
