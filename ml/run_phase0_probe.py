"""PLAN_ML_MODELS Phase 0 spike: find out what the Kaggle sim runner actually has.

We must not assume ``torch`` / ``scipy`` / ``sklearn`` exist in the episode
runner. This writes a probe submission that, on step 0, prints a JSON blob of:
python version, importability + versions of the libs we might want for
inference, ``os.cpu_count()``, and a rough per-call timing budget. The rest of
the episode it runs a safe wheat loop so the episode completes cleanly.

    python -m ml.run_phase0_probe                 # writes ml/artifacts/probe/main.py
    kaggle competitions submit kaggriculture -f ml/artifacts/probe/main.py -m "env probe"
    # after it plays a validation episode:
    kaggle competitions submissions kaggriculture
    kaggle competitions episodes <SUBMISSION_ID> -v
    kaggle competitions logs <EPISODE_ID> 0 -p ml/artifacts/probe/logs
    python -m ml.run_phase0_probe --parse ml/artifacts/probe/logs/<file>.json

Record the result in PLAN_ML_MODELS.md section 2.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts", "probe")

PROBE_SRC = r'''"""Kaggriculture runtime probe (PLAN_ML_MODELS Phase 0). Safe wheat loop + a
one-time environment dump to stdout, captured by `kaggle competitions logs`."""
import json, sys, time, platform

_PRINTED = False
_LIBS = ["numpy", "scipy", "sklearn", "pandas", "lightgbm", "xgboost",
         "torch", "jax", "numba", "cma", "optuna"]


def _dump():
    info = {"PROBE": "kaggriculture-env", "python": platform.python_version(),
            "executable": sys.executable, "libs": {}}
    for name in _LIBS:
        try:
            m = __import__(name)
            info["libs"][name] = getattr(m, "__version__", "unknown")
        except Exception as e:
            info["libs"][name] = f"MISSING ({type(e).__name__})"
    try:
        import os as _os
        info["cpu_count"] = _os.cpu_count()
    except Exception:
        info["cpu_count"] = None
    t0 = time.perf_counter()
    x = 0.0
    for i in range(200000):
        x += i ** 0.5
    info["loop200k_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    print("PROBE_JSON " + json.dumps(info), flush=True)


def agent(obs):
    global _PRINTED
    if not _PRINTED:
        _PRINTED = True
        try:
            _dump()
        except Exception as e:
            print("PROBE_JSON " + json.dumps({"PROBE": "error", "err": repr(e)}), flush=True)
    try:
        me = obs["farms"][obs["player"]]
        priv = obs.get("private") or {}
        fx, fy = me["farmer"]
        tile = me["tiles"][fy][fx]
        seeds = (priv.get("seeds") or {})
        shed = (priv.get("shed") or {})
        market = []
        if seeds.get("WHEAT", 0) == 0 and me.get("money", 0) >= 10:
            market.append(["BUY_SEED", "WHEAT", 1])
        if shed.get("WHEAT", 0) > 0:
            market.append(["SELL", "WHEAT", int(shed["WHEAT"])])
        hands = me.get("hands", []) or []
        pas = [["PASS"]] * len(hands)
        if tile is None and seeds.get("WHEAT", 0) > 0:
            return {"farmer": ["PLANT", "WHEAT"], "hands": pas, "market": market}
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            age = obs.get("day", 0) - tile.get("planted_day", 0)
            if age >= 2 and tile.get("yield_units", 0) > 0:
                return {"farmer": ["HARVEST"], "hands": pas, "market": market}
            if not tile.get("watered_today"):
                return {"farmer": ["WATER"], "hands": pas, "market": market}
        return {"farmer": ["PASS"], "hands": pas, "market": market}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
'''


def parse(path: str):
    raw = open(path, encoding="utf-8").read()
    try:
        data = json.loads(raw)
        chunks = []
        def walk(x):
            if isinstance(x, str):
                chunks.append(x)
            elif isinstance(x, list):
                for i in x:
                    walk(i)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
        walk(data)
        text = "\n".join(chunks)
    except Exception:
        text = raw
    for line in text.splitlines():
        if "PROBE_JSON" in line:
            blob = line.split("PROBE_JSON", 1)[1].strip()
            try:
                info = json.loads(blob)
            except Exception:
                print("could not parse:", blob)
                continue
            print(json.dumps(info, indent=2))
            libs = info.get("libs", {})
            ok = [k for k, v in libs.items() if not str(v).startswith("MISSING")]
            miss = [k for k, v in libs.items() if str(v).startswith("MISSING")]
            print(f"\navailable : {', '.join(ok)}")
            print(f"missing   : {', '.join(miss)}")
            print("\n-> inference in main.py must use only the 'available' set "
                  "(target: numpy-only, weights from a .npz).")
            return
    print("no PROBE_JSON line found in", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parse", metavar="LOGFILE", help="parse a downloaded logs json")
    args = ap.parse_args()
    if args.parse:
        parse(args.parse)
        return
    os.makedirs(_OUT, exist_ok=True)
    dst = os.path.join(_OUT, "main.py")
    open(dst, "w", encoding="utf-8").write(PROBE_SRC)
    print("wrote", dst)
    print("submit:  kaggle competitions submit kaggriculture -f", dst, "-m 'env probe'")


if __name__ == "__main__":
    main()
