from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from ml.loop import Lock, load_config, qualifies
from ml.evaluate import fitness, _paired_summary
from ml.optimize import _SpecView
from ml.replay_index import update_index


class ContinuousLearningTests(unittest.TestCase):
    def test_gate_rejects_unsafe_candidate(self):
        report = {
            "errors": 0, "p10_coins": 10_000, "terminal_unsold": 0,
            "ms_step": 1, "mean_score_rate": .6, "plant_deaths": 1,
            "animal_escapes": 0, "market_order_overflow": 0,
            "per_opponent": {"animalfactory_v2": {"score_rate": .6}},
        }
        ok, failures = qualifies(report, {"max_plant_deaths": 0})
        self.assertFalse(ok)
        self.assertTrue(any("plant deaths" in x for x in failures))

    def test_gate_accepts_safe_candidate(self):
        report = {
            "errors": 0, "p10_coins": 10_000, "terminal_unsold": 0,
            "ms_step": 1, "mean_score_rate": .6, "plant_deaths": 0,
            "animal_escapes": 0, "market_order_overflow": 0,
            "per_opponent": {"animalfactory_v2": {"score_rate": .55}},
        }
        ok, failures = qualifies(report, {})
        self.assertTrue(ok, failures)

    def test_gate_requires_credible_paired_improvement(self):
        report = {
            "errors": 0, "p10_coins": 10_000, "terminal_unsold": 0,
            "ms_step": 1, "mean_score_rate": .6, "plant_deaths": 0,
            "animal_escapes": 0, "market_order_overflow": 0,
            "paired": {"score_delta_lcb95": 0.01, "margin_delta": 100},
            "per_opponent": {"animalfactory_v2": {"score_rate": .55}},
        }
        ok, failures = qualifies(report, {"require_paired_improvement": True})
        self.assertTrue(ok, failures)
        report["paired"]["score_delta_lcb95"] = 0.0
        ok, failures = qualifies(report, {"require_paired_improvement": True})
        self.assertFalse(ok)

    def test_paired_summary_uses_matching_jobs(self):
        def row(result, diff, seed):
            return {"opponent": "starter", "seat": 0, "seed": seed,
                    "result": result, "diff": diff}
        summary = _paired_summary(
            [row(1, 10, 1), row(1, 20, 2)],
            [row(-1, -10, 1), row(0, 0, 2)], bootstrap_samples=100)
        self.assertEqual(summary["pairs"], 2)
        self.assertEqual(summary["score_delta"], .75)
        self.assertEqual(summary["margin_delta"], 20)

    def test_optimizer_disqualifies_lifecycle_failures(self):
        report = {
            "errors": 0, "mean_score_rate": .8, "worst_score_rate": .8,
            "mean_coins": 80_000, "p10_coins": 30_000, "baseline_p10": 0,
            "terminal_unsold": 0, "ms_step": 1, "plant_deaths": 0,
            "animal_escapes": 1, "market_order_overflow": 0,
            "per_opponent": {"animalfactory_v2": {"score_rate": .8}},
        }
        self.assertLess(fitness(report), -1.0)

    def test_lock_is_single_instance(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "loop.lock"
            with Lock(path):
                with self.assertRaises(SystemExit):
                    with Lock(path):
                        pass
            self.assertFalse(path.exists())

    def test_focused_animal_space_is_valid_and_smaller(self):
        spec = _SpecView("v7")
        animal = spec.knob_names("animal")
        self.assertTrue(animal)
        self.assertLess(len(animal), len(spec.knob_names("phase2")))
        self.assertEqual(len(animal), len(set(animal)))
        self.assertTrue(all(k in spec.default_params() for k in animal))

    def test_loop_config_has_bounded_windows_workers(self):
        cfg = load_config(Path(__file__).with_name("loop_config.json"))
        self.assertLessEqual(int(cfg["preflight"]["workers"]), 4)
        args = cfg["optimize"]["args"]
        workers = int(args[args.index("--workers") + 1])
        self.assertLessEqual(workers, 4)
        self.assertIn("--screen-games", args)
        self.assertTrue(cfg["gate"]["require_paired_improvement"])

    def test_replay_index_is_incremental(self):
        replay = {"info": {"Agents": [{"Name": "a"}, {"Name": "b"}], "seed": 7},
                  "steps": [[{"reward": 10}, {"reward": 9}]]}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "one.replay.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                json.dump(replay, fh)
            db = root / "index.sqlite3"
            first = update_index([root], db)
            second = update_index([root], db)
            self.assertEqual(first["added"], 1)
            self.assertEqual(second["unchanged"], 1)
            self.assertEqual(second["total"], 1)


if __name__ == "__main__":
    unittest.main()
