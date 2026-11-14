"""Turns what a student actually did into the six inputs the model was trained on.

Before, students typed these numbers into a form. Now the app measures them:

    quiz_score             score in the quest just finished (0-100)
    time_spent_hrs         time spent in finished quests over the last 30 days (hours, max 10)
    attempts               quests finished in this subject over the last 30 days (1-5)
    hints_used             hints taken in the quest just finished (0-10)
    streak_days            days in a row, up to today, with a finished quest (0-30)
    assignments_completed  share of quests started in the last 30 days that were finished (%)
"""
from datetime import timedelta

from ..db import parse


def streak_days(finished_dates, today):
    days, seen = 0, set(finished_dates)
    while today - timedelta(days=days) in seen and days < 30:
        days += 1
    return days


def compute(conn, student_id, quest, now_dt):
    since = (now_dt - timedelta(days=30)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT subject, finished_at, abandoned, duration_s FROM quests WHERE student_id = ? AND started_at >= ?",
        (student_id, since)).fetchall()
    finished = [r for r in rows if r["finished_at"]]
    started = len(rows)

    hours = sum(r["duration_s"] or 0 for r in finished) / 3600
    in_subject = sum(1 for r in finished if r["subject"] == quest["subject"])
    all_finished = conn.execute(
        "SELECT finished_at FROM quests WHERE student_id = ? AND finished_at IS NOT NULL", (student_id,)).fetchall()
    dates = {parse(r["finished_at"]).date() for r in all_finished}

    return {
        "quiz_score": round(quest["score"], 1),
        "time_spent_hrs": round(min(hours, 10), 3),
        "attempts": max(1, min(in_subject, 5)),
        "hints_used": min(quest["hints_used"], 10),
        "streak_days": streak_days(dates, now_dt.date()),
        "assignments_completed": round(100 * len(finished) / started, 1) if started else 0.0,
    }
