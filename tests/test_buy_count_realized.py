"""ENABLE_BUY_COUNT_REALIZED: count carried animals in the buy loop and keep the realized herd as explicit targets."""
import copy
import unittest

import main
from tests.test_herd_cap_reserve import observation, YARN_NO_MILK, NO_YARN_NO_MILK


def buy_observation(cows, inventories, shed=None):
    obs = observation(8, quads=2, mine={"COW": cows})
    obs["hour"] = 2
    obs["farms"][0]["money"] = 9000
    obs["farms"][0]["hands"] = [[2, 2]] * (len(inventories) - 1)
    obs["private"] = {"shed": dict(shed or {}), "seeds": {},
                      "inventories": [dict(i) for i in inventories]}
    return obs


def animal_buys(obs):
    me = obs["farms"][0]
    orders = main.market_orders(copy.deepcopy(obs), me, obs["private"], {}, 2)
    return [o for o in orders if o[0] == "BUY_ANIMAL"]


class BuyCountRealizedTests(unittest.TestCase):
    FLAGS = ("ENABLE_BUY_COUNT_REALIZED", "ENABLE_BUY_COUNT_CARRIED", "ENABLE_HERDBATCH",
             "ENABLE_COW_ON_MILK", "ENABLE_SHEEP_ON_YARN", "ENABLE_F1_HERD_MATCH",
             "ENABLE_HERD_14", "ENABLE_HERD_INSTALL_FIRST", "ENABLE_HERD_CAP_RESERVE")

    def setUp(self):
        self._saved = {k: getattr(main, k) for k in self.FLAGS}
        main.ENABLE_BUY_COUNT_REALIZED = True
        main.ENABLE_BUY_COUNT_CARRIED = False
        main.ENABLE_HERDBATCH = False
        main.ENABLE_COW_ON_MILK = True
        main.ENABLE_SHEEP_ON_YARN = True
        main.ENABLE_F1_HERD_MATCH = True
        main.ENABLE_HERD_14 = False
        main.ENABLE_HERD_INSTALL_FIRST = True
        main.ENABLE_HERD_CAP_RESERVE = False

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(main, k, v)

    def targets(self, **kw):
        obs = observation(**kw)
        return main.animal_targets(obs, obs["farms"][0])

    # --- explicit realized targets
    def test_match_no_yarn_is_six_one_six(self):
        self.assertEqual(self.targets(day=12, opp_animals=5, shops=NO_YARN_NO_MILK),
                         {"COW": 6, "GOOSE": 6, "SHEEP": 1})

    def test_match_yarn_is_six_six_one(self):
        self.assertEqual(self.targets(day=12, opp_animals=5, shops=("BAKERY", "YARN_STORE", "PIZZA_SHOP")),
                         {"COW": 6, "SHEEP": 6, "GOOSE": 1})

    def test_milk_cap_is_five_seven_one(self):
        self.assertEqual(self.targets(day=12, opp_animals=5, shops=YARN_NO_MILK),
                         {"COW": 5, "SHEEP": 7, "GOOSE": 1})

    def test_one_quad_cap_is_four_cows(self):
        self.assertEqual(self.targets(day=5, quads=1), {"COW": 4})

    def test_two_quad_stage_unchanged(self):
        self.assertEqual(self.targets(day=8, quads=2, opp_animals=5, shops=NO_YARN_NO_MILK),
                         {"COW": 5, "GOOSE": 3})

    def test_non_match_wants_unchanged(self):
        self.assertEqual(self.targets(day=12, shops=NO_YARN_NO_MILK),
                         {"COW": 9, "GOOSE": 2, "SHEEP": 1})
        self.assertEqual(self.targets(day=12, shops=("BAKERY", "YARN_STORE", "PIZZA_SHOP")),
                         {"COW": 8, "SHEEP": 4, "GOOSE": 1})

    def test_placed_animals_are_kept(self):
        self.assertEqual(self.targets(day=12, opp_animals=5, shops=NO_YARN_NO_MILK,
                                      mine={"COW": 7, "GOOSE": 6, "SHEEP": 1}),
                         {"COW": 7, "GOOSE": 6, "SHEEP": 1})

    def test_day_18_freeze(self):
        self.assertEqual(self.targets(day=18, opp_animals=5, shops=NO_YARN_NO_MILK,
                                      mine={"COW": 5, "GOOSE": 5, "SHEEP": 1}),
                         {"COW": 5, "GOOSE": 5, "SHEEP": 1})

    # --- carried animals count in the buy loop
    def test_carried_cow_completes_the_herd(self):
        obs = buy_observation(4, [{}, {"COW": 1}])   # 2-quad, no opp animals -> want COW 8
        obs["private"]["shed"] = {"COW": 3}
        self.assertEqual(animal_buys(obs), [])

    def test_missing_cow_is_still_bought(self):
        obs = buy_observation(4, [{}, {}])
        obs["private"]["shed"] = {"COW": 3}
        self.assertEqual(animal_buys(obs), [["BUY_ANIMAL", "COW", 1]])

    # --- OFF = exact prior behaviour
    def test_off_targets(self):
        main.ENABLE_BUY_COUNT_REALIZED = False
        self.assertEqual(self.targets(day=12, opp_animals=5, shops=NO_YARN_NO_MILK),
                         {"COW": 5, "GOOSE": 5, "SHEEP": 1})
        self.assertEqual(self.targets(day=12, opp_animals=5, shops=YARN_NO_MILK),
                         {"COW": 4, "SHEEP": 6, "GOOSE": 1})
        self.assertEqual(self.targets(day=5, quads=1), {"COW": 3})

    def test_off_rebuys_the_carried_cow(self):
        main.ENABLE_BUY_COUNT_REALIZED = False
        obs = buy_observation(4, [{}, {"COW": 1}])
        obs["private"]["shed"] = {"COW": 3}
        self.assertEqual(animal_buys(obs), [["BUY_ANIMAL", "COW", 1]])


if __name__ == "__main__":
    unittest.main()
