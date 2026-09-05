"""Local entry point for the opponent- and market-aware herd selector."""

from main import _run_strategy, strategy_intent


def agent(obs):
    return _run_strategy(obs, strategy_intent("ANTI_META"))
