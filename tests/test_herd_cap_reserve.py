"""ENABLE_HERD_CAP_RESERVE: the target loop reserves the placed animals of later species so a late yarn draw cannot stack sheep past the quad cap."""
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
LATE_YARN = ("BAKERY", "PET_CAFE", "FARMERS_MARKET", "YARN_STORE")
LATE_HERD = {"COW": 6, "SHEEP": 1, "GOOSE": 4}


class HerdCapReserveTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: getattr(main, k) for k in
                       ("ENABLE_HERD_CAP_RESERVE", "ENABLE_COW_ON_MILK", "ENABLE_SHEEP_ON_YARN",
                        "ENABLE_F1_HERD_MATCH", "ENABLE_HERD_14", "ENABLE_HERD_INSTALL_FIRST")}
        main.ENABLE_HERD_CAP_RESERVE = True
        main.ENABLE_COW_ON_MILK = True
        main.ENABLE_SHEEP_ON_YARN = True
        main.ENABLE_F1_HERD_MATCH = True
        main.ENABLE_HERD_14 = False
        main.ENABLE_HERD_INSTALL_FIRST = True

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(main, k, v)

    def targets(self, **kw):
        obs = observation(**kw)
        return main.animal_targets(obs, obs["farms"][0])

    def test_late_yarn_match_stays_at_cap(self):
        tgt = self.targets(day=12, opp_animals=6, shops=LATE_YARN, mine=LATE_HERD)
        self.assertEqual(tgt, {"COW": 6, "SHEEP": 3, "GOOSE": 4})
        self.assertEqual(sum(tgt.values()), 13)

    def test_late_yarn_non_match_stays_at_cap(self):
        tgt = self.targets(day=12, opp_animals=0, shops=LATE_YARN, mine=LATE_HERD)
        self.assertEqual(tgt, {"COW": 8, "SHEEP": 1, "GOOSE": 4})

    def test_off_stacks_sheep_past_cap(self):
        main.ENABLE_HERD_CAP_RESERVE = False
        tgt = self.targets(day=12, opp_animals=6, shops=LATE_YARN, mine=LATE_HERD)
        self.assertEqual(tgt, {"COW": 6, "SHEEP": 5, "GOOSE": 4})
        self.assertEqual(sum(tgt.values()), 15)

    def test_early_yarn_unchanged(self):
        for shops, want in ((YARN_NO_MILK, {"COW": 4, "SHEEP": 6, "GOOSE": 1}),
                            (YARN_MILK, {"COW": 5, "SHEEP": 5, "GOOSE": 1})):
            on = self.targets(day=9, opp_animals=6, shops=shops, mine={"COW": 4})
            main.ENABLE_HERD_CAP_RESERVE = False
            off = self.targets(day=9, opp_animals=6, shops=shops, mine={"COW": 4})
            main.ENABLE_HERD_CAP_RESERVE = True
            self.assertEqual(on, want)
            self.assertEqual(on, off)

    def test_no_yarn_unchanged(self):
        mine = {"COW": 6, "GOOSE": 2, "SHEEP": 1}
        on = self.targets(day=12, opp_animals=6, shops=NO_YARN_NO_MILK, mine=mine)
        main.ENABLE_HERD_CAP_RESERVE = False
        off = self.targets(day=12, opp_animals=6, shops=NO_YARN_NO_MILK, mine=mine)
        self.assertEqual(on, {"COW": 6, "GOOSE": 5, "SHEEP": 1})
        self.assertEqual(on, off)

    def test_already_over_cap_keeps_have(self):
        mine = {"COW": 6, "SHEEP": 6, "GOOSE": 6}
        self.assertEqual(self.targets(day=15, opp_animals=6, shops=LATE_YARN, mine=mine), mine)

    def test_freeze_after_day_17(self):
        self.assertEqual(self.targets(day=18, opp_animals=6, shops=LATE_YARN, mine=LATE_HERD), LATE_HERD)

    def test_two_quadrant_cap(self):
        tgt = self.targets(day=12, quads=2, opp_animals=6, shops=LATE_YARN, mine={"COW": 4, "GOOSE": 2})
        self.assertEqual(tgt, {"COW": 5, "SHEEP": 1, "GOOSE": 2})

    def test_shed_animals_are_reserved_too(self):
        obs = observation(day=12, opp_animals=6, shops=LATE_YARN, mine={"COW": 6, "SHEEP": 1, "GOOSE": 2})
        obs["private"]["shed"] = {"GOOSE": 2}
        self.assertEqual(main.animal_targets(obs, obs["farms"][0]), {"COW": 6, "SHEEP": 3, "GOOSE": 4})


if __name__ == "__main__":
    unittest.main()
