"""Small pure-Python linear intent policy with abstention and safe loading."""
from __future__ import annotations

import json
import math
from pathlib import Path

from ml.rl.encode import GLOBAL_NAMES, UNIT_NAMES, encode_policy_rows
from ml.rl.hybrid_action import N_INTENT


class IntentPolicy:
    def __init__(self, weights, bias, confidence=0.55):
        self.weights = weights
        self.bias = bias
        self.confidence = float(confidence)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != "kagri-intent-linear-v1":
            raise ValueError("unsupported intent-model format")
        n_features = len(GLOBAL_NAMES) + len(UNIT_NAMES)
        w, b = data["weights"], data["bias"]
        if len(w) != N_INTENT or len(b) != N_INTENT or any(len(row) != n_features for row in w):
            raise ValueError("intent-model shape mismatch")
        return cls(w, b, data.get("confidence", 0.55))

    def predict(self, obs):
        intents, confidences = [], []
        for row in encode_policy_rows(obs):
            logits = [float(self.bias[k]) + sum(float(a) * float(x)
                      for a, x in zip(self.weights[k], row)) for k in range(N_INTENT)]
            m = max(logits)
            ex = [math.exp(max(-40.0, z - m)) for z in logits]
            den = sum(ex) or 1.0
            probs = [v / den for v in ex]
            k = max(range(N_INTENT), key=probs.__getitem__)
            intents.append(k)
            confidences.append(probs[k])
        return intents, confidences

