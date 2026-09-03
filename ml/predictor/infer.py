"""Dependency-free inference for the opponent-production predictor.

Loads ``opppred.json`` (from ``train.py``) and walks the tree dicts in pure
Python -- so this module can be copied into a Kaggle ``main.py`` alongside
``features.py`` with no numpy/lightgbm needed.

    from ml.predictor.infer import Predictor
    pred = Predictor.load("ml/artifacts/opppred.json")
    next5 = pred.predict(opp_farm, market, town, day, opp_money_2days_ago)
    # -> {"WHEAT": 41.2, "MILK": 6.0, ...}  expected opp SELL units, next 5 days
"""
from __future__ import annotations

import json

from ml.predictor.features import PRODUCTS, extract, to_row


def _walk(node, row):
    while "v" not in node:
        node = node["l"] if row[node["f"]] <= node["t"] else node["r"]
    return node["v"]


class Predictor:
    def __init__(self, spec: dict):
        self.features = spec["features"]
        self.products = spec["products"]
        self.models = spec["models"]
        self.init = spec.get("init_score", {p: 0.0 for p in self.products})

    @classmethod
    def load(cls, path: str) -> "Predictor":
        return cls(json.load(open(path, encoding="utf-8")))

    def predict_row(self, row: list) -> dict:
        out = {}
        for p in self.products:
            trees = self.models.get(p, [])
            val = sum(_walk(t, row) for t in trees)
            out[p] = max(0.0, val)
        return out

    def predict(self, opp_farm, market, town, day, opp_money_2days_ago=None) -> dict:
        feat = extract(opp_farm, market, town, day, opp_money_2days_ago)
        return self.predict_row(to_row(feat))


def _selftest(model_path, data_path):
    """Check the pure-Python walk matches LightGBM on held-out rows."""
    import numpy as np
    pred = Predictor.load(model_path)
    d = np.load(data_path, allow_pickle=True)
    X = d["X"]
    idx = np.random.default_rng(0).choice(len(X), min(200, len(X)), replace=False)
    tot = 0.0
    for i in idx:
        r = pred.predict_row(X[i].tolist())
        tot += sum(r.values())
    print(f"self-test ok: mean total predicted sells/5d over {len(idx)} rows = "
          f"{tot/len(idx):.1f}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="ml/artifacts/opppred.json")
    ap.add_argument("--data", default="ml/artifacts/opppred_data.npz")
    a = ap.parse_args()
    _selftest(a.model, a.data)
