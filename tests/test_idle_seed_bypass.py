"""ENABLE_IDLE_SEED_BYPASS (Lever M1): cheap WHEAT seeds for tiles the reserve ramp leaves idle."""
import unittest
from collections import Counter

import main

SHED = main.SHED_TILES


def farm(money, plants, animals, idle, quads=("NW", "NE")):
    """NW+NE unlocked (y<5), SW/SE LOCKED. `plants` PLANT tiles, `animals` PASTURE
    tiles with a COW, `idle` None tiles; the rest of the unlocked tiles are
    filled with weeds so the empty count is exact."""
    tiles = [["LOCKED" for _ in range(10)] for _ in range(10)]
    cells = [(x, y) for y in range(5) for x in range(10) if (x, y) not in SHED]
    for (x, y) in SHED:
        tiles[y][x] = None
    todo = (["PLANT"] * plants + ["ANIMAL"] * animals + [None] * idle)
    todo += ["WEED"] * (len(cells) - len(todo))
    for (x, y), kind in zip(cells, todo):
        if kind == "PLANT":
            tiles[y][x] = {"kind": "PLANT", "crop": "WHEAT", "watered_today": True}
        elif kind == "ANIMAL":
            tiles[y][x] = {"kind": "PASTURE", "animal": "COW", "fed_today": True}
        elif kind == "WEED":
            tiles[y][x] = {"kind": "WEED"}
        else:
            tiles[y][x] = None
    return {"money": money, "tiles": tiles, "farmer": [4, 4], "hands": [[4, 5]] * 7,
            "unlocked_quadrants": list(quads), "hires_today": 8}


def observation(day, hour, money, plants=28, animals=4, idle=14, seeds=None, shed=None):
    inventory = {item: 10000 for item in main.BASE}
    return {
        "player": 0, "day": day, "hour": hour,
        "farms": [farm(money, plants, animals, idle), farm(600, 20, 4, 10)],
        "private": {"shed": dict(shed or {"WHEAT": 3}), "seeds": dict(seeds or {}),
                    "inventories": [{}] * 8},
        "market": {"inventory": inventory,
                   "prices": {item: main.price_at(item, inventory[item]) for item in main.BASE}},
        "town": {"unlocked_shops": ["FARMERS_MARKET", "PET_CAFE"]},
    }


def orders(obs, flag):
    saved = main.ENABLE_IDLE_SEED_BYPASS
    main.ENABLE_IDLE_SEED_BYPASS = flag
    try:
        me = obs["farms"][0]
        return main.market_orders(obs, me, obs["private"], main.field_counts(me), 8)
    finally:
        main.ENABLE_IDLE_SEED_BYPASS = saved


def seed_orders(out):
    return Counter({o[1]: int(o[2]) for o in out if o[0] == "BUY_SEED"})


class IdleSeedBypassMarketTests(unittest.TestCase):
    # `109713885` day 7 hour 3: money 225 after feed, 4 animals, 14-15 idle
    # tiles in 2 quadrants, reserve ramp 1,250 -> zero seeds bought all day.
    def test_off_reserve_blocks_every_seed_in_the_crater(self):
        out = orders(observation(7, 3, 225), False)
        self.assertEqual(sum(seed_orders(out).values()), 0)

    def test_on_buys_wheat_for_the_shortfall_down_to_the_feed_floor(self):
        obs = observation(7, 3, 225)
        out = orders(obs, True)
        so = seed_orders(out)
        self.assertEqual(set(so), {"WHEAT"})
        b = so["WHEAT"]
        short = main._idle_seed_shortfall(obs, obs["farms"][0], {})
        self.assertGreaterEqual(short, main.IDLE_SEED_BYPASS_MIN_IDLE)
        self.assertLessEqual(b, short)
        wp = main.price_at("WHEAT", 10000)
        floor = max(main.IDLE_SEED_BYPASS_FLOOR, 4 * wp)
        self.assertGreaterEqual(225 - 10 * b, floor)
        self.assertLess(225 - 10 * (b + 1), floor)      # bought as much as the floor allows

    def test_shortfall_excludes_shed_animal_reservations_and_seeds_on_hand(self):
        obs = observation(7, 3, 225, seeds={"STRAWBERRY": 4})
        me = obs["farms"][0]
        raw = sum(1 for y, row in enumerate(me["tiles"]) for x, t in enumerate(row)
                  if t is None and (x, y) not in SHED)
        self.assertEqual(raw, 14)
        short = main._idle_seed_shortfall(obs, me, obs["private"]["seeds"])
        reserved = max(0, sum(main.animal_targets(obs, me).values()) - 4)
        self.assertEqual(short, 14 - reserved - 4)

    def test_feed_floor_scales_with_the_herd(self):
        # 8 animals: one day of feed (8 * wheat price) exceeds the cash -> no buy
        out = orders(observation(7, 3, 200, plants=24, animals=8, idle=14), True)
        self.assertEqual(seed_orders(out)["WHEAT"], 0)

    def test_no_bypass_when_few_tiles_idle(self):
        out = orders(observation(7, 3, 225, plants=38, idle=4), True)
        self.assertEqual(sum(seed_orders(out).values()), 0)

    def test_no_bypass_after_last_day_or_when_seeds_already_bought(self):
        out = orders(observation(13, 3, 225), True)
        self.assertEqual(sum(seed_orders(out).values()), 0)
        # plenty of cash: the normal loop funds the chooser's picks, bypass stays out
        rich_on = seed_orders(orders(observation(7, 3, 6000), True))
        rich_off = seed_orders(orders(observation(7, 3, 6000), False))
        self.assertEqual(rich_on, rich_off)
        self.assertGreater(sum(rich_off.values()), 0)


