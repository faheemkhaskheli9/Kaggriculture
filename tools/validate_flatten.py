"""Validate a flattened single-file agent before it is ever submitted.

Catches two failure modes that a plain `python -c "import x; x.agent(...)"`
smoke test will NOT catch, because Kaggle does not import your file as a
module -- it execs the raw source and takes
`[v for v in namespace.values() if callable(v)][-1]`
(`kaggle_environments/agent.py:get_last_callable`). Reassigning an existing
top-level name (e.g. a second `def agent(...)` after a wrapped module already
defined one) updates its value but does NOT move it to the end of insertion
order, so the callable Kaggle actually picks can silently be some unrelated
helper function instead of your real `agent`. This is what produced
`main_v12.py`'s 123.2 ladder score, not a timeout (see docs/TOP10_TEARDOWN.md
finding 2 / tools/flatten_v12.py for the full root-cause writeup).

    python tools/validate_flatten.py main_v12_flat.py \
        --against main_v12.py --against-dir agents

Checks, in order:
1. The file parses and Kaggle's own `get_last_callable` resolves to a
   function literally named `agent`.
2. `agent` is callable with a single `observation` argument (matches
   Kaggle's calling convention after its argcount-based arg slicing).
3. If `--against` is given, runs a full local game comparing the flattened
   file's action (via `get_last_callable`, the real Kaggle path) against the
   reference module's `agent()` on every observation -- 0 mismatches
   required.
"""
import argparse
import copy
import importlib.util
import sys
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable


def load_via_kaggle(path: str):
    raw = Path(path).read_text(encoding="utf-8")
    fn = get_last_callable(raw, path=path)
    return fn


def load_module(path: str, dir_hint: str | None):
    if dir_hint:
        sys.path.insert(0, dir_hint)
    name = Path(path).stem
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", help="the flattened file to validate")
    ap.add_argument("--against", help="reference agent module to diff against (e.g. main_v12.py)")
    ap.add_argument("--against-dir", default=".", help="directory to add to sys.path so --against's own imports resolve")
    ap.add_argument("--opponent", default="agents/main_v4.py")
    args = ap.parse_args()

    fn = load_via_kaggle(args.candidate)
    print(f"[1/2] kaggle loader resolves to: {fn.__name__}")
    if fn.__name__ != "agent":
        print(f"FAIL: expected 'agent', got '{fn.__name__}' -- this file would silently")
        print("      run the wrong function on Kaggle. Check for a name collision between")
        print("      the wrapped module and the wrapper (see this file's docstring).")
        sys.exit(1)

    argcount = fn.__code__.co_argcount
    print(f"[2/2] agent() takes {argcount} arg(s): {fn.__code__.co_varnames[:argcount]}")
    if argcount not in (1, 2):
        print("FAIL: expected agent(observation) or agent(observation, configuration)")
        sys.exit(1)
    print("Static checks passed.")

    if not args.against:
        return

    ref = load_module(args.against, args.against_dir)
    env = make("kaggriculture", configuration={
        "episodeSteps": 720, "startingMoney": 3000, "actTimeout": 1, "debug": True,
    })
    env.reset()

    n, mismatches = 0, 0

    def driver(obs):
        nonlocal n, mismatches
        o1, o2 = copy.deepcopy(obs), copy.deepcopy(obs)
        ra = ref.agent(o1)
        rb = fn(o2)
        n += 1
        if ra != rb:
            mismatches += 1
            if mismatches <= 5:
                print(f"MISMATCH step {n} day={obs.get('day')} hour={obs.get('hour')}")
                print(f"  ref : {ra}")
                print(f"  flat: {rb}")
        return ra

    env.run([driver, args.opponent])
    print(f"\n{n} steps compared, {mismatches} mismatches (via {args.opponent})")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
