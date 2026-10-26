"""The tier formula from the project, explained, and the shortest path to the next tier.

The dataset's labels come from S = 0.4·quiz + 0.3·quests finished + 0.2·streak + 0.1·time
(streak scaled to 30 days and time to 10 hours). Because the tiers are defined by this
formula, it is also the clearest way to tell a child what counts and what to do next.
"""
import math

PARTS = [
    # feature, weight, value of 100% on its scale, label for children
    ("quiz_score", 0.4, 100, "Quiz score"),
    ("assignments_completed", 0.3, 100, "Quests finished"),
    ("streak_days", 0.2, 30, "Day streak"),
    ("time_spent_hrs", 0.1, 10, "Learning time"),
]
THRESHOLDS = {"Medium": 50, "High": 65}   # S above 50 is Medium, above 65 is High
TIERS = {
    "High": {"badge": "Gold Scholar", "emoji": "🏆", "mode": "Challenge", "line": "Top of the class!"},
    "Medium": {"badge": "Silver Star", "emoji": "🥈", "mode": "Steady", "line": "Rising star, almost there!"},
    "Low": {"badge": "Bronze Beginner", "emoji": "🥉", "mode": "Launchpad", "line": "Every expert was once a beginner!"},
}

SUBJECT_TIPS = {
    "Mathematics": {
        "High": "Excellent in Math! Try the challenge questions and help a friend with a tricky one.",
        "Medium": "Good progress in Math! Practise word problems and try to answer without hints.",
        "Low": "Focus on Math basics: revisit your times tables and do a short quest every day.",
    },
    "English": {
        "High": "Outstanding in English! Try writing a short story using three new words.",
        "Medium": "Good effort in English! Practise grammar and read a page out loud each day.",
        "Low": "Start with English basics: read a short story daily and look up one new word.",
    },
    "Computer Science": {
        "High": "Great at CS! Try building a small project, like a quiz game, in Scratch.",
        "Medium": "Good progress in CS! Practise reading code step by step and predicting what it does.",
        "Low": "Focus on CS basics: practise putting steps in order, like a recipe for the computer.",
    },
}


def breakdown(features):
    """Points each part contributes to S (out of 40, 30, 20 and 10)."""
    rows = []
    for key, weight, full, label in PARTS:
        share = min(max(features[key] / full, 0), 1)
        rows.append({"key": key, "label": label, "points": round(share * weight * 100, 1), "max": weight * 100})
    return rows


def formula_score(features):
    return round(sum(r["points"] for r in breakdown(features)), 1)


def formula_label(score):
    if score > THRESHOLDS["High"]:
        return "High"
    if score > THRESHOLDS["Medium"]:
        return "Medium"
    return "Low"


def next_tier_path(features):
    """Up to two concrete steps that would each, on their own, lift S into the next tier."""
    score = formula_score(features)
    label = formula_label(score)
    if label == "High":
        return {"target": None, "gap": 0, "steps": []}
    target = "High" if label == "Medium" else "Medium"
    gap = THRESHOLDS[target] - score + 0.1

    steps = []
    q = features["quiz_score"]
    need = math.ceil(gap / 0.4)
    if q + need <= 100:
        steps.append((need / 25, f"Score {need} points more in your next quest (aim for {min(100, round(q + need))}%)"))
    days = math.ceil(gap / (0.2 * 100 / 30))
    if features["streak_days"] + days <= 30:
        steps.append((days / 3, f"Play {days} more day{'s' if days != 1 else ''} in a row"))
    a = features["assignments_completed"]
    more = math.ceil(gap / 0.3)
    if a + more <= 100:
        steps.append((more / 20, "Finish every quest you start, no skipping"))
    hours = gap / (0.1 * 100 / 10)
    if features["time_spent_hrs"] + hours <= 10:
        mins = math.ceil(hours * 60 / 5) * 5
        steps.append((hours, f"Spend about {mins} more minutes learning this month"))
    steps.sort(key=lambda s: s[0])
    return {"target": target, "gap": round(gap, 1), "steps": [s[1] for s in steps[:2]]}
