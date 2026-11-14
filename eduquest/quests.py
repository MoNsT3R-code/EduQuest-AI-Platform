"""Quests: five questions chosen one at a time for the student, timed by the server.

Everything the model needs (score, hints, tries, time) is measured here rather than typed
in, and the answer to each question never leaves the server until it is answered.
"""
import json
import random

from flask import Blueprint, abort, current_app, g, redirect, render_template, request, url_for

from . import game, gamify
from .ai import adaptive, coach
from .ai.features import compute as compute_features
from .ai.model import FEATURE_LABELS
from .auth import login_required, require_owner
from .db import get_db, now, parse
from .questions import SUBJECTS, make_question

bp = Blueprint("quests", __name__)

HINTS_ALLOWED = {"Launchpad": 2, "Steady": 1, "Challenge": 1}
MAX_TRIES = 2
MAX_ITEM_SECONDS = 300   # idle time beyond 5 minutes on one question isn't counted as learning


# ── Lookups ──────────────────────────────────────────────────

def latest_label(db, student_id, subject):
    row = db.execute(
        """SELECT p.label FROM predictions p JOIN quests q ON q.id = p.quest_id
           WHERE q.student_id = ? AND q.subject = ? ORDER BY q.finished_at DESC, q.id DESC LIMIT 1""",
        (student_id, subject)).fetchone()
    return row["label"] if row else None


def rating_of(db, student_id, subject):
    row = db.execute("SELECT rating FROM skill_ratings WHERE student_id = ? AND subject = ?",
                     (student_id, subject)).fetchone()
    return row["rating"] if row else adaptive.START


def total_xp(db, student_id):
    return db.execute("SELECT COALESCE(SUM(xp), 0) FROM quests WHERE student_id = ?", (student_id,)).fetchone()[0]


def load_quest(qid):
    return require_owner(get_db().execute("SELECT * FROM quests WHERE id = ?", (qid,)).fetchone())


def current_item(db, quest_id):
    return db.execute("SELECT * FROM quest_items WHERE quest_id = ? ORDER BY position DESC LIMIT 1",
                      (quest_id,)).fetchone()


def today():
    return parse(now()).date()


def daily_done(db, student_id):
    """Whether today's daily challenge has been finished already (dates are UTC, like streaks)."""
    return db.execute("SELECT 1 FROM quests WHERE student_id = ? AND daily = 1 AND finished_at >= ?",
                      (student_id, today().isoformat())).fetchone() is not None


def eliminated_options(item):
    """The two wrong options a Launchpad 50:50 hint removes (always the same two for an item)."""
    if item["hints_used"] < 2:
        return []
    wrong = [i for i in range(len(json.loads(item["options_json"]))) if i != item["answer_index"]]
    return sorted(random.Random(item["id"]).sample(wrong, 2))


# ── Pages ────────────────────────────────────────────────────

@bp.get("/home")
@login_required
def home():
    if g.student["buddy"] is None:
        return redirect(url_for("world.choose"))
    db, sid = get_db(), g.student["id"]
    daily = game.daily_subject(today())
    subjects = []
    for name, meta in SUBJECTS.items():
        label = latest_label(db, sid, name)
        stats = db.execute(
            """SELECT COUNT(*) AS n, MAX(score) AS best, COALESCE(SUM(boss_defeated), 0) AS bosses
               FROM quests WHERE student_id = ? AND subject = ? AND finished_at IS NOT NULL""",
            (sid, name)).fetchone()
        subjects.append({"name": name, **meta, "label": label, "tier": coach.TIERS.get(label),
                         "mode": coach.TIERS[label]["mode"] if label else "Steady",
                         "quests": stats["n"], "best": stats["best"], "bosses": stats["bosses"],
                         "monster": game.MONSTERS[name], "map": game.map_path(stats["n"]), "daily": name == daily})
    unfinished = db.execute(
        "SELECT * FROM quests WHERE student_id = ? AND finished_at IS NULL AND abandoned = 0 ORDER BY id DESC LIMIT 1",
        (sid,)).fetchone()
    xp = total_xp(db, sid)
    return render_template("home.html", subjects=subjects, unfinished=unfinished,
                           level=gamify.level_for(xp), xp=xp, welcome=request.args.get("welcome"),
                           met=request.args.get("met"), daily=daily, daily_done=daily_done(db, sid),
                           daily_monster=game.MONSTERS[daily])


