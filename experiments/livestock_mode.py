"""Local evaluation entry point for main.py's LIVESTOCK_ENGINE toggle.

This thin adapter contains no strategy logic; it keeps experiments reproducible
without changing the submission-default STRATEGY_MODE in main.py.
"""

from main import _run_strategy, strategy_intent


def agent(obs):
    return _run_strategy(obs, strategy_intent("LIVESTOCK_ENGINE"))
