"""ENABLE_TASK_STICKY: a unit still walking to the target it was given last
turn keeps it (TASK_STICKY_BONUS instead of the +90 soft commitment) unless
survival work outbids it."""
import unittest

import main


def farm():
    return {
        "money": 5000,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [0, 0],
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def observation(day=12, hour=5):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(), farm()],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }


FAR = (3000, (4, 0), ["WATER"])
ZONES = [{(4, 0), (1, 1)}]


class TaskStickyTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_TASK_STICKY
        main._ROUTE_MEMORY.clear()

    def tearDown(self):
        main.ENABLE_TASK_STICKY = self._flag
        main._ROUTE_MEMORY.clear()

    def _second_turn(self, newcomer):
        """Turn 1 commits the farmer to FAR; turn 2 (one step on) adds a task."""
        obs = observation(hour=5)
        me = obs["farms"][0]
        first = main.assign(obs, me, obs["private"], [FAR], ZONES, {})
        self.assertEqual(first[0], ["EAST"])
        obs = observation(hour=6)
        me = obs["farms"][0]
        me["farmer"] = [1, 0]
        return main.assign(obs, me, obs["private"], [FAR, newcomer], ZONES, {})[0]

    def test_off_flag_rematches_to_the_nearer_newcomer(self):
        main.ENABLE_TASK_STICKY = False
        self.assertEqual(self._second_turn((3100, (1, 1), ["WATER"])), ["SOUTH"])

    def test_on_flag_keeps_the_route(self):
        main.ENABLE_TASK_STICKY = True
        self.assertEqual(self._second_turn((3100, (1, 1), ["WATER"])), ["EAST"])

    def test_on_flag_survival_work_still_wins(self):
        main.ENABLE_TASK_STICKY = True
        self.assertEqual(self._second_turn((10000, (1, 1), ["WATER"])), ["SOUTH"])

    def test_on_flag_no_memory_matches_like_off(self):
        obs = observation(hour=6)
        me = obs["farms"][0]
        me["farmer"] = [1, 0]
        tasks = [FAR, (3100, (1, 1), ["WATER"])]
        main.ENABLE_TASK_STICKY = False
        off = main.assign(obs, me, obs["private"], tasks, ZONES, {})
        main._ROUTE_MEMORY.clear()
        main.ENABLE_TASK_STICKY = True
        on = main.assign(obs, me, obs["private"], tasks, ZONES, {})
        self.assertEqual(on, off)


if __name__ == "__main__":
    unittest.main()
