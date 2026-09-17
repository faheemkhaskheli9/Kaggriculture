"""ENABLE_SHEEP_ON_YARN: goose slots go to sheep while a YARN_STORE is unlocked."""
import unittest

import main


def farm(quads, animals=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    todo = []
    for kind, n in (animals or {}).items():
        todo += [kind] * n
    i = 0
    for y in range(10):
        for x in range(10):
            if i >= len(todo):
                break
            if (x, y) in main.SHED_TILES:
                continue
            k = todo[i]
            tiles[y][x] = {"kind": "COOP" if k == "GOOSE" else "PASTURE", "animal": k,
                           "fed_today": True, "cared_today": True, "yield_units": 0,
                           "fertilizer_available": False}
            i += 1
    return {
        "money": 5000,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW", "NE", "SW"][:quads],
        "hires_today": 0,
    }


def observation(day, quads=3, opp_animals=0, shops=(), mine=None):
    return {
        "player": 0,
        "day": day,
        "hour": 3,
        "farms": [farm(quads, mine), farm(quads, {"COW": opp_animals})],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {
            "inventory": {item: 10000 for item in main.BASE},
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": list(shops)},
    }


YARN = ("BAKERY", "YARN_STORE", "PIZZA_SHOP")
NO_YARN = ("BAKERY", "PIZZA_SHOP", "SMOOTHIE_SHOP")


class SheepOnYarnTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_SHEEP_ON_YARN
        self._f1 = main.ENABLE_F1_HERD_MATCH
        self._h14 = main.ENABLE_HERD_14
        main.ENABLE_F1_HERD_MATCH = True
        main.ENABLE_HERD_14 = False

    def tearDown(self):
        main.ENABLE_SHEEP_ON_YARN = self._flag
        main.ENABLE_F1_HERD_MATCH = self._f1
        main.ENABLE_HERD_14 = self._h14

    def targets(self, **kw):
        obs = observation(**kw)
        return main.animal_targets(obs, obs["farms"][0])

    def test_off_ignores_yarn_store_match(self):
        main.ENABLE_SHEEP_ON_YARN = False
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=YARN),
                         {"COW": 5, "GOOSE": 5, "SHEEP": 1})

    def test_off_ignores_yarn_store_non_match(self):
        main.ENABLE_SHEEP_ON_YARN = False
        self.assertEqual(self.targets(day=12, opp_animals=0, shops=YARN),
                         {"COW": 9, "GOOSE": 2, "SHEEP": 2})

    def test_on_no_yarn_store_unchanged(self):
        main.ENABLE_SHEEP_ON_YARN = True
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=NO_YARN),
                         {"COW": 5, "GOOSE": 5, "SHEEP": 1})
        self.assertEqual(self.targets(day=12, opp_animals=0, shops=NO_YARN),
                         {"COW": 9, "GOOSE": 2, "SHEEP": 1})

    def test_on_yarn_store_match_sheep_before_goose(self):
        main.ENABLE_SHEEP_ON_YARN = True
        tgt = self.targets(day=12, opp_animals=6, shops=YARN)
        self.assertEqual(tgt, {"COW": 5, "SHEEP": 5, "GOOSE": 1})
        # the one-per-turn buy loop walks dict order: sheep must precede geese
        self.assertEqual(list(tgt), ["COW", "SHEEP", "GOOSE"])
        self.assertEqual(sum(tgt.values()), 11)

    def test_on_yarn_store_non_match(self):
        main.ENABLE_SHEEP_ON_YARN = True
        tgt = self.targets(day=12, opp_animals=0, shops=YARN)
        self.assertEqual(tgt, {"COW": 8, "SHEEP": 4, "GOOSE": 1})
        self.assertEqual(list(tgt), ["COW", "SHEEP", "GOOSE"])

    def test_on_late_draw_keeps_placed_geese(self):
        main.ENABLE_SHEEP_ON_YARN = True
        tgt = self.targets(day=12, opp_animals=6, shops=YARN,
                           mine={"COW": 4, "GOOSE": 3})
        self.assertEqual(tgt["GOOSE"], 3)
        self.assertEqual(tgt["COW"], 5)
        self.assertEqual(tgt["SHEEP"], 5)
        self.assertEqual(sum(tgt.values()), 13)

    def test_on_two_quadrant_cap_fills_sheep_not_geese(self):
        main.ENABLE_SHEEP_ON_YARN = True
        tgt = self.targets(day=12, quads=2, opp_animals=6, shops=YARN)
        self.assertEqual(sum(tgt.values()), 8)
        self.assertEqual(tgt, {"COW": 5, "SHEEP": 3})

    def test_on_freeze_after_day_17(self):
        main.ENABLE_SHEEP_ON_YARN = True
        tgt = self.targets(day=18, opp_animals=6, shops=YARN,
                           mine={"COW": 5, "GOOSE": 5, "SHEEP": 1})
        self.assertEqual(tgt, {"COW": 5, "GOOSE": 5, "SHEEP": 1})

    def test_on_f1_off_crouch_unchanged(self):
        main.ENABLE_SHEEP_ON_YARN = True
        main.ENABLE_F1_HERD_MATCH = False
        tgt = self.targets(day=12, opp_animals=6, shops=YARN)
        self.assertEqual(tgt, {"COW": 3, "GOOSE": 3})


if __name__ == "__main__":
    unittest.main()
