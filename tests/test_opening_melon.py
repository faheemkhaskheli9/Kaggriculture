"""ENABLE_OPENING_MELON (Lever N1): day-0 melon batch, its seed cap, and its sell-down."""
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


def observation(day=0, hour=0, shed=None, seeds=None, money=3000, inventory=None):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(money=money), farm()],
        "private": {
            "shed": dict(shed or {}),
            "seeds": dict(seeds or {}),
            "inventories": [{}],
        },
        "market": {
            "inventory": {item: 10000 for item in main.BASE} | dict(inventory or {}),
            "prices": dict(main.BASE),
        },
        "town": {"unlocked_shops": []},
    }


def picks(obs, counts=None, slots=14):
    me = obs["farms"][0]
    return main.choose_crops(obs, me, obs["private"], dict(counts or {}), slots)


def orders(obs, counts=None, n_units=7):
    me = obs["farms"][0]
    return main.market_orders(obs, me, obs["private"], dict(counts or {}), n_units)


def sell_qty(obs, item):
    return sum(int(o[2]) for o in orders(obs, {}, 11) if o[0] == "SELL" and o[1] == item)


class OpeningMelonTests(unittest.TestCase):
    def setUp(self):
        self._flag = main.ENABLE_OPENING_MELON
        main.ENABLE_OPENING_MELON = True

    def tearDown(self):
        main.ENABLE_OPENING_MELON = self._flag

    # ---- choose_crops ----
    def test_off_week1_has_no_melon(self):
        main.ENABLE_OPENING_MELON = False
        for day in (0, 1, 2):
            self.assertNotIn("MELON", picks(observation(day=day)))
        self.assertIn("TOMATO", picks(observation(day=0), slots=24))

    def test_on_day0_batch_leads_the_picks(self):
        p = picks(observation(day=0), slots=14)
        self.assertEqual(p[:main.OPENING_MELON_TILES], ["MELON"] * main.OPENING_MELON_TILES)
        self.assertEqual(len(p), 14)
        self.assertNotIn("MELON", p[main.OPENING_MELON_TILES:])
        self.assertNotIn("TOMATO", p)
        self.assertTrue(set(p[main.OPENING_MELON_TILES:]) <= {"WHEAT", "CARROT"})

    def test_on_partial_batch_only_tops_up(self):
        p = picks(observation(day=1), counts={"MELON": 9, "WHEAT": 5}, slots=6)
        self.assertEqual(p[:3], ["MELON"] * 3)
        self.assertNotIn("MELON", p[3:])

    def test_on_batch_complete_no_more_melon(self):
        self.assertNotIn("MELON", picks(observation(day=1), counts={"MELON": 12}))

    def test_on_after_last_day_is_the_normal_week1_mix(self):
        p_on = picks(observation(day=main.OPENING_MELON_LAST_DAY + 1), slots=24)
        main.ENABLE_OPENING_MELON = False
        p_off = picks(observation(day=main.OPENING_MELON_LAST_DAY + 1), slots=24)
        self.assertEqual(p_on, p_off)
        self.assertNotIn("MELON", p_on)

    def test_small_slot_count_never_exceeds_slots(self):
        self.assertEqual(picks(observation(day=0), slots=2), ["MELON", "MELON"])

    # ---- seeds ----
    def test_seed_target_capped_at_unplanted_batch(self):
        obs = observation(day=0, hour=3, seeds={"MELON": 10})
        melon = [o for o in orders(obs, {}, 7) if o[0] == "BUY_SEED" and o[1] == "MELON"]
        self.assertEqual(len(melon), 1)
        self.assertEqual(int(melon[0][2]), 2)

    def test_seed_buy_stops_once_batch_is_covered(self):
        obs = observation(day=1, hour=3, seeds={"MELON": 2})
        melon = [o for o in orders(obs, {"MELON": 10}, 7) if o[0] == "BUY_SEED" and o[1] == "MELON"]
        self.assertEqual(melon, [])

    def test_off_seed_orders_have_no_melon(self):
        main.ENABLE_OPENING_MELON = False
        obs = observation(day=0, hour=3)
        self.assertEqual([o for o in orders(obs, {}, 7) if o[0] == "BUY_SEED" and o[1] == "MELON"], [])

    # ---- sells ----
    def test_batch_sells_down_fast_inside_window(self):
        obs = observation(day=12, hour=10, shed={"MELON": 72})
        self.assertEqual(sell_qty(obs, "MELON"), main.OPENING_MELON_SELL_CAP)
        main.ENABLE_OPENING_MELON = False
        self.assertEqual(sell_qty(obs, "MELON"), 6)

    def test_batch_keeps_selling_under_the_premium_floor(self):
        # price ~$150 at +100 inventory: premium rule (keep $200) would hold, N1 (keep $112) sells
        obs = observation(day=13, hour=10, shed={"MELON": 30}, inventory={"MELON": 10100})
        self.assertGreater(sell_qty(obs, "MELON"), 1)
        main.ENABLE_OPENING_MELON = False
        self.assertLessEqual(sell_qty(obs, "MELON"), 1)

    def test_sell_rule_unchanged_after_window(self):
        obs = observation(day=main.OPENING_MELON_SELL_BY + 1, hour=10, shed={"MELON": 30})
        on = sell_qty(obs, "MELON")
        main.ENABLE_OPENING_MELON = False
        self.assertEqual(on, sell_qty(obs, "MELON"))

    def test_other_items_untouched(self):
        obs = observation(day=12, hour=10, shed={"STRAWBERRY": 40, "MILK": 20, "MELON": 72})
        on = {it: sell_qty(obs, it) for it in ("STRAWBERRY", "MILK")}
        main.ENABLE_OPENING_MELON = False
        self.assertEqual(on, {it: sell_qty(obs, it) for it in ("STRAWBERRY", "MILK")})


if __name__ == "__main__":
    unittest.main()
