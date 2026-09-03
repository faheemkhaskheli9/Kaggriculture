"""Opponent league for pipeline evaluation.

The whole point of PLAN_ML_MODELS is that local self-play does not predict the
ladder, so every optimiser run is scored against a *spread* of opponents:
the ``bots/`` archetypes (which reproduce ladder strategies that beat us),
``starter``, and the promoted-version lineage.

``resolve(name)`` returns something ``kaggle_environments`` accepts as an agent:
a builtin string (``"starter"``/``"random"``/``"pass"``) or a filesystem path.
"""
from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BUILTINS = {"starter", "random", "pass"}

BOTS = {
    "wheatflood": "bots/bot_wheatflood.py",
    "animalfarm": "bots/bot_animalfarm.py",
    "animalfactory_v2": "bots/bot_animalfactory_v2.py",
    "melonmono":  "bots/bot_melonmono.py",
    "premium":    "bots/bot_premium.py",
}
LINEAGE = {
    "v1": "agents/main_v1.py", "v2": "agents/main_v2.py",
    "v3": "agents/main_v3.py", "v4": "agents/main_v4.py",
    "v5": "agents/main_v5.py", "v6": "agents/main_v6.py",
    "v7": "agents/main_v7.py",
    "main": "main.py",
}

# named groups the drivers accept via --league
GROUPS = {
    "floor":   ["wheatflood", "animalfarm", "melonmono", "premium", "starter"],
    # PLAN_ML_IMPROVE.md B1: the gate now contains the strong animal-factory
    # proxy (our worst matchup, 56% of ladder games) + v4 (the matchup v6 broke)
    # + main. A high fitness here should mean promotable.
    "gate":    ["animalfactory_v2", "animalfarm", "wheatflood", "premium", "v4", "main"],
    # the docs/PLAN_LADDER_ECON.md s4 promote gate, verbatim
    "ladder_econ": ["animalfactory_v2", "animalfarm", "v4", "main",
                    "wheatflood", "premium", "starter"],
    # NEVER used for search -- report fitness here each gen to catch overfit (B3)
    "heldout": ["melonmono", "v6", "premium", "starter"],
    "lineage": ["v1", "v3", "v5", "v7", "main"],
    "quick":   ["animalfactory_v2", "premium", "starter"],
    "all":     ["wheatflood", "animalfarm", "animalfactory_v2", "melonmono",
                "premium", "starter", "v1", "v3", "v5", "v7", "main"],
}


def resolve(name: str) -> str:
    if name in BUILTINS:
        return name
    for table in (BOTS, LINEAGE):
        if name in table:
            p = os.path.join(_ROOT, table[name])
            if not os.path.exists(p):
                raise FileNotFoundError(f"league member {name!r} -> missing {p}")
            return p
    if os.path.exists(name):
        return name
    p = os.path.join(_ROOT, name)
    if os.path.exists(p):
        return p
    raise KeyError(f"unknown league member {name!r}")


def expand(spec: str) -> list[str]:
    """'floor' -> the group; 'a,b,c' -> that list; 'x' -> ['x']."""
    if spec in GROUPS:
        return list(GROUPS[spec])
    return [s.strip() for s in spec.split(",") if s.strip()]
