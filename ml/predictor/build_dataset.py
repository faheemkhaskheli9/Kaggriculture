"""Build the opponent-production training set from downloaded replays.

For every replay in ``replays/``, at each day boundary (hour 0) and for each
seat, we record:
  * features  = the *opponent's* public board + shared market/town state now
  * label     = how many units of each product that opponent SELLs on the
                market over the next ``HORIZON_DAYS`` days

The label is deliberately "sell volume", not "harvest volume": what the
downstream agent needs is how hard the opponent is about to press each price
line, so it can shade its own sells away (PLAN_ML_MODELS section 3C, playbook s7).

    python -m ml.predictor.build_dataset --replays replays --out ml/artifacts/opppred_data.npz
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

from ml.predictor.features import FEATURE_NAMES, PRODUCTS, extract, to_row

TURNS_PER_DAY = 24
HORIZON_DAYS = 5


def _obs_at(steps, i, seat):
    try:
        return steps[i][seat]["observation"]
    except Exception:
        return None


def _sell_units(step_entry) -> dict:
    out = {p: 0 for p in PRODUCTS}
    act = step_entry.get("action") if isinstance(step_entry, dict) else None
    if not isinstance(act, dict):
        return out
    for order in act.get("market") or []:
        if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
            try:
                out[order[1]] = out.get(order[1], 0) + int(order[2])
            except (TypeError, ValueError, KeyError):
                pass
    return out


def process_replay(path: str):
    rep = json.load(open(path, encoding="utf-8"))
    steps = rep.get("steps") or []
    n = len(steps)
    if n < TURNS_PER_DAY * (HORIZON_DAYS + 2):
        return [], []
    rows, labels = [], []
    horizon = HORIZON_DAYS * TURNS_PER_DAY
    for seat in (0, 1):
        opp = 1 - seat
        for i in range(0, n - horizon, TURNS_PER_DAY):
            day = i // TURNS_PER_DAY
            o = _obs_at(steps, i, seat)          # our obs holds both farms + market + town
            if not o:
                continue
            farms = o.get("farms") or []
            if opp >= len(farms):
                continue
            prev = _obs_at(steps, max(0, i - 2 * TURNS_PER_DAY), seat)
            opp_money_prev = None
            if prev and opp < len(prev.get("farms") or []):
                opp_money_prev = float(prev["farms"][opp].get("money", 0))
            feat = extract(farms[opp], o.get("market") or {}, o.get("town") or {},
                           day, opp_money_prev)
            lab = {p: 0 for p in PRODUCTS}
            for j in range(i, min(n, i + horizon)):
                if opp < len(steps[j]):
                    su = _sell_units(steps[j][opp])
                    for p in PRODUCTS:
                        lab[p] += su[p]
            rows.append(to_row(feat))
            labels.append([float(lab[p]) for p in PRODUCTS])
    return rows, labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", default="replays")
    ap.add_argument("--out", default="ml/artifacts/opppred_data.npz")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.replays, "*.json")))
    if not files:
        raise SystemExit(f"no replays under {args.replays}/ -- run download_episodes.py first")
    X, Y, gid = [], [], []
    for k, f in enumerate(files):
        r, l = process_replay(f)
        X.extend(r)
        Y.extend(l)
        gid.extend([k] * len(r))
        print(f"  {os.path.basename(f)}: +{len(r)} rows")
    X = np.asarray(X, np.float32)
    Y = np.asarray(Y, np.float32)
    gid = np.asarray(gid, np.int32)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    np.savez_compressed(args.out, X=X, Y=Y, group=gid,
                        features=np.array(FEATURE_NAMES), products=np.array(PRODUCTS))
    print(f"\nwrote {args.out}: X={X.shape} Y={Y.shape} from {len(files)} replays, "
          f"{len(set(gid.tolist()))} groups")
    if len(X) < 400:
        print("WARNING: small dataset -- the predictor will be weak. Pull more "
              "ladder replays (download_episodes.py) before relying on it.")


if __name__ == "__main__":
    main()
