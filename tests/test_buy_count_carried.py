"""ENABLE_BUY_COUNT_CARRIED: an animal carried in a hand counts as owned by the buy loop."""
import copy
import unittest

import main


def farm(cows=0, hands=()):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    placed = 0
    for y in range(10):
        for x in range(10):
            if placed >= cows:
                break
            if (x, y) in main.SHED_TILES:
                continue
            tiles[y][x] = {"kind": "PASTURE", "animal": "COW", "fed_today": True,
                           "cared_today": True, "yield_units": 0,
                           "fertilizer_available": False}
            placed += 1
    return {
        "money": 9000,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [list(h) for h in hands],
        "unlocked_quadrants": ["NW", "NE"],
        "hires_today": 0,
    }


def observation(cows, inventories, shed=None):
    hands = [(2, 2)] * (len(inventories) - 1)
    return {
        "player": 0,
        "day": 8,
        "hour": 2,
        "farms": [farm(cows, hands), farm()],
        "private": {"shed": dict(shed or {}), "seeds": {},
                    "inventories": [dict(i) for i in inventories]},
        "market": {
            "inventory": {item: 10000 for item in main.BASE},
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": []},
    }


def animal_buys(obs):
    me = obs["farms"][0]
    orders = main.market_orders(copy.deepcopy(obs), me, obs["private"], {}, 2)
    return [o for o in orders if o[0] == "BUY_ANIMAL"]


class BuyCountCarriedTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_BUY_COUNT_CARRIED
        self._batch = main.ENABLE_HERDBATCH
        self._f1 = main.ENABLE_F1_HERD_MATCH
        main.ENABLE_BUY_COUNT_CARRIED = True
        main.ENABLE_HERDBATCH = False
        main.ENABLE_F1_HERD_MATCH = True

    def tearDown(self):
        main.ENABLE_BUY_COUNT_CARRIED = self._flag
        main.ENABLE_HERDBATCH = self._batch
        main.ENABLE_F1_HERD_MATCH = self._f1

    def test_two_quadrant_target_is_eight_cows(self):
        obs = observation(7, [{}, {}])
        self.assertEqual(main.animal_targets(obs, obs["farms"][0])["COW"], 8)

    def test_carried_cow_completes_the_herd(self):
        # 7 placed + 1 in a hand = the 8-cow target: no second buy.
        obs = observation(7, [{}, {"COW": 1}])
        self.assertEqual(animal_buys(obs), [])

    def test_missing_cow_is_still_bought(self):
        obs = observation(7, [{}, {}])
        self.assertEqual(animal_buys(obs), [["BUY_ANIMAL", "COW", 1]])

    def test_shed_cow_still_counts(self):
        obs = observation(7, [{}, {}], shed={"COW": 1})
        self.assertEqual(animal_buys(obs), [])

    def test_off_rebuys_the_carried_cow(self):
        main.ENABLE_BUY_COUNT_CARRIED = False
        obs = observation(7, [{}, {"COW": 1}])
        self.assertEqual(animal_buys(obs), [["BUY_ANIMAL", "COW", 1]])

    def test_herdbatch_branch_counts_carried(self):
        main.ENABLE_HERDBATCH = True
        obs = observation(7, [{}, {"COW": 1}])
        obs["farms"][1]["tiles"][0][0] = {"kind": "PASTURE", "animal": "COW"}
        self.assertEqual(animal_buys(obs), [])
        main.ENABLE_BUY_COUNT_CARRIED = False
        self.assertEqual(animal_buys(obs), [["BUY_ANIMAL", "COW", 1]])


if __name__ == "__main__":
    unittest.main()
