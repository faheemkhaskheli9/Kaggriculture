"""ENABLE_HERD_BEFORE_LAND: on days 2-9 the 1-quad herd cap is 6, the
quadrant-2 BUY_LAND waits for a herd of 6, and the animal buy under that herd
uses the small reserve floor."""
import unittest
from collections import Counter

import main


def cow():
    return {"kind": "PASTURE", "animal": "COW", "fed_today": True,
            "cared_today": True, "yield_units": 0}


def plant():
    return {"kind": "PLANT", "crop": "STRAWBERRY", "planted_day": 1,
            "fertilized_until_day": -1, "yield_units": 0,
            "consecutive_unwatered": 0, "watered_today": True,
            "max_lifespan_step": -1}


def observation(day, hour, money, animals=3, plants=20, quads=("NW",)):
    width = 5 * len(quads)
    tiles = [[None if (y < 5 and x < width) else "LOCKED" for x in range(10)]
             for y in range(10)]
    cells = [(x, y) for y in range(5) for x in range(5)
             if (x, y) not in main.SHED_TILES]
    for (x, y) in cells[:animals]:
        tiles[y][x] = cow()
    for (x, y) in cells[animals:animals + plants]:
        tiles[y][x] = plant()
    def farm():
        return {"money": money, "tiles": [list(r) for r in tiles],
                "farmer": [4, 4], "hands": [[4, 4]] * 7,
                "unlocked_quadrants": list(quads), "hires_today": 7}
    return {
        "player": 0, "day": day, "hour": hour,
        "farms": [farm(), farm()],
        "private": {"shed": {"WHEAT": 40}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }


def orders(obs):
    me = obs["farms"][0]
    return main.market_orders(obs, me, obs["private"],
                              Counter({"STRAWBERRY": 20}), 8)


class Flagged(unittest.TestCase):
    def setUp(self):
        self._saved = main.ENABLE_HERD_BEFORE_LAND

    def tearDown(self):
        main.ENABLE_HERD_BEFORE_LAND = self._saved

    def cap(self, day):
        obs = observation(day, 1, 5000)
        return sum(main.animal_targets(obs, obs["farms"][0]).values())

    def test_off_one_quad_cap_is_three(self):
        main.ENABLE_HERD_BEFORE_LAND = False
        self.assertEqual(self.cap(5), 3)

    def test_on_one_quad_cap_is_six_inside_window_only(self):
        main.ENABLE_HERD_BEFORE_LAND = True
        self.assertEqual(self.cap(1), 3)
        self.assertEqual(self.cap(5), 6)
        self.assertEqual(self.cap(10), 3)

    def test_on_two_quad_cap_unchanged(self):
        main.ENABLE_HERD_BEFORE_LAND = True
        obs = observation(5, 1, 5000, quads=("NW", "NE"))
        self.assertEqual(sum(main.animal_targets(obs, obs["farms"][0]).values()), 8)

    def test_land_waits_for_herd(self):
        main.ENABLE_HERD_BEFORE_LAND = False
        self.assertIn(["BUY_LAND"], orders(observation(5, 1, 2500)))
        main.ENABLE_HERD_BEFORE_LAND = True
        self.assertNotIn(["BUY_LAND"], orders(observation(5, 1, 2500)))
        self.assertIn(["BUY_LAND"], orders(observation(5, 1, 2500, animals=6, plants=17)))
        self.assertIn(["BUY_LAND"], orders(observation(10, 1, 2500)))   # window over

    def test_shed_animals_count_toward_herd(self):
        main.ENABLE_HERD_BEFORE_LAND = True
        obs = observation(5, 1, 2500, animals=5)
        obs["private"]["shed"]["COW"] = 1
        self.assertIn(["BUY_LAND"], orders(obs))

    def test_animal_buy_uses_small_reserve(self):
        def buys(o):
            return [x for x in orders(o) if x[0] == "BUY_ANIMAL"]
        main.ENABLE_HERD_BEFORE_LAND = False
        self.assertEqual(buys(observation(5, 1, 800)), [])
        main.ENABLE_HERD_BEFORE_LAND = True
        self.assertEqual(len(buys(observation(5, 1, 800))), 1)
        self.assertEqual(buys(observation(5, 1, 250)), [])          # cost + floor out of reach
        self.assertEqual(buys(observation(1, 1, 800)), [])          # opening untouched


if __name__ == "__main__":
    unittest.main()
