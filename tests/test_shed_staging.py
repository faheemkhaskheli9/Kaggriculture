"""ENABLE_SHED_STAGING (Lever H1): late-day delivery + overflow sell-down."""
import copy
import unittest

import main


def farm(money=3000, hands=()):
    return {
        "money": money,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [list(h) for h in hands],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def observation(day=12, hour=18, shed=None, inventories=None, hands=()):
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


class ShedStagingTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_SHED_STAGING
        main.ENABLE_SHED_STAGING = True

    def tearDown(self):
        main.ENABLE_SHED_STAGING = self._flag

    # ---- (a) assign(): late-day delivery ----
    def _assign(self, obs):
        me = obs["farms"][0]
        n = 1 + len(me["hands"])
        zones = [set() for _ in range(n)]
        return main.assign(obs, me, obs["private"], [], zones, forced={})

    def test_loaded_hand_walks_to_shed_late_in_the_day(self):
        obs = observation(hour=15, hands=[(0, 0)], inventories=[{}, {"WHEAT": 8}])
        actions = self._assign(obs)
        self.assertEqual(actions[1], main.step_toward((0, 0), (4, 4)))

    def test_hand_on_shed_tile_drops(self):
        obs = observation(hour=20, hands=[(5, 5)], inventories=[{}, {"STRAWBERRY": 7}])
        self.assertEqual(self._assign(obs)[1], ["DROP"])

    def test_no_staging_before_window_or_with_light_cargo(self):
        early = observation(hour=10, hands=[(0, 0)], inventories=[{}, {"WHEAT": 8}])
        self.assertNotEqual(self._assign(early)[1], main.step_toward((0, 0), (4, 4)))
        light = observation(hour=20, hands=[(5, 5)], inventories=[{}, {"WHEAT": 2}])
        self.assertNotEqual(self._assign(light)[1], ["DROP"])

    def test_staging_respects_forecast_room_and_reach(self):
        # shed already at 98: no room -> nobody is pulled off the field
        full = observation(hour=18, shed={"WHEAT": 98}, hands=[(5, 5)],
                           inventories=[{}, {"WHEAT": 8}])
        self.assertNotEqual(self._assign(full)[1], ["DROP"])
        # hour 22 at (0, 0): cannot reach the shed before day end -> stays
        late = observation(hour=22, hands=[(0, 0)], inventories=[{}, {"WHEAT": 8}])
        self.assertNotEqual(self._assign(late)[1], main.step_toward((0, 0), (4, 4)))

    # ---- (b) market_orders(): overflow sell-down ----
    def _orders(self, obs):
        me = obs["farms"][0]
        return main.market_orders(obs, me, obs["private"], {}, 1 + len(me["hands"]))

    def test_projected_overflow_widens_cheapest_sell(self):
        obs = observation(hour=18, shed={"WHEAT": 90, "STRAWBERRY": 4},
                          inventories=[{"TOMATO": 30}])
        orders = self._orders(obs)
        wheat = [o for o in orders if o[0] == "SELL" and o[1] == "WHEAT"]
        self.assertEqual(len(wheat), 1)
        # 90 + 4 + 30 carried = 124 vs 94 usable -> 30 must go this turn; the
        # 4 strawberries sell anyway, so wheat carries the other 26.
        self.assertGreaterEqual(wheat[0][2], 26)
        self.assertLessEqual(len(orders), 10)

    def test_no_overflow_means_no_change(self):
        obs = observation(hour=18, shed={"WHEAT": 20}, inventories=[{"TOMATO": 5}])
        with_flag = self._orders(obs)
        main.ENABLE_SHED_STAGING = False
        self.assertEqual(with_flag, self._orders(copy.deepcopy(obs)))

    def test_off_path_is_identical(self):
        obs = observation(hour=19, shed={"WHEAT": 80}, hands=[(2, 4)],
                          inventories=[{}, {"WHEAT": 40}])
        main.ENABLE_SHED_STAGING = False
        off_actions = self._assign(copy.deepcopy(obs))
        off_orders = self._orders(copy.deepcopy(obs))
        main.ENABLE_SHED_STAGING = True
        self.assertNotEqual(off_actions, self._assign(copy.deepcopy(obs)))
        self.assertEqual(self._assign(copy.deepcopy(obs))[1], main.step_toward((2, 4), (4, 4)))
        self.assertNotEqual(off_orders, self._orders(copy.deepcopy(obs)))

    def test_day_28_plus_untouched(self):
        obs = observation(day=28, hour=10, shed={"WHEAT": 95}, hands=[(0, 0)],
                          inventories=[{}, {"WHEAT": 20}])
        on = (self._assign(copy.deepcopy(obs)), self._orders(copy.deepcopy(obs)))
        main.ENABLE_SHED_STAGING = False
        off = (self._assign(copy.deepcopy(obs)), self._orders(copy.deepcopy(obs)))
        self.assertEqual(on, off)


if __name__ == "__main__":
    unittest.main()
