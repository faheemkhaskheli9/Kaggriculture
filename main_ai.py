"""Kaggriculture hybrid AI v1. Safe fallback is the unchanged v10 main.agent."""
import os
from pathlib import Path

import main as v10
from ml.rl.hybrid_action import expand
from ml.rl.policy import IntentPolicy

_MODEL = None
# kaggle-environments executes source files without defining ``__file__``.
# Submission bundles place weights beside main_ai.py at the working directory.
_MODEL_PATH = Path(os.environ.get("KAGRI_INTENT_MODEL", "intent_model.json"))
try:
    if _MODEL_PATH.exists():
        _MODEL = IntentPolicy.load(_MODEL_PATH)
except Exception:
    _MODEL = None


def agent(obs):
    if _MODEL is None:
        return v10.agent(obs)
    try:
        intents, confidence = _MODEL.predict(obs)
        # Whole-turn abstention prevents a weak/out-of-distribution model from
        # perturbing the tested teacher policy.
        if not confidence or min(confidence) < _MODEL.confidence:
            return v10.agent(obs)
        return expand(obs, intents=intents)
    except Exception:
        return v10.agent(obs)


if __name__ == "__main__":
    print("Kaggriculture Hybrid AI v1", "learned" if _MODEL else "v10 fallback")
