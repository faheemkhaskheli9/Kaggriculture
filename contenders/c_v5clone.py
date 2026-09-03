"""Neutrality check for contenders/_engine.py.

`make_agent({})` with no overrides must reproduce `main.py` v5 behaviour. This
file is that agent; benchmark it head-to-head against `main.py` and expect a
coin-neutral, ~50/50 result (small noise only, from RNG in the env, not the
policy). If it is not neutral, `_engine.py` has drifted from v5 and the drift
must be fixed before any contender built on it can be trusted.

    python test.py --games 30 --candidate contenders/c_v5clone.py --incumbent main.py \
        --opponents starter main_v5.py
"""
from _engine import make_agent

agent = make_agent({"name": "v5clone"})
