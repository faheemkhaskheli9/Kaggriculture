"""ENABLE_HERD_14: 3-quadrant herd cap 13 -> 14 with GOOSE-weighted wants."""
import unittest

import main


def farm(quads, opp_animals=0):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    n = 0
    for y in range(10):
        for x in range(10):
            if n >= opp_animals:
                break
            if (x, y) in main.SHED_TILES:
                continue
            tiles[y][x] = {"kind": "PASTURE", "animal": "COW", "fed_today": True,
                           "cared_today": True, "yield_units": 0,
                           "fertilizer_available": False}
            n += 1
    return {
        "money": 5000,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW", "NE", "SW"][:quads],
        "hires_today": 0,
    }


def observation(day, quads=3, opp_animals=0):
    return {
        "player": 0,
        "day": day,
        "hour": 3,
        "farms": [farm(quads), farm(quads, opp_animals)],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {
            "inventory": {item: 10000 for item in main.BASE},
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": []},
    }


class Herd14Tests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_HERD_14
        self._f1 = main.ENABLE_F1_HERD_MATCH
        main.ENABLE_F1_HERD_MATCH = True

    def tearDown(self):
        main.ENABLE_HERD_14 = self._flag
        main.ENABLE_F1_HERD_MATCH = self._f1

    def test_off_matches_prior_herd_match_target(self):
        main.ENABLE_HERD_14 = False
        obs = observation(day=12, opp_animals=6)
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(tgt, {"COW": 5, "GOOSE": 5, "SHEEP": 1})

    def test_on_herd_match_targets_14(self):
        main.ENABLE_HERD_14 = True
        obs = observation(day=12, opp_animals=6)
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(tgt, {"COW": 6, "GOOSE": 6, "SHEEP": 2})
        self.assertEqual(sum(tgt.values()), 14)

    def test_on_non_match_targets_14(self):
        main.ENABLE_HERD_14 = True
        obs = observation(day=12, opp_animals=0)
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(sum(tgt.values()), 14)
        self.assertEqual(tgt["GOOSE"], 3)

    def test_off_non_match_unchanged(self):
        main.ENABLE_HERD_14 = False
        obs = observation(day=12, opp_animals=0)
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(sum(tgt.values()), 12)   # COW9/GOOSE2/SHEEP1 at cap 13

    def test_on_lower_quadrant_caps_unchanged(self):
        main.ENABLE_HERD_14 = True
        for quads, cap in ((1, 3), (2, 8)):
            obs = observation(day=12, quads=quads, opp_animals=6)
            tgt = main.animal_targets(obs, obs["farms"][0])
            self.assertEqual(sum(tgt.values()), cap, quads)

    def test_on_freeze_after_day_17(self):
        main.ENABLE_HERD_14 = True
        obs = observation(day=18, opp_animals=6)
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(sum(tgt.values()), 0)

    def test_on_reserves_14_empty_tiles(self):
        main.ENABLE_HERD_14 = True
        obs = observation(day=12, opp_animals=6)
        me = obs["farms"][0]
        tiles = main.animal_tiles(me, main.animal_targets(obs, me))
        self.assertEqual(len(tiles), 14)
        self.assertTrue(all(t not in main.SHED_TILES for t in tiles))


if __name__ == "__main__":
    unittest.main()
