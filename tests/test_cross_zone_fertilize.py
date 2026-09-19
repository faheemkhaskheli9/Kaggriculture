"""ENABLE_CROSS_ZONE_FERTILIZE: let a hand cross zones for a crop FERTILIZE
task specifically when its own zone has no pending FERTILIZE task left.
Same structural gap CROSS_ZONE_DIG fixed for DIG, applied to FERTILIZE
(main.py:3406-3417) -- FERTILIZE had no cross-zone escape hatch at all."""
import unittest

import main


def farm(hands=()):
    return {
        "money": 5000,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [list(h) for h in hands],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def observation(day=12, hour=5, hands=(), inventories=None):
    n = 1 + len(hands)
    invs = inventories if inventories is not None else [{} for _ in range(n)]
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(hands=hands), farm()],
        "private": {"shed": {}, "seeds": {}, "inventories": invs},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }


class CrossZoneFertilizeTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_CROSS_ZONE_FERTILIZE
        main.ENABLE_CROSS_ZONE_FERTILIZE = True
        self.assertTrue(main.ENABLE_CROP_FERTILIZE)

    def tearDown(self):
        main.ENABLE_CROSS_ZONE_FERTILIZE = self._flag

    def test_off_flag_blocks_cross_zone_fertilize(self):
        main.ENABLE_CROSS_ZONE_FERTILIZE = False
        obs = observation(hands=[(0, 1)], inventories=[{"FERTILIZER": 1}, {}])
        me = obs["farms"][0]
        tasks = [(2400, (5, 5), ["PLANT"]), (2650, (0, 1), ["FERTILIZE"])]
        zones = [{(5, 5)}, {(0, 1)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertNotEqual(actions[0], ["FERTILIZE"])

    def test_on_flag_allows_cross_zone_fertilize_when_own_zone_has_none(self):
        # single unit (no hand) so there's no other candidate to steal the
        # cross-zone FERTILIZE assignment.
        obs = observation(inventories=[{"FERTILIZER": 1}])
        me = obs["farms"][0]
        me["farmer"] = [0, 1]
        tasks = [(2400, (5, 5), ["PLANT"]), (2650, (0, 1), ["FERTILIZE"])]
        zones = [{(5, 5)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertEqual(actions[0], ["FERTILIZE"])

    def test_on_flag_still_blocked_when_own_zone_has_a_fertilize_task(self):
        # farmer at (0,0); own-zone FERTILIZE task at (5,5) (step_toward ->
        # EAST first); a closer out-of-zone FERTILIZE task sits at (0,1)
        # (step_toward -> SOUTH). Even with the flag ON, a pending own-zone
        # fertilize need must keep the farmer heading EAST, not crossing
        # SOUTH to the nearer foreign one.
        obs = observation(hands=[(9, 9)],
                           inventories=[{"FERTILIZER": 2}, {}])
        me = obs["farms"][0]
        me["farmer"] = [0, 0]
        tasks = [(2650, (5, 5), ["FERTILIZE"]), (2650, (0, 1), ["FERTILIZE"])]
        zones = [{(5, 5)}, {(9, 9)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertEqual(actions[0], ["EAST"])

    def test_on_flag_does_not_help_without_fertilizer_in_hand(self):
        # the pre-existing "needs FERTILIZER in hand" gate still applies --
        # cross-zone coverage doesn't bypass carrying the input.
        obs = observation(inventories=[{}])
        me = obs["farms"][0]
        me["farmer"] = [0, 1]
        tasks = [(2400, (5, 5), ["PLANT"]), (2650, (0, 1), ["FERTILIZE"])]
        zones = [{(5, 5)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertNotEqual(actions[0], ["FERTILIZE"])


if __name__ == "__main__":
    unittest.main()
