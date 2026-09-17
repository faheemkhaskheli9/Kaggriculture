"""ENABLE_COW_ON_MILK: under a yarn store, cow slots go to sheep from day 9 when none of the first three draws buys MILK."""
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


YARN_NO_MILK = ("BAKERY", "YARN_STORE", "PET_CAFE")
YARN_MILK = ("BAKERY", "YARN_STORE", "PIZZA_SHOP")
NO_YARN_NO_MILK = ("BAKERY", "PET_CAFE", "FARMERS_MARKET")


class CowOnMilkTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: getattr(main, k) for k in
                       ("ENABLE_COW_ON_MILK", "ENABLE_SHEEP_ON_YARN",
                        "ENABLE_F1_HERD_MATCH", "ENABLE_HERD_14")}
        main.ENABLE_COW_ON_MILK = True
        main.ENABLE_SHEEP_ON_YARN = True
        main.ENABLE_F1_HERD_MATCH = True
        main.ENABLE_HERD_14 = False

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(main, k, v)

    def targets(self, **kw):
        obs = observation(**kw)
        return main.animal_targets(obs, obs["farms"][0])

    def test_yarn_no_milk_match_cows_to_sheep(self):
        tgt = self.targets(day=12, opp_animals=6, shops=YARN_NO_MILK)
        self.assertEqual(tgt, {"COW": 4, "SHEEP": 6, "GOOSE": 1})
        self.assertEqual(list(tgt), ["COW", "SHEEP", "GOOSE"])

    def test_yarn_no_milk_non_match(self):
        self.assertEqual(self.targets(day=12, opp_animals=0, shops=YARN_NO_MILK),
                         {"COW": 4, "SHEEP": 8, "GOOSE": 1})

    def test_no_yarn_no_milk_unchanged(self):
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=NO_YARN_NO_MILK),
                         {"COW": 5, "GOOSE": 5, "SHEEP": 1})
        self.assertEqual(self.targets(day=12, opp_animals=0, shops=NO_YARN_NO_MILK),
                         {"COW": 9, "GOOSE": 2, "SHEEP": 1})

    def test_milk_shop_present_unchanged(self):
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=YARN_MILK),
                         {"COW": 5, "SHEEP": 5, "GOOSE": 1})

    def test_milk_shop_as_fourth_draw_is_too_late(self):
        late = ("BAKERY", "YARN_STORE", "PET_CAFE", "PIZZA_SHOP")
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=late),
                         {"COW": 4, "SHEEP": 6, "GOOSE": 1})
        early = ("PIZZA_SHOP", "YARN_STORE", "PET_CAFE", "BAKERY")
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=early),
                         {"COW": 5, "SHEEP": 5, "GOOSE": 1})

    def test_yarn_as_fourth_draw_is_too_late(self):
        late_yarn = ("BAKERY", "PET_CAFE", "FARMERS_MARKET", "YARN_STORE")
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=late_yarn),
                         {"COW": 5, "SHEEP": 5, "GOOSE": 1})

    def test_repeated_draws_count_by_position(self):
        self.assertEqual(self.targets(day=12, opp_animals=6,
                                      shops=("YARN_STORE", "BAKERY", "BAKERY", "SMOOTHIE_SHOP")),
                         {"COW": 4, "SHEEP": 6, "GOOSE": 1})

    def test_before_day_9_unchanged(self):
        self.assertEqual(self.targets(day=8, opp_animals=6, shops=YARN_NO_MILK),
                         {"COW": 5, "SHEEP": 5, "GOOSE": 1})

    def test_placed_cows_are_kept(self):
        tgt = self.targets(day=12, opp_animals=6, shops=YARN_NO_MILK, mine={"COW": 5})
        self.assertEqual(tgt, {"COW": 5, "SHEEP": 6, "GOOSE": 1})

    def test_two_quadrant_cap(self):
        tgt = self.targets(day=12, quads=2, opp_animals=6, shops=YARN_NO_MILK)
        self.assertEqual(tgt, {"COW": 4, "SHEEP": 4})

    def test_off_unchanged(self):
        main.ENABLE_COW_ON_MILK = False
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=YARN_NO_MILK),
                         {"COW": 5, "SHEEP": 5, "GOOSE": 1})
        self.assertEqual(self.targets(day=12, opp_animals=6, shops=NO_YARN_NO_MILK),
                         {"COW": 5, "GOOSE": 5, "SHEEP": 1})


if __name__ == "__main__":
    unittest.main()
