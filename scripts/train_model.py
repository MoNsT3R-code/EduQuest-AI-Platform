"""Train the engagement model and export it as plain JSON (no pickle).

    python scripts/train_model.py

Compares the notebook's Random Forest with Gradient Boosting and Logistic Regression
using 5-fold stratified cross-validation on student_data.csv, keeps the notebook's
80/20 split as a hold-out check, and writes models/engagement_model.json.
"""
import json
import os
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES = ["quiz_score", "time_spent_hrs", "attempts", "hints_used", "streak_days", "assignments_completed"]
SEED = 42


def main():
    df = pd.read_csv(os.path.join(ROOT, "student_data.csv"))
    X, y = df[FEATURES].to_numpy(dtype=float), df["performance_label"].to_numpy()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    candidates = {
        "Random Forest (notebook)": RandomForestClassifier(n_estimators=100, random_state=SEED),
        "Gradient Boosting": GradientBoostingClassifier(random_state=SEED),
    }
    for C in (1, 10, 100):
        candidates[f"Logistic Regression (C={C})"] = make_pipeline(
            StandardScaler(), LogisticRegression(C=C, max_iter=5000))

    comparison = []
    for name, model in candidates.items():
        scores = cross_val_score(model, X, y, cv=cv)
        comparison.append({"model": name, "cv_accuracy": round(scores.mean(), 4), "cv_std": round(scores.std(), 4)})
        print(f"{name:32s} {scores.mean():.3f} ± {scores.std():.3f}")

    # Only a logistic regression can be exported as weights; pick the best of those
    best = max((c for c in comparison if c["model"].startswith("Logistic")), key=lambda c: c["cv_accuracy"])
    chosen = candidates[best["model"]]

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    holdout = chosen.fit(X_tr, y_tr)
    pred = holdout.predict(X_te)
    report = classification_report(y_te, pred, output_dict=True)
    classes = list(holdout.classes_)

    final = chosen.fit(X, y)  # the shipped model learns from every record
    scaler, lr = final.named_steps["standardscaler"], final.named_steps["logisticregression"]
    version = datetime.now(timezone.utc).strftime("lr-%Y%m%d")

    card = {
        "version": version,
        "kind": "multinomial logistic regression",
        "features": FEATURES,
        "classes": [str(c) for c in lr.classes_],
        "scaler": {"mean": scaler.mean_.round(8).tolist(), "scale": scaler.scale_.round(8).tolist()},
        "coef": lr.coef_.round(8).tolist(),
        "intercept": lr.intercept_.round(8).tolist(),
        "training": {
            "records": int(len(df)),
            "label_counts": {k: int(v) for k, v in df["performance_label"].value_counts().items()},
            "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sklearn": sklearn.__version__,
            "chosen": best["model"],
        },
        "comparison": comparison,
        "holdout": {
            "accuracy": round(float(np.mean(pred == y_te)), 4),
            "per_class": {c: {k: round(report[c][k], 3) for k in ("precision", "recall", "f1-score")} for c in classes},
            "confusion_matrix": {"labels": classes, "rows": confusion_matrix(y_te, pred, labels=classes).tolist()},
        },
    }
    out = os.path.join(ROOT, "models", "engagement_model.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)
        f.write("\n")
    print(f"\nChose {best['model']} · hold-out accuracy {card['holdout']['accuracy']:.1%} · wrote {out}")


if __name__ == "__main__":
    main()
