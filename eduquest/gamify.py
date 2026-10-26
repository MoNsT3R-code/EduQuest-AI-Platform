"""XP, levels and achievement badges.

XP rewards what the student did (every right answer counts, and right on a second try
still earns some), plus a bonus for showing up on consecutive days. The tier adds a
small bonus too, but the lowest tier gets the biggest effort bonus, so a beginner who
keeps going is never left behind.
"""
from .db import now

XP_FIRST_TRY = 10
XP_SECOND_TRY = 5
XP_NO_HINT = 2
TIER_BONUS = {"Low": 15, "Medium": 10, "High": 10}
LEVEL_XP = 200

BADGES = {
    "first_quest": ("🚩", "First Quest", "Finished your very first quest"),
    "perfect": ("💯", "Perfect Run", "Every answer right first time"),
    "no_hints": ("🧠", "Brain Power", "A whole quest without hints"),
    "streak_3": ("🔥", "On Fire", "Quests 3 days in a row"),
    "streak_7": ("🌋", "Unstoppable", "Quests 7 days in a row"),
    "explorer": ("🧭", "Explorer", "Tried all three subjects"),
    "comeback": ("🚀", "Comeback", "Moved up a tier in a subject"),
    "level_5": ("👑", "Level 5", "Reached level 5"),
}


def quest_xp(items, label, streak):
    xp = 0
    for it in items:
        if it["correct"]:
            xp += XP_FIRST_TRY if it["tries"] == 1 else XP_SECOND_TRY
        if it["hints_used"] == 0:
            xp += XP_NO_HINT
    return xp + TIER_BONUS[label] + min(streak, 7) * 2


def level_for(total_xp):
    level = total_xp // LEVEL_XP + 1
    into = total_xp % LEVEL_XP
    return {"level": level, "into": into, "needed": LEVEL_XP, "percent": round(100 * into / LEVEL_XP)}


def award(conn, student_id, quest_id, items, label, previous_label, features, total_xp):
    """Insert newly earned badges and return their codes."""
    have = {r["code"] for r in conn.execute("SELECT code FROM badges WHERE student_id = ?", (student_id,))}
    earned = ["first_quest"]
    if all(it["correct"] and it["tries"] == 1 for it in items):
        earned.append("perfect")
    if sum(it["hints_used"] for it in items) == 0:
        earned.append("no_hints")
    if features["streak_days"] >= 3:
        earned.append("streak_3")
    if features["streak_days"] >= 7:
        earned.append("streak_7")
    subjects = conn.execute(
        "SELECT COUNT(DISTINCT subject) FROM quests WHERE student_id = ? AND finished_at IS NOT NULL", (student_id,)).fetchone()[0]
    if subjects >= 3:
        earned.append("explorer")
    order = {"Low": 0, "Medium": 1, "High": 2}
    if previous_label and order[label] > order[previous_label]:
        earned.append("comeback")
    if level_for(total_xp)["level"] >= 5:
        earned.append("level_5")
    new = [c for c in earned if c not in have]
    conn.executemany("INSERT INTO badges (student_id, code, quest_id, earned_at) VALUES (?, ?, ?, ?)",
                     [(student_id, c, quest_id, now()) for c in new])
    return new
