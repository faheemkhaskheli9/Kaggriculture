"""ENABLE_LATE_CREW: days 27-28 hire the same crew as days 3-26 instead of 8."""
import unittest

import main


def observation(day, hour=0, nq=3):
    farm = {
        "money": 50000,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW", "NE", "SW"][:nq],
        "hires_today": 0,
    }
    obs = {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm, dict(farm)],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {item: 10000 for item in main.BASE},
                   "prices": dict(main.BASE)},
        "town": {"unlocked_shops": []},
    }
    return obs


def hires(day, hour=0, nq=3):
    """HIRE orders over the two dawn turns (hour 0 then hour 1), modelling the
    engine's 10-orders-per-turn cap and hires_today carry-over."""
    total = 0
    for h in (hour, hour + 1) if hour <= 1 else (hour,):
        obs = observation(day, h, nq)
        obs["farms"][0]["hires_today"] = total
        orders = main.market_orders(obs, obs["farms"][0], obs["private"], {}, 1 + total)
        n = sum(1 for o in orders if o and o[0] == "HIRE")
        assert len(orders) <= 10
        total += n
    return total


def full_crew(nq=3):
    want = {1: 7, 2: 10}.get(nq, 13)
    if main.ENABLE_MAXHANDS_12:
        want = min(want, main.MAXHANDS_12_CAP)
    return want


class LateCrewTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_LATE_CREW

    def tearDown(self):
        main.ENABLE_LATE_CREW = self._flag

    def test_off_days_27_28_hire_eight(self):
        main.ENABLE_LATE_CREW = False
        self.assertEqual(hires(27), 8)
        self.assertEqual(hires(28), 8)

    def test_on_days_27_28_hire_full_crew(self):
        main.ENABLE_LATE_CREW = True
        self.assertEqual(hires(27), full_crew())
        self.assertEqual(hires(28), full_crew())

    def test_on_respects_quadrant_ramp(self):
        main.ENABLE_LATE_CREW = True
        self.assertEqual(hires(27, nq=1), full_crew(1))
        self.assertEqual(hires(27, nq=2), full_crew(2))

    def test_day_26_and_29_unchanged(self):
        for flag in (False, True):
            main.ENABLE_LATE_CREW = flag
            self.assertEqual(hires(26), full_crew(), flag)
            self.assertEqual(hires(29), 0, flag)

    def test_hires_only_at_dawn(self):
        main.ENABLE_LATE_CREW = True
        self.assertEqual(hires(27, hour=5), 0)

    def test_hires_already_made_are_subtracted(self):
        main.ENABLE_LATE_CREW = True
        obs = observation(27)
        obs["farms"][0]["hires_today"] = 5
        orders = main.market_orders(obs, obs["farms"][0], obs["private"], {}, 6)
        self.assertEqual(sum(1 for o in orders if o and o[0] == "HIRE"),
                         full_crew() - 5)


if __name__ == "__main__":
    unittest.main()
