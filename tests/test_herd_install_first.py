"""ENABLE_HERD_INSTALL_FIRST (Lever C2): install bought animals before crew goals."""
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


def observation(hour=10, day=12, shed=None, inventories=None, hands=()):
    return {
        "player": 0,
        "day": day,
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


def placed_cow(fed=True):
    # a placed cow that still has fertilizer to collect -> a live crew goal
    return {"kind": "PASTURE", "animal": "COW", "fed_today": fed,
            "cared_today": True, "yield_units": 0, "fertilizer_available": True}


def crew(obs, reserved, crew_idx=(1,)):
    me = obs["farms"][0]
    positions = [tuple(me["farmer"])] + [tuple(p) for p in me["hands"]]
    return main.animal_crew_actions(obs, me, obs["private"], reserved, list(crew_idx),
                                    positions, obs["private"]["inventories"])


class HerdInstallFirstTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_HERD_INSTALL_FIRST
        self._h2 = main.ENABLE_ANIMAL_CARRY_GUARD
        main.ENABLE_HERD_INSTALL_FIRST = True
        main.ENABLE_ANIMAL_CARRY_GUARD = False

    def tearDown(self):
        main.ENABLE_HERD_INSTALL_FIRST = self._flag
        main.ENABLE_ANIMAL_CARRY_GUARD = self._h2

    def _shed_cow_with_goal(self, hour=10, hands=((5, 3),)):
        """Shed holds a COW, an empty PASTURE waits at (2,2), and a placed cow
        at (8,8) offers a fertilizer goal that used to win every time."""
        obs = observation(hour=hour, shed={"COW": 1, "WHEAT": 20}, hands=hands,
                          inventories=[{}, {"WHEAT": 3}])
        obs["farms"][0]["tiles"][2][2] = {"kind": "PASTURE"}
        obs["farms"][0]["tiles"][8][8] = placed_cow()
        return obs

    def test_shed_animal_is_fetched_ahead_of_fertilizer_goal(self):
        obs = self._shed_cow_with_goal()
        # hand at (5,3) is shed-adjacent? (5,4) is a shed tile; (5,3) is not -> walk first
        act = crew(obs, [(2, 2), (8, 8)])[1]
        self.assertEqual(act, main.step_toward((5, 3), (5, 4)))
        obs["farms"][0]["hands"] = [[5, 4]]
        self.assertEqual(crew(obs, [(2, 2), (8, 8)])[1], ["PICKUP", "COW", 1])

    def test_carried_animal_is_placed_before_any_goal(self):
        obs = observation(shed={"WHEAT": 20}, hands=[(2, 2)],
                          inventories=[{}, {"COW": 1, "WHEAT": 3}])
        obs["farms"][0]["tiles"][2][2] = {"kind": "PASTURE"}
        obs["farms"][0]["tiles"][8][8] = placed_cow(fed=False)   # feed goal pending
        self.assertEqual(crew(obs, [(2, 2), (8, 8)])[1], ["PLACE", "COW"])
        obs["farms"][0]["hands"] = [[0, 2]]
        self.assertEqual(crew(obs, [(2, 2), (8, 8)])[1], main.step_toward((0, 2), (2, 2)))

    def test_carried_animal_builds_when_no_structure_is_empty(self):
        obs = observation(shed={}, hands=[(3, 3)], inventories=[{}, {"GOOSE": 1}])
        obs["farms"][0]["tiles"][8][8] = placed_cow()
        self.assertEqual(crew(obs, [(3, 3), (8, 8)])[1], ["BUILD_COOP"])

    def test_no_fetch_when_errand_cannot_finish_today(self):
        obs = self._shed_cow_with_goal(hour=22)
        self.assertNotEqual(crew(obs, [(2, 2), (8, 8)])[1], ["PICKUP", "COW", 1])
        self.assertNotEqual(crew(obs, [(2, 2), (8, 8)])[1], main.step_toward((5, 3), (5, 4)))

    def test_no_fetch_when_animal_has_nowhere_to_go(self):
        obs = observation(shed={"COW": 1}, hands=[(5, 4)], inventories=[{}, {}])
        obs["farms"][0]["tiles"][8][8] = placed_cow()
        # reserved holds only the occupied pasture: no empty structure, no build spot
        self.assertNotEqual(crew(obs, [(8, 8)]).get(1), ["PICKUP", "COW", 1])

    def test_lone_crew_hand_feeds_before_fetching(self):
        obs = self._shed_cow_with_goal()
        obs["farms"][0]["tiles"][8][8] = placed_cow(fed=False)
        act = crew(obs, [(2, 2), (8, 8)])[1]
        self.assertNotEqual(act, ["PICKUP", "COW", 1])
        self.assertNotEqual(act, main.step_toward((5, 3), (5, 4)))

    def test_targets_keep_shed_animals_after_freeze(self):
        obs = observation(day=20, shed={"COW": 2, "GOOSE": 1})
        obs["farms"][0]["tiles"][8][8] = placed_cow()
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(tgt.get("COW"), 3)
        self.assertEqual(tgt.get("GOOSE"), 1)
        main.ENABLE_HERD_INSTALL_FIRST = False
        tgt = main.animal_targets(obs, obs["farms"][0])
        self.assertEqual(tgt.get("COW"), 1)
        self.assertNotIn("GOOSE", tgt)

    def test_off_path_still_diverts_to_goal(self):
        main.ENABLE_HERD_INSTALL_FIRST = False
        obs = self._shed_cow_with_goal()
        obs["farms"][0]["hands"] = [[5, 4]]
        self.assertNotEqual(crew(obs, [(2, 2), (8, 8)])[1], ["PICKUP", "COW", 1])


if __name__ == "__main__":
    unittest.main()