class IdleSeedBypassPlantTests(unittest.TestCase):
    def tasks(self, flag, seeds, picks):
        saved_flag, saved_choose = main.ENABLE_IDLE_SEED_BYPASS, main.choose_crops
        main.ENABLE_IDLE_SEED_BYPASS = flag
        main.choose_crops = lambda obs, me, private, counts, n, intent=None: list(picks)[:n]
        try:
            obs = observation(7, 5, 125, seeds=seeds)
            me = obs["farms"][0]
            tasks = []
            main.add_plant_tasks(obs, me, obs["private"], main.field_counts(me), tasks, 8)
            return [t for t in tasks if t[2][0] == "PLANT"]
        finally:
            main.ENABLE_IDLE_SEED_BYPASS, main.choose_crops = saved_flag, saved_choose

    def test_off_leaves_wheat_seeds_in_the_shed_when_picks_are_strawberry(self):
        self.assertEqual(self.tasks(False, {"WHEAT": 10}, ["STRAWBERRY"] * 30), [])

    def test_on_plants_leftover_wheat_on_uncovered_empty_tiles(self):
        got = self.tasks(True, {"WHEAT": 10}, ["STRAWBERRY"] * 30)
        self.assertEqual(len(got), 10)
        self.assertTrue(all(t[2] == ["PLANT", "WHEAT"] for t in got))
        self.assertEqual(len({t[1] for t in got}), 10)          # distinct tiles

    def test_on_does_not_double_book_tiles_the_picks_covered(self):
        got = self.tasks(True, {"STRAWBERRY": 3, "WHEAT": 4}, ["STRAWBERRY"] * 3 + ["WHEAT"] * 30)
        crops = Counter(t[2][1] for t in got)
        self.assertEqual(crops["STRAWBERRY"], 3)
        self.assertEqual(crops["WHEAT"], 4)
        self.assertEqual(len({t[1] for t in got}), 7)

    def test_on_plants_other_leftover_seeds_after_wheat_within_plant_by(self):
        got = self.tasks(True, {"WHEAT": 2, "CARROT": 3, "MELON": 1}, ["STRAWBERRY"] * 30)
        self.assertEqual([t[2][1] for t in got], ["WHEAT", "WHEAT", "CARROT", "CARROT", "CARROT", "MELON"])
        self.assertEqual(len({t[1] for t in got}), 6)

    def test_on_is_a_no_op_after_the_last_day(self):
        saved = main.ENABLE_IDLE_SEED_BYPASS
        main.ENABLE_IDLE_SEED_BYPASS = True
        saved_choose = main.choose_crops
        main.choose_crops = lambda obs, me, private, counts, n, intent=None: ["STRAWBERRY"] * n
        try:
            obs = observation(13, 5, 125, seeds={"WHEAT": 10})
            me = obs["farms"][0]
            tasks = []
            main.add_plant_tasks(obs, me, obs["private"], main.field_counts(me), tasks, 8)
            self.assertEqual([t for t in tasks if t[2][0] == "PLANT"], [])
        finally:
            main.ENABLE_IDLE_SEED_BYPASS, main.choose_crops = saved, saved_choose


if __name__ == "__main__":
    unittest.main()
