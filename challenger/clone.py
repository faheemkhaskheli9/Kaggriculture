"""Behaviour-cloning *cadence* controller for the challenger (IMPACT plan §8,
Workstream A).

Scope, deliberately narrow: the held-out benchmark
(`ml/artifacts/top_policy_benchmark.json`, `tools/benchmark_top_policy.py`) shows
only a few strategic action *families* are learnable from public state --
HIRE (F1 0.77), SELL (0.50), BUY_SEED (0.50); BUY_LAND / BUY_ANIMAL are noise
(<0.07) and stay as explicit rules elsewhere. So this module trains one binary
NB per family and exposes, per turn, "does a top player act on family X here?"
-- a *timing* signal to gate the incumbent's own order assembly, never a
replacement for it.

Two entry points:

* ``train(dataset) -> dict`` and ``python -m challenger.clone`` -- fit + calibrate
  + serialise to ``challenger/clone_model.json`` and print a held-out check that
  must track the benchmark (family micro-F1 ~0.42, HIRE ~0.77).
* ``CadenceModel.load()`` + ``.active_families(feat)`` -- dependency-free
  inference for use inside ``challenger/agent.py``. ``feat`` is the binned
  feature dict from ``feature_row()`` (replay rows) or, at run time,
  ``live_features()`` (kaggle obs) -- both must produce identical keys.

The feature binning here is a verbatim copy of the benchmark's ``features()`` so
train-time and the benchmark stay in lockstep; a divergence there silently
invalidates every reported number.
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "ml" / "artifacts" / "top_policy.jsonl"
MODEL_PATH = Path(__file__).resolve().parent / "clone_model.json"

FAMILIES = ("HIRE", "BUY_SEED", "SELL")  # the learnable subset; see module docstring
_ALL_FAMILIES = ("HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "SELL")


# --------------------------------------------------------------------------- #
# feature binning -- keep byte-identical to tools/benchmark_top_policy.features
# --------------------------------------------------------------------------- #
def _bin(value, cuts):
    value = float(value or 0)
    for index, cut in enumerate(cuts):
        if value < cut:
            return str(index)
    return str(len(cuts))


def _total(mapping):
    return sum((mapping or {}).values())


def feature_row(row):
    """Binned feature dict from a `top_policy.jsonl` replay row."""
    farm = row["farm"]
    opponent = row["opponent"]
    prices = row.get("market_prices") or {}
    history = row.get("history") or {}
    counts = history.get("market_counts") or {}
    quantities = history.get("market_quantities") or {}
    since = history.get("turns_since") or {}
    return {
        "agent": row.get("agent", "UNKNOWN"),
        "day": _bin(row["day"], (2, 5, 8, 12, 16, 21, 26, 29)),
        "hour": _bin(row["hour"], (1, 4, 8, 12, 16, 20, 23)),
        "money": _bin(row["money"], (50, 150, 400, 800, 1500, 3000, 6000, 12000, 25000, 50000)),
        "hands": _bin(row["hands"], (2, 5, 8, 11, 14, 18)),
        "quadrants": str(row["quadrants"]),
        "plants": _bin(_total(farm["crops"]), (5, 15, 30, 50, 70)),
        "animals": _bin(_total(farm["animals"]), (1, 4, 8, 12, 16)),
        "empty": _bin(farm["empty"], (3, 10, 20, 40)),
        "weeds": _bin(farm["weeds"], (1, 5, 15, 30)),
        "opp_plants": _bin(_total(opponent["crops"]), (5, 15, 30, 50, 70)),
        "opp_animals": _bin(_total(opponent["animals"]), (1, 4, 8, 12, 16)),
        "shed": _bin(_total(row.get("shed")), (1, 10, 30, 60, 90)),
        "seeds": _bin(_total(row.get("seeds")), (1, 5, 15, 30)),
        "carried": _bin(_total(row.get("carried")), (1, 5, 15, 30)),
        "wheat_price": _bin(prices.get("WHEAT"), (15, 22, 28, 40, 60)),
        "strawberry_price": _bin(prices.get("STRAWBERRY"), (80, 120, 160, 220, 300)),
        "milk_price": _bin(prices.get("MILK"), (100, 160, 220, 320)),
        "wool_price": _bin(prices.get("WOOL"), (120, 200, 300, 450)),
        "shops": _bin(len(row.get("town_shops") or []), (1, 3, 6, 9)),
        "hires_so_far": _bin(counts.get("HIRE"), (5, 20, 50, 100, 180, 260)),
        "land_buys_so_far": str(min(3, int(counts.get("BUY_LAND", 0)))),
        "seed_units_so_far": _bin(quantities.get("BUY_SEED"), (10, 40, 100, 250, 500, 900)),
        "animals_so_far": _bin(quantities.get("BUY_ANIMAL"), (1, 4, 8, 12, 18)),
        "products_bought_so_far": _bin(quantities.get("BUY_PRODUCT"), (5, 20, 60, 150, 300)),
        "sell_units_so_far": _bin(quantities.get("SELL"), (10, 50, 150, 400, 800)),
        "since_hire": _bin(since.get("HIRE", 999), (1, 2, 4, 8, 16, 24, 48)),
        "since_land": _bin(since.get("BUY_LAND", 999), (1, 6, 24, 72, 144, 288)),
        "since_seed": _bin(since.get("BUY_SEED", 999), (1, 2, 6, 12, 24, 48)),
        "since_animal": _bin(since.get("BUY_ANIMAL", 999), (1, 4, 12, 24, 48, 96)),
        "since_product": _bin(since.get("BUY_PRODUCT", 999), (1, 2, 6, 12, 24, 48)),
        "since_sell": _bin(since.get("SELL", 999), (1, 2, 4, 8, 16, 24)),
        "previous_day_money": _bin(history.get("previous_day_money"),
                                   (50, 150, 400, 800, 1500, 3000, 6000, 12000, 25000)),
        "previous_day_plants": _bin(history.get("previous_day_plants"), (5, 15, 30, 50, 70)),
        "previous_day_animals": _bin(history.get("previous_day_animals"), (1, 4, 8, 12, 16)),
    }


def label_set(row):
    out = set()
    for order in row["labels"]["market_orders"]:
        op = order[0]
        if op in _ALL_FAMILIES:
            out.add(op)
    return out


# --------------------------------------------------------------------------- #
# training
# --------------------------------------------------------------------------- #
class _NB:
    def __init__(self):
        self.class_counts = Counter()
        self.values = defaultdict(set)
        self.counts = {False: defaultdict(Counter), True: defaultdict(Counter)}

    def fit(self, rows, target):
        for feat, labs in rows:
            sel = target in labs
            self.class_counts[sel] += 1
            for name, value in feat.items():
                self.values[name].add(value)
                self.counts[sel][name][value] += 1

    def probability(self, feat):
        total_rows = sum(self.class_counts.values())
        logp = {}
        for sel in (False, True):
            lv = math.log((self.class_counts[sel] + 1) / (total_rows + 2))
            for name, value in feat.items():
                width = len(self.values[name]) + 1
                num = self.counts[sel][name][value] + 1
                den = self.class_counts[sel] + width
                lv += math.log(num / den)
            logp[sel] = lv
        scale = max(logp.values())
        yes, no = math.exp(logp[True] - scale), math.exp(logp[False] - scale)
        return yes / (yes + no)

    def to_json(self):
        return {
            "class_counts": {"true": self.class_counts[True],
                             "false": self.class_counts[False]},
            "values": {k: sorted(v) for k, v in self.values.items()},
            "cond": {
                "true": {k: dict(v) for k, v in self.counts[True].items()},
                "false": {k: dict(v) for k, v in self.counts[False].items()},
            },
        }


def _f1(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return (2 * p * r / (p + r)) if p + r else 0.0, p, r


def _best_threshold(model, calib, target):
    scored = [(model.probability(f), target in l) for f, l in calib]
    best = (0.0, 0.5)
    for i in range(5, 96, 5):
        t = i / 100
        tp = sum(pr >= t and a for pr, a in scored)
        fp = sum(pr >= t and not a for pr, a in scored)
        fn = sum(pr < t and a for pr, a in scored)
        s = _f1(tp, fp, fn)[0]
        if s > best[0] or (s == best[0] and t > best[1]):
            best = (s, t)
    return best[1]


def _load_rows(dataset):
    rows = []
    with Path(dataset).open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            rows.append((r["episode_id"], feature_row(r), label_set(r)))
    return rows


def train(dataset=DATASET, split_seed=20260905, validation_fraction=0.25,
          model_path=MODEL_PATH, verbose=True):
    """Fit + calibrate on an episode-held-out split, serialise, return a report."""
    rows = _load_rows(dataset)
    episodes = sorted({e for e, _, _ in rows})
    rng = random.Random(split_seed)
    rng.shuffle(episodes)
    n_val = max(1, round(len(episodes) * validation_fraction))
    val_ep = set(episodes[:n_val])
    train_rows = [(f, l) for e, f, l in rows if e not in val_ep]
    val_rows = [(f, l) for e, f, l in rows if e in val_ep]

    # calibrate thresholds on the last 1/5 of *training* episodes only
    train_ep = sorted(set(episodes) - val_ep)
    calib_ep = set(train_ep[-max(1, len(train_ep) // 5):])
    fit_rows = [(f, l) for e, f, l in rows if e not in val_ep and e not in calib_ep]
    calib_rows = [(f, l) for e, f, l in rows if e in calib_ep]

    models, thresholds = {}, {}
    for fam in FAMILIES:
        cal_model = _NB()
        cal_model.fit(fit_rows, fam)
        thresholds[fam] = _best_threshold(cal_model, calib_rows, fam)
        full = _NB()
        full.fit(train_rows, fam)
        models[fam] = full

    # held-out evaluation
    per_label, micro = {}, Counter()
    for fam in FAMILIES:
        tp = fp = fn = 0
        for f, l in val_rows:
            guess = models[fam].probability(f) >= thresholds[fam]
            actual = fam in l
            tp += guess and actual
            fp += guess and not actual
            fn += (not guess) and actual
        s, p, r = _f1(tp, fp, fn)
        per_label[fam] = {"support": tp + fn, "precision": p, "recall": r,
                          "f1": s, "threshold": thresholds[fam]}
        micro.update(tp=tp, fp=fp, fn=fn)
    micro_f1 = _f1(micro["tp"], micro["fp"], micro["fn"])[0]

    artifact = {
        "dataset": str(Path(dataset).relative_to(ROOT)) if Path(dataset).is_absolute()
        else str(dataset),
        "split_seed": split_seed,
        "families": list(FAMILIES),
        "thresholds": thresholds,
        "feature_keys": sorted(feature_row(json.loads(
            next(Path(dataset).open(encoding="utf-8")))).keys()),
        "models": {fam: models[fam].to_json() for fam in FAMILIES},
        "heldout": {"validation_episodes": sorted(val_ep),
                    "validation_rows": len(val_rows),
                    "micro_f1": micro_f1, "per_label": per_label},
    }
    Path(model_path).write_text(json.dumps(artifact), encoding="utf-8")
    if verbose:
        print(json.dumps({"model_path": str(model_path),
                          "validation_rows": len(val_rows),
                          "family_micro_f1": round(micro_f1, 4),
                          "per_label": {k: {m: round(v[m], 4) for m in
                                            ("f1", "precision", "recall", "threshold")}
                                        for k, v in per_label.items()}}, indent=2))
    return artifact


# --------------------------------------------------------------------------- #
# inference (dependency-free; safe to import inside the agent)
# --------------------------------------------------------------------------- #
class CadenceModel:
    def __init__(self, artifact):
        self.families = list(artifact["families"])
        self.thresholds = artifact["thresholds"]
        self.feature_keys = artifact.get("feature_keys")
        self._m = {}
        for fam, mj in artifact["models"].items():
            ct = mj["class_counts"]
            self._m[fam] = {
                "n_true": ct["true"], "n_false": ct["false"],
                "total": ct["true"] + ct["false"],
                "values": {k: set(v) for k, v in mj["values"].items()},
                "cond": {True: mj["cond"]["true"], False: mj["cond"]["false"]},
            }

    @classmethod
    def load(cls, path=MODEL_PATH):
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return None

    def _prob(self, fam, feat):
        m = self._m[fam]
        out = {}
        for sel in (False, True):
            n_sel = m["n_true"] if sel else m["n_false"]
            lv = math.log((n_sel + 1) / (m["total"] + 2))
            cond = m["cond"][sel]
            for name, value in feat.items():
                width = len(m["values"].get(name, ())) + 1
                num = cond.get(name, {}).get(value, 0) + 1
                lv += math.log(num / (n_sel + width))
            out[sel] = lv
        scale = max(out.values())
        yes, no = math.exp(out[True] - scale), math.exp(out[False] - scale)
        return yes / (yes + no)

    def scores(self, feat):
        return {fam: self._prob(fam, feat) for fam in self.families}

    def active_families(self, feat):
        """Set of families a top player is predicted to act on in this state."""
        return {fam for fam in self.families
                if self._prob(fam, feat) >= self.thresholds[fam]}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(DATASET))
    ap.add_argument("--split-seed", type=int, default=20260905)
    _a = ap.parse_args()
    train(_a.dataset, split_seed=_a.split_seed)
