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
        if not confidence:
            return v10.agent(obs)
        # Abstain per unit. An intent of -1 receives no learned priority bonus,
        # so that unit follows the teacher assignment while confident units can
        # still contribute; requiring min(confidence) previously disabled the
        # model whenever any one of 10-14 workers was uncertain.
        intents = [intent if conf >= _MODEL.confidence else -1
                   for intent, conf in zip(intents, confidence)]
        if all(intent < 0 for intent in intents):
            return v10.agent(obs)
        return expand(obs, intents=intents)
    except Exception:
        return v10.agent(obs)


if __name__ == "__main__":
    print("Kaggriculture Hybrid AI v1", "learned" if _MODEL else "v10 fallback")
