"""Final-day liquidation checks against the installed game interpreter."""
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


baseline = load("terminal_baseline", "research/baseline_main_20260912.py")
candidate = load("terminal_candidate", "experiments/candidate_top3_terminal.py")


def terminal_state():
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.reset(num_agents=2)
    state = copy.deepcopy(env.state)
    obs = state[0].observation
    obs.day, obs.hour, obs.step = 29, 0, 696
    farm = obs.farms[0]
    farm.money = 10000
    farm.farmer = [4, 4]
    farm.hands = []
    farm.hires_today = 0
    for y in range(5):
        for x in range(5):
            farm.tiles[y][x] = None
    for other in state[1:]:
        other.observation.farms = obs.farms
        other.observation.market = obs.market
        other.observation.town = obs.town
    runtime = SimpleNamespace(configuration=env.configuration, done=False,
                              info={"seed": 123456789})
    return state, runtime


def abundant_state():
    state, runtime = terminal_state()
    farm = state[0].observation.farms[0]
    for y in range(5):
        for x in range(5):
            tile = engine._new_animal("COW", 1)
            tile.update(yield_units=3, fertilizer_available=True,
                        fed_today=False, consecutive_unfed=0)
            farm.tiles[y][x] = tile
    return state, runtime


def finish(module, state, runtime):
    state = copy.deepcopy(state)
    module._ROUTE_MEMORY.clear()
    for hour in range(23):
        obs = state[0].observation
        obs.day, obs.hour, obs.step = 29, hour, 696 + hour
        state[0].action = module.agent(obs)
        state[1].action = {"farmer": ["PASS"], "hands": [], "market": []}
        engine.interpreter(state, runtime)
    return state


class TerminalWorkforceTests(unittest.TestCase):
    def setUp(self):
        candidate.ENABLE_TERMINAL_WORKFORCE = True
        baseline._ROUTE_MEMORY.clear()
        candidate._ROUTE_MEMORY.clear()

    def test_baseline_reproduces_missing_workforce_and_fertilizer(self):
        state, _ = terminal_state()
        obs = state[0].observation
        tile = engine._new_animal("COW", 1)
        tile.update(fertilizer_available=True, yield_units=0)
        obs.farms[0].tiles[3][4] = tile
        tasks, _ = baseline.build_tasks(obs, obs.farms[0], obs.private)
        self.assertEqual([], tasks)
        orders = baseline.agent(obs)["market"]
        self.assertNotIn(["HIRE"], orders)
        self.assertTrue(any(order[0] == "BUY_PRODUCT" for order in orders))
        self.assertEqual(["NORTH"], candidate.agent(obs)["farmer"])

    def test_flag_off_preserves_incumbent_actions(self):
        state, _ = abundant_state()
        candidate.ENABLE_TERMINAL_WORKFORCE = False
        for day in (0, 10, 28, 29):
            for hour in (0, 15, 22):
                with self.subTest(day=day, hour=hour):
                    obs = copy.deepcopy(state[0].observation)
                    obs.day, obs.hour, obs.step = day, hour, day * 24 + hour
                    baseline._ROUTE_MEMORY.clear()
                    candidate._ROUTE_MEMORY.clear()
                    self.assertEqual(baseline.agent(copy.deepcopy(obs)),
                                     candidate.agent(copy.deepcopy(obs)))

    def test_enabled_normal_days_preserve_incumbent_actions(self):
        state, _ = abundant_state()
        for day in (0, 10, 28):
            obs = copy.deepcopy(state[0].observation)
            obs.day, obs.step = day, day * 24
            baseline._ROUTE_MEMORY.clear()
            candidate._ROUTE_MEMORY.clear()
            self.assertEqual(baseline.agent(copy.deepcopy(obs)),
                             candidate.agent(copy.deepcopy(obs)))

    def test_empty_farm_has_no_final_investment(self):
        state, _ = terminal_state()
        self.assertEqual([], candidate.agent(state[0].observation)["market"])

    def test_hiring_respects_cash_and_does_not_buy_feed(self):
        state, _ = abundant_state()
        obs = state[0].observation
        obs.farms[0].money = 3
        orders = candidate.agent(obs)["market"]
        self.assertEqual([["HIRE"], ["HIRE"]], orders)

    def test_last_action_drops_and_sells_in_same_engine_turn(self):
        state, runtime = terminal_state()
        obs = state[0].observation
        obs.hour, obs.step = 22, 718
        obs.private.inventories[0] = {"FERTILIZER": 3}
        cash = obs.farms[0].money
        state[0].action = candidate.agent(obs)
        self.assertEqual(["DROP"], state[0].action["farmer"])
        self.assertIn(["SELL", "FERTILIZER", 3], state[0].action["market"])
        state[1].action = {}
        engine.interpreter(state, runtime)
        self.assertGreater(state[0].reward, cash)
        self.assertEqual(0, sum(obs.private.shed.values()))
        self.assertEqual({}, obs.private.inventories[0])

    def test_harvest_that_cannot_reach_shed_is_rejected(self):
        state, _ = terminal_state()
        obs = state[0].observation
        obs.hour, obs.step = 22, 718
        obs.farms[0].farmer = [0, 0]
        tile = engine._new_plant("WHEAT", 20, 24)
        tile["yield_units"] = 5
        obs.farms[0].tiles[0][0] = tile
        self.assertEqual(["HARVEST"], baseline.agent(obs)["farmer"])
        self.assertEqual(["PASS"], candidate.agent(obs)["farmer"])

    def test_terminal_crew_realizes_positive_net_engine_cash(self):
        state, runtime = abundant_state()
        before = finish(baseline, state, runtime)
        after = finish(candidate, state, runtime)
        self.assertEqual("DONE", after[0].status)
        self.assertGreater(after[0].reward, before[0].reward + 1000)
        self.assertGreater(after[0].reward, 10000)
        self.assertEqual(0, sum(sum(inv.values())
                                for inv in after[0].observation.private.inventories))

    def test_immature_positive_starting_yield_is_not_a_harvest_job(self):
        state, _ = terminal_state()
        obs = state[0].observation
        obs.farms[0].tiles[4][4] = engine._new_plant("MELON", 20, 24)
        self.assertEqual([], candidate._terminal_jobs(obs, obs.farms[0]))

    def test_full_shed_sells_before_delivering_final_cargo(self):
        state, runtime = terminal_state()
        obs = state[0].observation
        obs.hour, obs.step = 21, 717
        obs.private.shed = {"WHEAT": 100}
        obs.private.inventories = [{"FERTILIZER": 3}]
        cash = obs.farms[0]["money"]
        state[0].action = candidate.agent(obs)
        state[1].action = {}
        self.assertEqual(["PASS"], state[0].action["farmer"])
        engine.interpreter(state, runtime)
        self.assertEqual(3, obs.private.inventories[0]["FERTILIZER"])
        obs.hour, obs.step = 22, 718
        state[0].action = candidate.agent(obs)
        self.assertEqual(["DROP"], state[0].action["farmer"])
        engine.interpreter(state, runtime)
        self.assertEqual({}, obs.private.inventories[0])
        self.assertEqual(0, sum(obs.private.shed.values()))
        expected_sales = sum(engine.market_price("WHEAT", 10000 + i)
                             for i in range(100))
        expected_sales += sum(engine.market_price("FERTILIZER", 10000 + i)
                              for i in range(3))
        self.assertEqual(cash + expected_sales, obs.farms[0]["money"])


if __name__ == "__main__":
    unittest.main()
