"""ENABLE_CROP_CROWD_OWN_ONLY (Lever C3): opponent tiles no longer discount a crop's price."""
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
    return {
        "money": 15000,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [[4, 5]] * 10,
        "unlocked_quadrants": ["NW", "NE", "SW"],
        "hires_today": 0,
    }


def observation(day, mine, opp, inv_delta):
    """Replay-shaped obs; inv_delta = market inventory offsets from I0 per item."""
    inventory = {item: 10000 + inv_delta.get(item, 0) for item in main.BASE}
    return {
        "player": 0,
        "day": day,
        "hour": 1,
        "farms": [farm(mine), farm(opp)],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {
            "inventory": inventory,
            "prices": {item: main.price_at(item, inventory[item]) for item in main.BASE},
        },
        "town": {"unlocked_shops": []},
    }


# `109371856` day 12 hour 1: STRAWBERRY -32 (price 168), WHEAT -154 (37),
# TOMATO -50, MELON +101; we held 24 STRAWBERRY, the opponent 39.
FLIP = dict(day=12,
            mine={"STRAWBERRY": 24, "WHEAT": 6, "TOMATO": 2, "MELON": 1},
            opp={"STRAWBERRY": 39, "WHEAT": 7, "MELON": 12},
            inv_delta={"STRAWBERRY": -32, "WHEAT": -154, "TOMATO": -50,
                       "MELON": 101, "CARROT": 29})


def picks(obs, flag):
    saved = main.ENABLE_CROP_CROWD_OWN_ONLY
    main.ENABLE_CROP_CROWD_OWN_ONLY = flag
    try:
        me = obs["farms"][0]
        return Counter(main.choose_crops(obs, me, obs["private"],
                                         main.field_counts(me), 24))
    finally:
        main.ENABLE_CROP_CROWD_OWN_ONLY = saved


class CropCrowdOwnOnlyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(main.ENABLE_LEVER2_CROP_MIX)
        self.assertTrue(main.ENABLE_CROP_VALUE_LIFESPAN)

    def test_off_reproduces_the_wheat_flip(self):
        p = picks(observation(**FLIP), False)
        self.assertGreaterEqual(p["WHEAT"], 15, p)
        self.assertLessEqual(p["STRAWBERRY"], 5, p)

    def test_on_fills_the_new_quadrant_with_strawberry(self):
        p = picks(observation(**FLIP), True)
        self.assertGreaterEqual(p["STRAWBERRY"], 20, p)
        self.assertEqual(p["WHEAT"], 0, p)

    def test_no_op_when_opponent_field_is_empty(self):
        kw = dict(FLIP, opp={})
        self.assertEqual(picks(observation(**kw), True), picks(observation(**kw), False))

    def test_own_pick_discount_still_diversifies(self):
        # neutral market, no opponent tiles: each own STRAWBERRY pick still
        # walks its projected price down, so a 24-slot call is not all STRAWBERRY
        obs = observation(day=12, mine={}, opp={}, inv_delta={})
        p = picks(obs, True)
        self.assertGreater(p["STRAWBERRY"], 8, p)
        self.assertLess(p["STRAWBERRY"], 24, p)
        self.assertGreater(p["TOMATO"] + p["MELON"], 0, p)

    def test_early_bootstrap_unchanged(self):
        kw = dict(FLIP, day=5)
        self.assertEqual(picks(observation(**kw), True), picks(observation(**kw), False))


if __name__ == "__main__":
    unittest.main()
