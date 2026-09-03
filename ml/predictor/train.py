"""Train the opponent 5-day sell-volume predictor (one LightGBM model / product).

Group-aware split (by replay) so we don't leak. Exports a *pure-Python* model
dump (``opppred.json``) that ``infer.py`` walks with zero deps -- so it can ride
inside a Kaggle ``main.py``.

    python -m ml.predictor.train --data ml/artifacts/opppred_data.npz --out ml/artifacts/opppred.json
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from ml.predictor.features import FEATURE_NAMES, PRODUCTS


def _split(group, val_frac, seed):
    g = np.unique(group)
    rng = np.random.default_rng(seed)
    rng.shuffle(g)
    n_val = max(1, int(len(g) * val_frac))
    val_g = set(g[:n_val].tolist())
    val_mask = np.array([x in val_g for x in group])
    return ~val_mask, val_mask


def _tree_to_dict(node):
    if "leaf_value" in node:
        return {"v": float(node["leaf_value"])}
    return {
        "f": int(node["split_feature"]),
        "t": float(node["threshold"]),
        # LightGBM: go left when x <= threshold (default_left handles NaN; we have none)
        "l": _tree_to_dict(node["left_child"]),
        "r": _tree_to_dict(node["right_child"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="ml/artifacts/opppred_data.npz")
    ap.add_argument("--out", default="ml/artifacts/opppred.json")
    ap.add_argument("--val-frac", type=float, default=0.25)
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    try:
        import lightgbm as lgb
    except Exception:
        raise SystemExit("pip install lightgbm  (training only; inference is dep-free)")

    d = np.load(args.data, allow_pickle=True)
    X, Y, group = d["X"], d["Y"], d["group"]
    tr, va = _split(group, args.val_frac, args.seed)
    print(f"train rows={tr.sum()} val rows={va.sum()} features={X.shape[1]}")

    models, metrics = {}, {}
    params = dict(objective="regression_l1", num_leaves=31, learning_rate=0.05,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
                  min_data_in_leaf=20, verbose=-1)
    for pi, prod in enumerate(PRODUCTS):
        ytr, yva = Y[tr, pi], Y[va, pi]
        dtr = lgb.Dataset(X[tr], label=ytr)
        dva = lgb.Dataset(X[va], label=yva, reference=dtr)
        booster = lgb.train(params, dtr, num_boost_round=args.rounds,
                            valid_sets=[dva],
                            callbacks=[lgb.early_stopping(30, verbose=False),
                                       lgb.log_evaluation(0)])
        dump = booster.dump_model()
        trees = [_tree_to_dict(t["tree_structure"]) for t in dump["tree_info"]]
        models[prod] = trees
        pred = booster.predict(X[va])
        mae = float(np.mean(np.abs(pred - yva)))
        base = float(np.mean(np.abs(ytr.mean() - yva)))
        metrics[prod] = {"val_mae": round(mae, 3), "baseline_mae": round(base, 3),
                         "n_trees": len(trees), "best_iter": booster.best_iteration}
        print(f"  {prod:11} val MAE {mae:7.3f}  (mean-baseline {base:7.3f})  "
              f"trees {len(trees)}")

    out = {"features": FEATURE_NAMES, "products": PRODUCTS,
           "models": models, "metrics": metrics,
           "init_score": {p: float(Y[tr, i].mean()) for i, p in enumerate(PRODUCTS)}}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"))
    json.dump(metrics, open(os.path.splitext(args.out)[0] + "_metrics.json", "w"), indent=2)
    kb = os.path.getsize(args.out) / 1024
    print(f"\nwrote {args.out} ({kb:.0f} KB). "
          f"{'OK for main.py bundling.' if kb < 500 else 'LARGE -- trim rounds/leaves.'}")
    lift = np.mean([1 - metrics[p]['val_mae'] / max(1e-6, metrics[p]['baseline_mae'])
                    for p in PRODUCTS])
    print(f"mean MAE lift over baseline: {lift:+.1%}  "
          f"({'useful' if lift > 0.1 else 'WEAK -- keep advisory only / get more data'})")


if __name__ == "__main__":
    main()
