"""Validate the NumPy clone against ground truth.

Two levels:
  --prices : unit-test the implemented pure functions (market_price, _shape,
             town_consume, decay_plants) against the installed env's own code.
             Runs today.
  --replay : replay every episode in replays/ through the clone, feeding the
             recorded actions, and assert farm state matches step-by-step.
             Fails until apply_unit_actions / process_market / end_of_day land.

    python -m ml.clone.validate_clone --prices
    python -m ml.clone.validate_clone --replay replays/ --max 5
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

from ml.clone.engine_np import PRODUCTS, market_price


def check_prices():
    from kaggle_environments.envs.kaggriculture import kaggriculture as K
    params = getattr(K, "MARKET_PARAMS", None)
    fn = getattr(K, "market_price", None)
    if fn is None or params is None:
        print("could not find env market_price / MARKET_PARAMS -- "
              "check the installed kaggriculture.py symbol names")
        return 1
    bad = 0
    for item in PRODUCTS:
        for inv in [0, 1, 100, 2500, 9999, 10000, 10001, 12000, 25000, 100000]:
            got = int(market_price(item, np.array([inv]))[0])
            try:
                want = int(fn(item, inv, params[item]))
            except TypeError:
                want = int(fn(item, inv))
            if got != want:
                bad += 1
                print(f"  MISMATCH {item} inv={inv}: clone={got} env={want}")
    print("price curve: OK" if not bad else f"price curve: {bad} mismatches")
    return bad


def check_replay(path):
    print(f"[replay] {os.path.basename(path)} -- "
          "NOT RUNNABLE until apply_unit_actions/process_market/end_of_day land "
          "(see ml/clone/README.md). Skeleton harness below.")
    rep = json.load(open(path, encoding="utf-8"))
    steps = rep.get("steps") or []
    print(f"         {len(steps)} steps, seed={rep.get('info', {}).get('seed')}")
    # TODO: State.reset([seed]); for each step feed steps[i][seat]['action'];
    #       compare st.money / st.market_inv / tile planes to
    #       steps[i+1][seat]['observation']. Report first divergence (step, field).
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", action="store_true")
    ap.add_argument("--replay", nargs="?", const="replays")
    ap.add_argument("--max", type=int, default=3)
    a = ap.parse_args()
    rc = 0
    if a.prices or not a.replay:
        rc += check_prices()
    if a.replay:
        for f in sorted(glob.glob(os.path.join(a.replay, "*.json")))[:a.max]:
            rc += check_replay(f)
    raise SystemExit(1 if rc else 0)


if __name__ == "__main__":
    main()
