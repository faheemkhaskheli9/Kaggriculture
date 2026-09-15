"""ENABLE_ANIMAL_CARRY_GUARD (Lever H2): place carried animals, gate pickups/buys."""
import copy
import unittest

import main


def farm(hands=()):
    return {
        "money": 5000,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [list(h) for h in hands],
        "unlocked_quadrants": ["NW", "NE"],
        "hires_today": 0,
    }


def observation(hour=10, shed=None, inventories=None, hands=()):
    return {
        "player": 0,
        "day": 8,
        "hour": hour,
        "farms": [farm(hands=hands), farm()],
        "private": {
            "shed": dict(shed or {}),
            "seeds": {},
            "inventories": [dict(i) for i in (inventories or [{}])],
        },
        "market": {
            "inventory": {item: 10000 for item in main.BASE},
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": []},
    }


def crew(obs, reserved):
    me = obs["farms"][0]
    positions = [tuple(me["farmer"])] + [tuple(p) for p in me["hands"]]
    return main.animal_crew_actions(obs, me, obs["private"], reserved, [1],
                                    positions, obs["private"]["inventories"])


class AnimalCarryGuardTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_ANIMAL_CARRY_GUARD
        self._c2 = main.ENABLE_HERD_INSTALL_FIRST
        main.ENABLE_ANIMAL_CARRY_GUARD = True
        main.ENABLE_HERD_INSTALL_FIRST = False   # H2 tests isolate H2 from C2

    def tearDown(self):
        main.ENABLE_ANIMAL_CARRY_GUARD = self._flag
        main.ENABLE_HERD_INSTALL_FIRST = self._c2

    def test_last_carried_animal_is_placed_even_with_empty_shed(self):
        obs = observation(hands=[(2, 2)], inventories=[{}, {"COW": 1}])
        obs["farms"][0]["tiles"][2][2] = {"kind": "PASTURE"}
        self.assertEqual(crew(obs, [(2, 2)])[1], ["PLACE", "COW"])
        obs["farms"][0]["hands"] = [[0, 2]]
        self.assertEqual(crew(obs, [(2, 2)])[1], main.step_toward((0, 2), (2, 2)))

    def test_carried_animal_without_structure_builds_one(self):
        obs = observation(hands=[(3, 3)], inventories=[{}, {"GOOSE": 1}])
        self.assertEqual(crew(obs, [(3, 3)])[1], ["BUILD_COOP"])

    def test_off_path_leaves_last_carried_animal_unplaced(self):
        main.ENABLE_ANIMAL_CARRY_GUARD = False
        obs = observation(hands=[(2, 2)], inventories=[{}, {"COW": 1}])
        obs["farms"][0]["tiles"][2][2] = {"kind": "PASTURE"}
        self.assertNotEqual(crew(obs, [(2, 2)]).get(1), ["PLACE", "COW"])

    def test_no_pickup_when_place_cannot_finish_today(self):
        obs = observation(hour=22, hands=[(4, 4)], shed={"SHEEP": 1})
        obs["farms"][0]["tiles"][0][9] = {"kind": "PASTURE"}
        self.assertNotEqual(crew(obs, [(9, 0)]).get(1), ["PICKUP", "SHEEP", 1])
        obs["hour"] = 5
        self.assertEqual(crew(obs, [(9, 0)]).get(1), ["PICKUP", "SHEEP", 1])

    def test_no_animal_buy_into_a_full_shed(self):
        obs = observation(hour=2, shed={"WHEAT": 100})
        me = obs["farms"][0]
        orders = main.market_orders(obs, me, obs["private"], {}, 1)
        self.assertFalse([o for o in orders if o[0] == "BUY_ANIMAL"])
        main.ENABLE_ANIMAL_CARRY_GUARD = False
        orders = main.market_orders(copy.deepcopy(obs), me, obs["private"], {}, 1)
        self.assertTrue([o for o in orders if o[0] == "BUY_ANIMAL"])


if __name__ == "__main__":
    unittest.main()