@bp.post("/quest/start")
@login_required
def start():
    subject = request.form.get("subject")
    if subject not in SUBJECTS:
        abort(400, description="Pick one of the three subjects.")
    db, sid = get_db(), g.student["id"]
    label = latest_label(db, sid, subject)
    mode = coach.TIERS[label]["mode"] if label else "Steady"
    daily = int(subject == game.daily_subject(today()) and not daily_done(db, sid))
    with db:
        db.execute("UPDATE quests SET abandoned = 1 WHERE student_id = ? AND finished_at IS NULL", (sid,))
        cur = db.execute("INSERT INTO quests (student_id, subject, mode, started_at, daily) VALUES (?, ?, ?, ?, ?)",
                         (sid, subject, mode, now(), daily))
        quest = db.execute("SELECT * FROM quests WHERE id = ?", (cur.lastrowid,)).fetchone()
        serve_item(db, quest, 1)
    return redirect(url_for("quests.play", qid=quest["id"]))


def serve_item(db, quest, position):
    sid = quest["student_id"]
    difficulty = adaptive.pick_difficulty(rating_of(db, sid, quest["subject"]), quest["mode"])
    recent = [r["prompt"] for r in db.execute(
        """SELECT qi.prompt FROM quest_items qi JOIN quests q ON q.id = qi.quest_id
           WHERE q.student_id = ? AND q.subject = ? ORDER BY qi.id DESC LIMIT 40""", (sid, quest["subject"]))]
    q = make_question(quest["subject"], g.student["grade"], difficulty, used=recent)
    db.execute(
        """INSERT INTO quest_items (quest_id, position, skill, difficulty, prompt, options_json, answer_index,
           hint, explanation, served_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (quest["id"], position, q.skill, q.difficulty, q.prompt, json.dumps(q.options), q.answer,
         q.hint, q.explanation, now()))


@bp.get("/quest/<int:qid>")
@login_required
def play(qid):
    quest = load_quest(qid)
    if quest["finished_at"]:
        return redirect(url_for("quests.result", qid=qid))
    if quest["abandoned"]:
        return redirect(url_for("quests.home"))
    db = get_db()
    item = current_item(db, qid)
    allowed = HINTS_ALLOWED[quest["mode"]]
    resolved = item["correct"] is not None
    return render_template(
        "play.html", quest=quest, item=item, options=json.loads(item["options_json"]),
        eliminated=eliminated_options(item), hints_left=allowed - item["hints_used"], hints_allowed=allowed,
        total=current_app.config["QUEST_LENGTH"], resolved=resolved,
        elapsed=int((parse(now()) - parse(quest["started_at"])).total_seconds()),
        show_timer=quest["mode"] != "Launchpad", subject=SUBJECTS[quest["subject"]],
        battle=battle_state(db, quest, item, resolved))


def battle_state(db, quest, item, resolved):
    """What the battle arena shows: monster hearts, the combo, and what just happened."""
    items = db.execute("SELECT * FROM quest_items WHERE quest_id = ? ORDER BY position", (quest["id"],)).fetchall()
    done = [it for it in items if it["correct"] is not None]
    monster = game.MONSTERS[quest["subject"]]
    if resolved and item["correct"]:
        event = "hit" if item["tries"] == 1 else "hit_retry"
    elif resolved:
        event = "miss"
    elif item["tries"] == 1:
        event = "oops"
    elif item["hints_used"]:
        event = "hint"
    elif item["position"] == 1:
        event = "start"
    else:
        event = None
    combo = game.combo_series(done)[-1] if done else 0
    return {
        "monster": monster, "event": event, "hearts": current_app.config["QUEST_LENGTH"],
        "lost": game.hits(done), "combo": combo, "daily": quest["daily"],
        "line": game.say(event, item["id"] * 7 + item["tries"], monster=monster["name"]) if event else None,
    }


@bp.post("/quest/<int:qid>/answer")
@login_required
def answer(qid):
    quest = load_quest(qid)
    db = get_db()
    item = current_item(db, qid)
    if quest["finished_at"] or quest["abandoned"] or item["correct"] is not None:
        return redirect(url_for("quests.play", qid=qid))
    try:
        choice = int(request.form.get("choice", ""))
    except ValueError:
        choice = -1
    if choice not in range(len(json.loads(item["options_json"]))) or choice in eliminated_options(item):
        abort(400, description="Pick one of the answers.")

    tries = item["tries"] + 1
    right = choice == item["answer_index"]
    resolved = right or tries >= MAX_TRIES
    credit = (1.0 if tries == 1 else 0.5) if right else 0.0
    with db:
        # The tries check makes a double-click count once
        cur = db.execute(
            """UPDATE quest_items SET tries = ?, last_choice = ?, correct = ?, credit = ?, answered_at = ?
               WHERE id = ? AND tries = ? AND correct IS NULL""",
            (tries, choice, int(right) if resolved else None, credit if resolved else None,
             now() if resolved else None, item["id"], item["tries"]))
        if cur.rowcount and resolved:
            sid, subject = g.student["id"], quest["subject"]
            row = db.execute("SELECT rating, answers FROM skill_ratings WHERE student_id = ? AND subject = ?",
                             (sid, subject)).fetchone()
            rating, answers = (row["rating"], row["answers"]) if row else (adaptive.START, 0)
            rating = adaptive.update(rating, item["difficulty"], credit, answers)
            db.execute(
                """INSERT INTO skill_ratings (student_id, subject, rating, answers, updated_at) VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT (student_id, subject) DO UPDATE SET rating = excluded.rating,
                   answers = answers + 1, updated_at = excluded.updated_at""",
                (sid, subject, rating, now()))
    return redirect(url_for("quests.play", qid=qid) + "#arena")


@bp.post("/quest/<int:qid>/hint")
@login_required
def hint(qid):
    quest = load_quest(qid)
    db = get_db()
    item = current_item(db, qid)
    if not quest["finished_at"] and item["correct"] is None and item["hints_used"] < HINTS_ALLOWED[quest["mode"]]:
        with db:
            db.execute("UPDATE quest_items SET hints_used = hints_used + 1 WHERE id = ? AND hints_used = ?",
                       (item["id"], item["hints_used"]))
    return redirect(url_for("quests.play", qid=qid) + "#arena")


@bp.post("/quest/<int:qid>/next")
@login_required
def next_question(qid):
    quest = load_quest(qid)
    db = get_db()
    item = current_item(db, qid)
    if quest["finished_at"]:
        return redirect(url_for("quests.result", qid=qid))
    if item["correct"] is None:
        return redirect(url_for("quests.play", qid=qid))
    if item["position"] >= current_app.config["QUEST_LENGTH"]:
        finish(db, quest)
        return redirect(url_for("quests.result", qid=qid))
    with db:
        if current_item(db, qid)["position"] == item["position"]:
            serve_item(db, quest, item["position"] + 1)
    return redirect(url_for("quests.play", qid=qid) + "#arena")


@bp.post("/quest/<int:qid>/quit")
@login_required
def quit_quest(qid):
    quest = load_quest(qid)
    if not quest["finished_at"]:
        with get_db() as db:
            db.execute("UPDATE quests SET abandoned = 1 WHERE id = ?", (qid,))
    return redirect(url_for("quests.home"))


def finish(db, quest):
    sid, qid = quest["student_id"], quest["id"]
    items = db.execute("SELECT * FROM quest_items WHERE quest_id = ? ORDER BY position", (qid,)).fetchall()
    score = 100 * sum(it["credit"] for it in items) / len(items)
    hints = sum(it["hints_used"] for it in items)
    duration = sum(min((parse(it["answered_at"]) - parse(it["served_at"])).total_seconds(), MAX_ITEM_SECONDS)
                   for it in items)
    previous = latest_label(db, sid, quest["subject"])
    xp_before = total_xp(db, sid)
    finished_at = now()
    model = current_app.extensions["engagement_model"]

    with db:
        cur = db.execute(
            "UPDATE quests SET finished_at = ?, score = ?, hints_used = ?, duration_s = ? WHERE id = ? AND finished_at IS NULL",
            (finished_at, score, hints, duration, qid))
        if not cur.rowcount:
            return  # finished already by a double-submit
        updated = db.execute("SELECT * FROM quests WHERE id = ?", (qid,)).fetchone()
        features = compute_features(db, sid, updated, parse(finished_at))
        pred = model.predict(features)
        defeated = game.hits(items) == len(items)
        best_combo = max(game.combo_series(items), default=0)
        daily = bool(quest["daily"])
        xp = gamify.quest_xp(items, pred.label, features["streak_days"]) + game.combo_xp(items) \
            + (game.DAILY_XP if daily else 0)
        coins = game.quest_coins(items, defeated, daily)
        db.execute("UPDATE quests SET xp = ?, coins = ?, best_combo = ?, boss_defeated = ? WHERE id = ?",
                   (xp, coins, best_combo, int(defeated), qid))
        db.execute("UPDATE students SET coins = coins + ? WHERE id = ?", (coins, sid))
        extra = [code for code, ok in (("boss_slayer", defeated), ("combo_5", best_combo >= 5),
                                       ("daily_hero", daily)) if ok]
        db.execute(
            """INSERT INTO predictions (quest_id, label, confidence, formula_score, model_version, features_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (qid, pred.label, pred.confidence, coach.formula_score(features), model.version,
             json.dumps({"features": features, "probabilities": pred.probabilities,
                         "contributions": pred.contributions, "previous": previous}), finished_at))
        gamify.award(db, sid, qid, items, pred.label, previous, features, xp_before + xp, extra)


@bp.get("/quest/<int:qid>/result")
@login_required
def result(qid):
    quest = load_quest(qid)
    if not quest["finished_at"]:
        return redirect(url_for("quests.play", qid=qid))
    db = get_db()
    pred = db.execute("SELECT * FROM predictions WHERE quest_id = ?", (qid,)).fetchone()
    saved = json.loads(pred["features_json"])
    features = saved["features"]
    items = db.execute("SELECT * FROM quest_items WHERE quest_id = ? ORDER BY position", (qid,)).fetchall()
    review = [{"prompt": it["prompt"], "options": json.loads(it["options_json"]), "answer": it["answer_index"],
               "choice": it["last_choice"], "correct": it["correct"], "tries": it["tries"], "skill": it["skill"],
               "explanation": it["explanation"], "hints": it["hints_used"]} for it in items]
    practise = sorted({r["skill"] for r in review if not r["correct"] or r["tries"] > 1})
    new_badges = [gamify.BADGES[r["code"]] for r in
                  db.execute("SELECT code FROM badges WHERE quest_id = ?", (qid,))]
    xp_now = total_xp(db, g.student["id"])
    before, after = gamify.level_for(xp_now - (quest["xp"] or 0)), gamify.level_for(xp_now)
    formula = coach.formula_label(pred["formula_score"])
    pushes = [{"label": FEATURE_LABELS[f], "push": v} for f, v in saved["contributions"] if abs(v) >= 0.05][:4]
    return render_template(
        "result.html", quest=quest, pred=pred, tier=coach.TIERS[pred["label"]], features=features,
        breakdown=coach.breakdown(features), path=coach.next_tier_path(features),
        tip=coach.SUBJECT_TIPS[quest["subject"]][pred["label"]], review=review, practise=practise,
        new_badges=new_badges, level=after, levelled_up=after["level"] > before["level"],
        borderline=formula != pred["label"] or pred["confidence"] < 60, pushes=pushes,
        previous=saved.get("previous"), probabilities=saved["probabilities"], subject=SUBJECTS[quest["subject"]],
        monster=game.MONSTERS[quest["subject"]], defeated=bool(quest["boss_defeated"]),
        hits=game.hits(items), outro=game.say("win" if quest["boss_defeated"] else "escape", qid,
                                               monster=game.MONSTERS[quest["subject"]]["name"]))
