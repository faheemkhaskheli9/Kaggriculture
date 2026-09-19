"""ENABLE_CROSS_ZONE_DIG: let a hand cross zones for a DIG task specifically
when its own zone has no pending DIG task left. Unlike WATER/HARVEST, DIG had
no cross-zone escape hatch at all before this flag (main.py:3395)."""
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


def observation(day=12, hour=5, hands=()):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(hands=hands), farm()],
        "private": {"shed": {}, "seeds": {},
                    "inventories": [{} for _ in range(1 + len(hands))]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }


class CrossZoneDigTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_CROSS_ZONE_DIG
        main.ENABLE_CROSS_ZONE_DIG = True

    def tearDown(self):
        main.ENABLE_CROSS_ZONE_DIG = self._flag

    def test_off_flag_blocks_cross_zone_dig(self):
        main.ENABLE_CROSS_ZONE_DIG = False
        obs = observation(hands=[(0, 1)])
        me = obs["farms"][0]
        tasks = [(2400, (5, 5), ["PLANT"]), (2200, (0, 1), ["DIG"])]
        zones = [{(5, 5)}, {(0, 1)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertNotEqual(actions[0], ["DIG"])

    def test_on_flag_allows_cross_zone_dig_when_own_zone_has_none(self):
        # single unit (no hand) so there's no other candidate to steal the
        # cross-zone DIG assignment.
        obs = observation()
        me = obs["farms"][0]
        me["farmer"] = [0, 1]
        tasks = [(2400, (5, 5), ["PLANT"]), (2200, (0, 1), ["DIG"])]
        zones = [{(5, 5)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertEqual(actions[0], ["DIG"])

    def test_on_flag_still_blocked_when_own_zone_has_a_weed_task(self):
        # farmer at (0,0); own-zone DIG task at (5,5) (step_toward -> EAST
        # first); a closer out-of-zone DIG task sits at (0,1) (step_toward ->
        # SOUTH). Even with the flag ON, a pending own-zone weed must keep
        # the farmer heading EAST toward its own tile, not crossing SOUTH to
        # the nearer foreign one.
        obs = observation(hands=[(9, 9)])
        me = obs["farms"][0]
        me["farmer"] = [0, 0]
        tasks = [(2200, (5, 5), ["DIG"]), (2200, (0, 1), ["DIG"])]
        zones = [{(5, 5)}, {(9, 9)}]
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertEqual(actions[0], ["EAST"])

    def test_on_flag_does_not_touch_a_zoned_weed_still_blocked_for_others(self):
        # A DIG target outside every hand's zone (no zone owns it at all)
        # must stay unreachable regardless of the flag -- cross-zone means
        # "borrow another unit's zone", not "ignore zoning entirely".
        obs = observation()
        me = obs["farms"][0]
        me["farmer"] = [0, 0]
        tasks = [(2200, (9, 9), ["DIG"])]
        zones = [{(5, 5)}]   # (9, 9) is in nobody's zone
        actions = main.assign(obs, me, obs["private"], tasks, zones, {})
        self.assertNotEqual(actions[0], ["DIG"])


if __name__ == "__main__":
    unittest.main()
