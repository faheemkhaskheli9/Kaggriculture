"""ENABLE_FEED_FIRST (C2b): at-risk (second-day unfed) animals outrank harvest/care/fertilizer."""
import unittest

import main
from test_herd_install_first import observation, crew


def animal(fed, yield_units=0, fert=False, cared=False, unfed_days=0):
    return {"kind": "COOP", "animal": "GOOSE", "fed_today": fed,
            "cared_today": cared, "yield_units": yield_units,
            "fertilizer_available": fert, "consecutive_unfed": unfed_days}


class FeedFirstTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_FEED_FIRST
        self._c2 = main.ENABLE_HERD_INSTALL_FIRST
        self._h2 = main.ENABLE_ANIMAL_CARRY_GUARD
        main.ENABLE_FEED_FIRST = True
        main.ENABLE_HERD_INSTALL_FIRST = False
        main.ENABLE_ANIMAL_CARRY_GUARD = False

    def tearDown(self):
        main.ENABLE_FEED_FIRST = self._flag
        main.ENABLE_HERD_INSTALL_FIRST = self._c2
        main.ENABLE_ANIMAL_CARRY_GUARD = self._h2

    def _obs(self, wheat, shed_wheat=20, unfed_days=1):
        # hand 1 stands on a fed goose with eggs at (2,2); an unfed goose that
        # already missed yesterday's feed (at risk) sits at (2,6)
        obs = observation(hour=10, shed={"WHEAT": shed_wheat},
                          inventories=[{}, {"WHEAT": wheat} if wheat else {}],
                          hands=[(2, 2)])
        tiles = obs["farms"][0]["tiles"]
        tiles[2][2] = animal(fed=True, yield_units=3, fert=True)
        tiles[6][2] = animal(fed=False, unfed_days=unfed_days)
        return obs

    def test_on_first_day_unfed_is_not_urgent(self):
        acts = crew(self._obs(wheat=3, unfed_days=0), reserved=[(2, 2), (2, 6)])
        self.assertEqual(acts[1], ["HARVEST"])      # prior ordering kept

    def test_on_hand_with_wheat_leaves_eggs_to_feed(self):
        acts = crew(self._obs(wheat=3), reserved=[(2, 2), (2, 6)])
        self.assertEqual(acts[1], ["SOUTH"])          # toward (2,6), not HARVEST

    def test_off_hand_with_wheat_harvests_first(self):
        main.ENABLE_FEED_FIRST = False
        acts = crew(self._obs(wheat=3), reserved=[(2, 2), (2, 6)])
        self.assertEqual(acts[1], ["HARVEST"])

    def test_on_hand_without_wheat_goes_to_shed_not_harvest(self):
        acts = crew(self._obs(wheat=0), reserved=[(2, 2), (2, 6)])
        self.assertIn(acts[1], (["EAST"], ["SOUTH"]))   # toward the shed at (4,4)

    def test_on_no_wheat_anywhere_falls_back_to_harvest(self):
        acts = crew(self._obs(wheat=0, shed_wheat=0), reserved=[(2, 2), (2, 6)])
        self.assertEqual(acts[1], ["HARVEST"])

    def test_on_standing_on_unfed_animal_feeds(self):
        obs = self._obs(wheat=2)
        obs["farms"][0]["hands"] = [[2, 6]]
        acts = crew(obs, reserved=[(2, 2), (2, 6)])
        self.assertEqual(acts[1], ["FEED"])

    def test_on_all_fed_resumes_normal_goals(self):
        obs = self._obs(wheat=2)
        obs["farms"][0]["tiles"][6][2] = animal(fed=True)
        acts = crew(obs, reserved=[(2, 2), (2, 6)])
        self.assertEqual(acts[1], ["HARVEST"])


if __name__ == "__main__":
    unittest.main()
