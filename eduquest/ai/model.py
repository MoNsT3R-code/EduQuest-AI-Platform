"""The engagement model: a logistic regression stored as JSON weights.

Loading JSON instead of a pickle means a swapped model file can change predictions
but can never run code on the server.
"""
import json
from dataclasses import dataclass

import numpy as np

FEATURE_LABELS = {
    "quiz_score": "Quiz score",
    "time_spent_hrs": "Learning time",
    "attempts": "Quests in this subject",
    "hints_used": "Hints used",
    "streak_days": "Day streak",
    "assignments_completed": "Quests finished",
}


@dataclass
class Prediction:
    label: str
    confidence: float          # 0 to 100
    probabilities: dict        # label -> 0..1
    contributions: list        # [(feature, signed push toward the label)], largest first


class EngagementModel:
    def __init__(self, card):
        self.card = card
        self.features = card["features"]
        self.classes = card["classes"]
        self.mean = np.asarray(card["scaler"]["mean"], dtype=float)
        self.scale = np.asarray(card["scaler"]["scale"], dtype=float)
        self.coef = np.asarray(card["coef"], dtype=float)
        self.intercept = np.asarray(card["intercept"], dtype=float)
        n_cls, n_feat = len(self.classes), len(self.features)
        if self.mean.shape != (n_feat,) or self.scale.shape != (n_feat,) or self.coef.shape != (n_cls, n_feat) \
                or self.intercept.shape != (n_cls,) or not np.all(self.scale > 0):
            raise ValueError("engagement_model.json has inconsistent shapes")

    @classmethod
    def load(cls, path):
        try:
            with open(path, encoding="utf-8") as f:
                return cls(json.load(f))
        except FileNotFoundError:
            raise RuntimeError(f"Model not found at {path}. Run: python scripts/train_model.py") from None

    @property
    def version(self):
        return self.card["version"]

    def predict(self, values: dict) -> Prediction:
        x = np.array([float(values[f]) for f in self.features])
        z = (x - self.mean) / self.scale
        logits = self.coef @ z + self.intercept
        p = np.exp(logits - logits.max())
        p /= p.sum()
        k = int(p.argmax())
        # How much each feature pushes toward the chosen label versus the other labels
        others = np.delete(self.coef, k, axis=0).mean(axis=0)
        push = (self.coef[k] - others) * z
        contributions = sorted(zip(self.features, push.round(3).tolist()), key=lambda t: -abs(t[1]))
        return Prediction(
            label=self.classes[k],
            confidence=round(float(p[k]) * 100, 1),
            probabilities={c: round(float(v), 4) for c, v in zip(self.classes, p)},
            contributions=contributions,
        )

    def global_weights(self):
        """Average absolute weight per feature, for the About the AI page."""
        w = np.abs(self.coef).mean(axis=0)
        w = w / w.sum()
        return sorted(zip(self.features, w.round(3).tolist()), key=lambda t: -t[1])
