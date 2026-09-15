"""ENABLE_CROP_VALUE_LIFESPAN (Lever C1): ongoing crops yield MAX_YIELD ticks, not a season."""
import unittest

import main


def farm():
    return {
        "money": 5000,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW", "NE"],
        "hires_today": 0,
    }


def observation(day):
    return {
        "player": 0,
        "day": day,
        "hour": 3,
        "farms": [farm(), farm()],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {
            "inventory": {item: 10000 for item in main.BASE},
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": []},
    }


def value(crop, day):
    cost, fy, my, ongoing, _ = main.CROPS[crop]
    val, units = main._crop_tile_value(crop, cost, fy, my, ongoing, 29 - day, main.BASE[crop])
    return val, units


class CropValueLifespanTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_CROP_VALUE_LIFESPAN
        main.ENABLE_CROP_VALUE_LIFESPAN = True

    def tearDown(self):
        main.ENABLE_CROP_VALUE_LIFESPAN = self._flag

    def test_units_capped_at_engine_max_yield(self):
        for crop in ("TOMATO", "STRAWBERRY"):
            _, units = value(crop, 10)
            self.assertEqual(units, main.MAX_YIELD[crop])

    def test_strawberry_beats_tomato_at_day_10_base_prices(self):
        tom, _ = value("TOMATO", 10)
        straw, _ = value("STRAWBERRY", 10)
        self.assertAlmostEqual(tom, (60 * 4 - 50) / 12, places=6)
        self.assertAlmostEqual(straw, (120 * 4 - 100) / 17, places=6)
        self.assertGreater(straw, tom)

    def test_off_path_reproduces_the_tomato_preference(self):
        main.ENABLE_CROP_VALUE_LIFESPAN = False
        tom, tu = value("TOMATO", 10)
        straw, su = value("STRAWBERRY", 10)
        self.assertEqual((tu, su), (12, 5))
        self.assertGreater(tom, straw)

    def test_one_time_crops_unchanged_and_melon_stays_max(self):
        on = {c: value(c, 10)[0] for c in main.CROPS}
        main.ENABLE_CROP_VALUE_LIFESPAN = False
        off = {c: value(c, 10)[0] for c in main.CROPS}
        for c in main.ONE_TIME:
            self.assertEqual(on[c], off[c])
        self.assertEqual(max(on, key=on.get), "MELON")

    def test_choose_crops_day_10_picks_no_tomato(self):
        obs = observation(10)
        picks = main.choose_crops(obs, obs["farms"][0], obs["private"], {}, 8)
        self.assertEqual(len(picks), 8)
        self.assertNotIn("TOMATO", picks)
        self.assertIn("STRAWBERRY", picks)

    def test_choose_crops_day_15_still_allows_tomato(self):
        obs = observation(15)   # STRAWBERRY past plant_by 13
        picks = main.choose_crops(obs, obs["farms"][0], obs["private"], {}, 8)
        self.assertTrue(picks)
        self.assertNotIn("STRAWBERRY", picks)
        self.assertGreater(value("TOMATO", 15)[0], 0)


if __name__ == "__main__":
    unittest.main()
