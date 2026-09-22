"""v100 CARE_PARITY: standing-on-a-fed-uncared-animal tile does CARE ahead of
COLLECT_FERTILIZER/HARVEST (unless yield_units is already near max_held).
Fixtures follow tests/test_v99_toptemplate.py; module loading follows
tests/test_terminal_workforce.py (importlib by path, not `import main`)."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v100 = load("v100_candidate", "agents/main_v100_careparity.py")


def animal_tile(species="COW", fed_today=True, cared_today=False,
                 fertilizer_available=True, yield_units=0):
    return {"kind": v100.ANIMALS[species][1], "animal": species,
            "fed_today": fed_today, "cared_today": cared_today,
            "fertilizer_available": fertilizer_available,
            "yield_units": yield_units, "consecutive_unfed": 0}


def crew_action(tile, wheat=0, hour=5):
    """Run animal_crew_actions with one crew hand standing on `tile`."""
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[5][5] = tile
    me = {"tiles": tiles}
    private = {"shed": {}, "inventories": [{"WHEAT": wheat}]}
    reserved = [(5, 5)]
    crew_idx = [0]
    positions = [(5, 5)]
    invs = [{"WHEAT": wheat}]
    obs = {"hour": hour}
    out = v100.animal_crew_actions(obs, me, private, reserved, crew_idx,
                                    positions, invs)
    return out.get(0)


class CareParityOnTests(unittest.TestCase):
    def setUp(self):
        self._saved = v100.ENABLE_CARE_PARITY

    def tearDown(self):
        v100.ENABLE_CARE_PARITY = self._saved

    def test_fed_uncared_with_fertilizer_does_care_first(self):
        v100.ENABLE_CARE_PARITY = True
        tile = animal_tile(fed_today=True, cared_today=False,
                            fertilizer_available=True, yield_units=0)
        self.assertEqual(crew_action(tile), ["CARE"])

    def test_near_cap_yield_still_harvests_first(self):
        v100.ENABLE_CARE_PARITY = True
        # COW max_held=6, CARE_NEAR_CAP_MARGIN=1 -> yield_units=5 is near cap.
        tile = animal_tile(fed_today=True, cared_today=False,
                            fertilizer_available=True, yield_units=5)
        self.assertEqual(crew_action(tile), ["HARVEST"])

    def test_already_cared_falls_through_to_fertilizer(self):
        v100.ENABLE_CARE_PARITY = True
        tile = animal_tile(fed_today=True, cared_today=True,
                            fertilizer_available=True, yield_units=0)
        self.assertEqual(crew_action(tile), ["COLLECT_FERTILIZER"])

    def test_not_fed_today_never_cares(self):
        v100.ENABLE_CARE_PARITY = True
        tile = animal_tile(fed_today=False, cared_today=False,
                            fertilizer_available=True, yield_units=0)
        # unfed today with no wheat carried and not at-risk -> no forced
        # on-tile action from this branch (falls through to goal-seeking).
        self.assertNotEqual(crew_action(tile), ["CARE"])


class CareParityOffParityTests(unittest.TestCase):
    """Flag OFF must reproduce the parent's FEED > HARVEST >
    COLLECT_FERTILIZER > CARE ordering exactly (byte-identical action)."""

    def setUp(self):
        self._saved = v100.ENABLE_CARE_PARITY
        v100.ENABLE_CARE_PARITY = False

    def tearDown(self):
        v100.ENABLE_CARE_PARITY = self._saved

    def test_fed_uncared_with_fertilizer_collects_fertilizer(self):
        tile = animal_tile(fed_today=True, cared_today=False,
                            fertilizer_available=True, yield_units=0)
        self.assertEqual(crew_action(tile), ["COLLECT_FERTILIZER"])

    def test_fed_uncared_no_fertilizer_cares_last(self):
        tile = animal_tile(fed_today=True, cared_today=False,
                            fertilizer_available=False, yield_units=0)
        self.assertEqual(crew_action(tile), ["CARE"])

    def test_yield_present_harvests_first(self):
        tile = animal_tile(fed_today=True, cared_today=False,
                            fertilizer_available=True, yield_units=2)
        self.assertEqual(crew_action(tile), ["HARVEST"])


class NeverRaisesTests(unittest.TestCase):
    def _obs(self, day=12, hour=5):
        farm = {
            "money": 5000,
            "tiles": [[None for _ in range(10)] for _ in range(10)],
            "farmer": [4, 4],
            "hands": [],
            "unlocked_quadrants": ["NW"],
            "hires_today": 0,
        }
        return {
            "player": 0,
            "day": day,
            "hour": hour,
            "farms": [farm, {"money": 5000, "tiles": [[None] * 10] * 10,
                              "farmer": [4, 4], "hands": [],
                              "unlocked_quadrants": ["NW"], "hires_today": 0}],
            "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
            "market": {"inventory": {item: 10000 for item in v100.BASE},
                       "prices": dict(v100.BASE)},
            "town": {"unlocked_shops": []},
        }

    def _check(self, obs):
        out = v100.agent(obs)
        self.assertIsInstance(out, dict)
        self.assertIn("farmer", out)
        self.assertIn("hands", out)
        self.assertIn("market", out)

    def test_basic_obs_both_flag_states(self):
        for flag in (True, False):
            v100.ENABLE_CARE_PARITY = flag
            with self.subTest(flag=flag):
                self._check(self._obs())

    def test_empty_obs(self):
        self._check({})

    def test_farms_too_short(self):
        self._check({"player": 0, "farms": [self._obs()["farms"][0]]})


if __name__ == "__main__":
    unittest.main()
