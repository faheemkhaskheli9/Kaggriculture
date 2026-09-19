"""ENABLE_STR_CAP: hard-cap new STRAWBERRY plantings on a dry board (no
STRAWBERRY-demanding shop unlocked, price below BASE) instead of relying on
the value calc to redirect on its own."""
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


def observation(day, mine, opp, inv_delta, shops=()):
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
        "town": {"unlocked_shops": list(shops)},
    }


# Dry board, day 13 (STRAWBERRY's last plantable day -- CROPS["STRAWBERRY"]
# plant_by=13, so this is the only day both >= STR_CAP_START_DAY and still
# in STRAWBERRY's window). Inventory just above I0 (price 118, just under
# BASE 120 -- still the myopic top pick over WHEAT/CARROT/TOMATO, val 23.3
# vs TOMATO's 15.8), no shop demands it.
DRY = dict(day=13, mine={"STRAWBERRY": 30}, opp={}, inv_delta={"STRAWBERRY": 1})


def picks(obs, flag):
    saved = main.ENABLE_STR_CAP
    main.ENABLE_STR_CAP = flag
    try:
        me = obs["farms"][0]
        return Counter(main.choose_crops(obs, me, obs["private"],
                                          main.field_counts(me), 20))
    finally:
        main.ENABLE_STR_CAP = saved


class StrCapTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(main.ENABLE_LEVER2_CROP_MIX)
        self.assertFalse(main.ENABLE_SHOP_DEMAND_VALUE)

    def test_off_still_plants_strawberry_on_a_dry_board(self):
        p = picks(observation(**DRY), False)
        self.assertGreater(p["STRAWBERRY"], 0, p)

    def test_on_caps_new_strawberry_on_a_dry_board(self):
        p = picks(observation(**DRY), True)
        self.assertEqual(p["STRAWBERRY"], 0, p)
        self.assertGreater(sum(p.values()), 0, p)

    def test_on_no_cap_once_a_strawberry_shop_is_unlocked(self):
        kw = dict(DRY, shops=["SMOOTHIE_SHOP"])
        self.assertEqual(picks(observation(**kw), True),
                          picks(observation(**kw), False))

    def test_on_no_cap_when_price_is_at_or_above_base(self):
        kw = dict(DRY, inv_delta={})   # I0, price == BASE
        self.assertEqual(picks(observation(**kw), True),
                          picks(observation(**kw), False))

    def test_on_no_cap_before_start_day(self):
        kw = dict(DRY, day=main.STR_CAP_START_DAY - 1)
        self.assertEqual(picks(observation(**kw), True),
                          picks(observation(**kw), False))

    def test_existing_strawberry_tiles_untouched(self):
        # the cap only blocks *new* picks; field_counts already reflects the
        # 30 planted tiles regardless of the flag.
        obs = observation(**DRY)
        me = obs["farms"][0]
        self.assertEqual(main.field_counts(me)["STRAWBERRY"], 30)

    def test_early_bootstrap_unchanged(self):
        kw = dict(DRY, day=5)
        self.assertEqual(picks(observation(**kw), True),
                          picks(observation(**kw), False))


if __name__ == "__main__":
    unittest.main()
