"""v99 TOP-TEMPLATE hunks: ENABLE_STR_TRIM, ENABLE_FEED_WHEAT, ENABLE_HERD_BIG,
ENABLE_HERD_STEP_D14. Each test pins one rule of the hunk; the all-flags-OFF
path is checked (synthetic states + a real engine rollout) to stay
byte-identical to agents/main_v78_herdd6.py, the parent this build is stacked
on. Fixtures follow tests/test_v78_herd_fert.py; module loading follows
tests/test_terminal_workforce.py (importlib by path, not `import main`)."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as engine


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v78 = load("v99_parent_v78", "agents/main_v78_herdd6.py")
v99 = load("v99_candidate", "agents/main_v99_toptemplate.py")

V99_FLAGS = ("ENABLE_STR_TRIM", "ENABLE_FEED_WHEAT", "ENABLE_HERD_BIG",
             "ENABLE_HERD_STEP_D14")


def all_off(module):
    for f in V99_FLAGS:
        setattr(module, f, False)


def farm(quadrants=("NW",), money=5000, hands=()):
    return {
        "money": money,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "farmer": [4, 4],
        "hands": [list(h) for h in hands],
        "unlocked_quadrants": list(quadrants),
        "hires_today": 0,
    }


def observation(day=12, hour=5, shops=(), quadrants=("NW",), money=5000, module=v99):
    return {
        "player": 0,
        "day": day,
        "hour": hour,
        "farms": [farm(quadrants, money), farm()],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {item: 10000 for item in module.BASE},
                   "prices": dict(module.BASE)},
        "town": {"unlocked_shops": list(shops)},
    }


def place_animals(me, species, n, start=0):
    """Mark `n` tiles on row 4.. as a placed animal of `species`, starting at
    flat index `start` (10-wide grid, matches the farm() fixture)."""
    for i in range(start, start + n):
        me["tiles"][i // 10][i % 10] = {"kind": "PASTURE" if species != "GOOSE" else "COOP",
                                         "animal": species, "fed_today": True}


class FlagCase(unittest.TestCase):
    """Base for tests against the v99 candidate module only."""

    def setUp(self):
        self._saved = {f: getattr(v99, f) for f in V99_FLAGS}

    def tearDown(self):
        for f, v in self._saved.items():
            setattr(v99, f, v)


class OffPathParityTests(unittest.TestCase):
    """All 4 flags False -> v99 must reproduce agents/main_v78_herdd6.py."""

    def setUp(self):
        all_off(v99)
        v78._ROUTE_MEMORY.clear()
        v99._ROUTE_MEMORY.clear()

    def test_off_path_identical_to_v78_across_days(self):
        cases = [
            dict(day=0, hour=0, quadrants=("NW",)),
            dict(day=8, hour=3, quadrants=("NW", "NE")),
            dict(day=12, hour=5, quadrants=("NW", "NE", "SW")),
            dict(day=20, hour=10, quadrants=("NW", "NE", "SW")),
            dict(day=28, hour=15, quadrants=("NW", "NE", "SW", "SE")),
        ]
        for kwargs in cases:
            with self.subTest(**kwargs):
                obs78 = observation(module=v78, **kwargs)
                obs99 = observation(module=v99, **kwargs)
                # give both farms an identical 13-animal herd so the ported
                # hunks' guard conditions (nq >= 3, placed_total, ...) are
                # actually exercised on the OFF path, not just skipped idle.
                place_animals(obs78["farms"][0], "COW", 13)
                place_animals(obs99["farms"][0], "COW", 13)
                v78._ROUTE_MEMORY.clear()
                v99._ROUTE_MEMORY.clear()
                self.assertEqual(v78.agent(obs78), v99.agent(obs99))

    def test_off_path_full_engine_rollout_identical_actions(self):
        """Run one real game (kaggle_environments engine) and feed both
        modules the same evolving state, applying v78's action every step so
        the two farms track identically -- if v99's OFF path ever diverged
        the actions (and hence the applied state) would diverge too."""
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
        env.reset(num_agents=2)
        state = copy.deepcopy(env.state)
        runtime = SimpleNamespace(configuration=env.configuration, done=False,
                                   info={"seed": 210921})
        v78._ROUTE_MEMORY.clear()
        v99._ROUTE_MEMORY.clear()
        steps = 60  # ~2.5 days: enough to cross the quadrant-2/day-7+ boundaries
        for _ in range(steps):
            obs = state[0].observation
            a78 = v78.agent(obs)
            a99 = v99.agent(obs)
            self.assertEqual(a78, a99)
            state[0].action = a78
            state[1].action = {"farmer": ["PASS"], "hands": [], "market": []}
            engine.interpreter(state, runtime)
            if state[0].status == "DONE":
                break


class NeverRaisesTests(unittest.TestCase):
    def _check(self, obs):
        out = v99.agent(obs)
        self.assertIsInstance(out, dict)
        self.assertIn("farmer", out)
        self.assertIn("hands", out)
        self.assertIn("market", out)

    def test_empty_obs(self):
        self._check({})

    def test_farms_too_short(self):
        self._check({"player": 0, "farms": [farm()]})

    def test_missing_market_and_private(self):
        self._check({"player": 0, "day": 5, "hour": 2,
                      "farms": [farm(), farm()]})

    def test_four_quadrants_full_shed(self):
        obs = observation(day=20, quadrants=("NW", "NE", "SW", "SE"))
        obs["private"]["shed"] = {item: v99.SHED_CAP for item in v99.BASE}
        place_animals(obs["farms"][0], "COW", 13)
        self._check(obs)

    def test_malformed_tiles(self):
        obs = observation(day=10)
        obs["farms"][0]["tiles"] = None
        self._check(obs)


class StrTrimTests(FlagCase):
    # MELON already at its own 5-tile cap so it can't out-rank STRAWBERRY and
    # mask the trim -- isolates the STR_TRIM effect on the value loop.
    def test_caps_at_31_when_on(self):
        v99.ENABLE_STR_TRIM = True
        obs = observation(day=12)
        counts = v99.Counter({"STRAWBERRY": 30, "MELON": 5})
        picks = v99.choose_crops(obs, obs["farms"][0], obs["private"], counts, 5)
        self.assertLessEqual(picks.count("STRAWBERRY"), 1)

    def test_off_allows_more(self):
        v99.ENABLE_STR_TRIM = False
        obs = observation(day=12)
        counts = v99.Counter({"STRAWBERRY": 30, "MELON": 5})
        picks = v99.choose_crops(obs, obs["farms"][0], obs["private"], counts, 5)
        self.assertGreater(picks.count("STRAWBERRY"), 1)


class FeedWheatTests(FlagCase):
    def test_quota_tracks_placed_herd(self):
        v99.ENABLE_FEED_WHEAT = True
        obs = observation(day=12)
        place_animals(obs["farms"][0], "COW", 15)
        picks = v99.choose_crops(obs, obs["farms"][0], obs["private"], v99.Counter(), 20)
        self.assertEqual(picks[:15], ["WHEAT"] * 15)

    def test_quota_caps_at_feed_wheat_max(self):
        v99.ENABLE_FEED_WHEAT = True
        obs = observation(day=12)
        place_animals(obs["farms"][0], "COW", 25)
        picks = v99.choose_crops(obs, obs["farms"][0], obs["private"], v99.Counter(), 20)
        self.assertEqual(picks[:v99.FEED_WHEAT_MAX], ["WHEAT"] * v99.FEED_WHEAT_MAX)
        # the quota itself never exceeds the named cap, even with more animals.
        wheat_run = 0
        for p in picks:
            if p != "WHEAT":
                break
            wheat_run += 1
        self.assertLessEqual(wheat_run, v99.FEED_WHEAT_MAX)

    def test_off_does_not_force_wheat(self):
        v99.ENABLE_FEED_WHEAT = False
        obs = observation(day=12)
        place_animals(obs["farms"][0], "COW", 15)
        picks = v99.choose_crops(obs, obs["farms"][0], obs["private"], v99.Counter(), 20)
        self.assertNotEqual(picks[:15], ["WHEAT"] * 15)


class HerdBigTests(FlagCase):
    def test_targets_17_no_goose(self):
        v99.ENABLE_HERD_BIG = True
        obs = observation(day=11, quadrants=("NW", "NE", "SW"))
        tgt = v99.animal_targets(obs, obs["farms"][0])
        self.assertEqual(sum(tgt.values()), 17)
        self.assertEqual(tgt.get("GOOSE", 0), 0)

    def test_off_keeps_incumbent_cap(self):
        v99.ENABLE_HERD_BIG = False
        obs = observation(day=11, quadrants=("NW", "NE", "SW"))
        tgt = v99.animal_targets(obs, obs["farms"][0])
        self.assertLess(sum(tgt.values()), 17)


class HerdStepD14Tests(FlagCase):
    def _buys(self, day, money, placed=13, quadrants=("NW", "NE", "SW")):
        obs = observation(day=day, hour=2, quadrants=quadrants, money=money)
        me = obs["farms"][0]
        place_animals(me, "COW", placed)
        orders = v99.market_orders(obs, me, obs["private"], v99.Counter(), 8)
        return [o for o in orders if o and o[0] == "BUY_ANIMAL"]

    def test_relaxes_reserve_inside_window(self):
        v99.ENABLE_HERD_BIG = True
        v99.ENABLE_HERD_STEP_D14 = True
        self.assertTrue(self._buys(day=12, money=1500))

    def test_no_relax_outside_window(self):
        v99.ENABLE_HERD_BIG = True
        v99.ENABLE_HERD_STEP_D14 = True
        self.assertEqual(self._buys(day=15, money=1500), [])

    def test_no_relax_when_flag_off(self):
        v99.ENABLE_HERD_BIG = True
        v99.ENABLE_HERD_STEP_D14 = False
        self.assertEqual(self._buys(day=12, money=1500), [])

    def test_herd_big_without_step_does_not_buy(self):
        """Regression for B56: raising the cap alone (no funding relax) must
        not buy past the reserve gate -- otherwise this reproduces the
        -2.5k/game lone-atom failure inside the stack."""
        v99.ENABLE_HERD_BIG = True
        v99.ENABLE_HERD_STEP_D14 = False
        self.assertEqual(self._buys(day=12, money=1500, placed=13), [])


class OrderCountTests(unittest.TestCase):
    def test_orders_le_10_in_rollout(self):
        for f in V99_FLAGS:
            setattr(v99, f, True)
        v99._ROUTE_MEMORY.clear()
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
        env.reset(num_agents=2)
        state = copy.deepcopy(env.state)
        runtime = SimpleNamespace(configuration=env.configuration, done=False,
                                   info={"seed": 921099})
        for _ in range(40):
            obs = state[0].observation
            action = v99.agent(obs)
            self.assertLessEqual(len(action["market"]), 10)
            state[0].action = action
            state[1].action = {"farmer": ["PASS"], "hands": [], "market": []}
            engine.interpreter(state, runtime)
            if state[0].status == "DONE":
                break


if __name__ == "__main__":
    unittest.main()
