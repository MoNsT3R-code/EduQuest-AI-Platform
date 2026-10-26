"""The progress dashboard, the About the AI page, and the student's own data controls."""
import json

from flask import Blueprint, Response, current_app, g, redirect, render_template, request, session, url_for

from . import gamify
from .ai import adaptive, coach
from .ai.features import streak_days
from .ai.model import FEATURE_LABELS
from .auth import login_required
from .db import get_db, now, parse
from .questions import SUBJECTS

bp = Blueprint("dashboard", __name__)


def sparkline(values, width=220, height=48, pad=4):
    """SVG points for a small score chart (scores are 0-100)."""
    if not values:
        return ""
    if len(values) == 1:
        values = values * 2
    step = (width - 2 * pad) / (len(values) - 1)
    return " ".join(f"{pad + i * step:.1f},{height - pad - v / 100 * (height - 2 * pad):.1f}" for i, v in enumerate(values))


@bp.get("/dashboard")
@login_required
def dashboard():
    db, sid = get_db(), g.student["id"]
    quests = db.execute(
        """SELECT q.*, p.label, p.confidence FROM quests q LEFT JOIN predictions p ON p.quest_id = q.id
           WHERE q.student_id = ? AND q.finished_at IS NOT NULL ORDER BY q.finished_at DESC""", (sid,)).fetchall()
    started = db.execute("SELECT COUNT(*) FROM quests WHERE student_id = ?", (sid,)).fetchone()[0]
    xp = sum(q["xp"] or 0 for q in quests)
    dates = {parse(q["finished_at"]).date() for q in quests}
    streak = streak_days(dates, parse(now()).date())

    subjects = []
    for name, meta in SUBJECTS.items():
        mine = [q for q in quests if q["subject"] == name]
        scores = [round(q["score"]) for q in reversed(mine)][-10:]
        rating = db.execute("SELECT rating FROM skill_ratings WHERE student_id = ? AND subject = ?", (sid, name)).fetchone()
        rating = rating["rating"] if rating else adaptive.START
        label = mine[0]["label"] if mine else None
        subjects.append({
            "name": name, **meta, "count": len(mine), "label": label, "tier": coach.TIERS.get(label),
            "average": round(sum(scores) / len(scores)) if scores else None, "scores": scores,
            "points": sparkline(scores), "last": scores[-1] if scores else None,
            # Rating mapped to how likely a medium question is answered right: a friendly "mastery" figure
            "mastery": round(100 * adaptive.expected(rating, 2)),
        })

    have = {r["code"]: r["earned_at"] for r in db.execute("SELECT code, earned_at FROM badges WHERE student_id = ?", (sid,))}
    badges = [{"code": c, "emoji": e, "name": n, "desc": d, "earned": have.get(c)} for c, (e, n, d) in gamify.BADGES.items()]

    return render_template(
        "dashboard.html", quests=quests[:15], subjects=subjects, xp=xp, level=gamify.level_for(xp),
        streak=streak, badges=badges, finished=len(quests), started=started,
        minutes=round(sum(q["duration_s"] or 0 for q in quests) / 60))


@bp.get("/about-ai")
def about_ai():
    model = current_app.extensions["engagement_model"]
    weights = [(FEATURE_LABELS[f], w) for f, w in model.global_weights()]
    return render_template("about_ai.html", card=model.card, weights=weights, parts=coach.PARTS,
                           thresholds=coach.THRESHOLDS, tiers=coach.TIERS, targets=adaptive.TARGET)


@bp.get("/me/export")
@login_required
def export():
    """Everything stored about the signed-in student, as JSON (for a parent or teacher)."""
    db, sid = get_db(), g.student["id"]
    rows = lambda sql: [dict(r) for r in db.execute(sql, (sid,))]
    data = {
        "student": {k: g.student[k] for k in ("name", "grade", "created_at", "last_seen_at")},
        "quests": rows("SELECT id, subject, mode, started_at, finished_at, abandoned, score, hints_used, duration_s, xp FROM quests WHERE student_id = ?"),
        "answers": rows("""SELECT qi.quest_id, qi.position, qi.skill, qi.difficulty, qi.prompt, qi.tries, qi.hints_used, qi.correct
                           FROM quest_items qi JOIN quests q ON q.id = qi.quest_id WHERE q.student_id = ?"""),
        "predictions": rows("""SELECT p.quest_id, p.label, p.confidence, p.formula_score, p.model_version, p.features_json
                               FROM predictions p JOIN quests q ON q.id = p.quest_id WHERE q.student_id = ?"""),
        "skill_ratings": rows("SELECT subject, rating, updated_at FROM skill_ratings WHERE student_id = ?"),
        "badges": rows("SELECT code, earned_at FROM badges WHERE student_id = ?"),
        "exported_at": now(),
    }
    return Response(json.dumps(data, indent=2, ensure_ascii=False), mimetype="application/json",
                    headers={"Content-Disposition": 'attachment; filename="eduquest-my-data.json"'})


@bp.post("/me/delete")
@login_required
def delete_me():
    if request.form.get("confirm") != "DELETE":
        return redirect(url_for("dashboard.dashboard", delete_error=1) + "#my-data")
    with get_db() as db:
        db.execute("DELETE FROM students WHERE id = ?", (g.student["id"],))  # cascades to everything else
    session.clear()
    return redirect(url_for("auth.login", deleted=1))
