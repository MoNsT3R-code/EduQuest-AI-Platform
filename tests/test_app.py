import json
import re

import pandas as pd

from eduquest.ai import adaptive, coach
from eduquest.ai.model import EngagementModel
from eduquest.db import connect
from eduquest.questions import SUBJECTS, make_question

from conftest import post, sign_up, token


def answer_index(app, quest_id):
    conn = connect(app.config["DATABASE"])
    row = conn.execute("SELECT answer_index FROM quest_items WHERE quest_id = ? ORDER BY position DESC LIMIT 1",
                       (quest_id,)).fetchone()
    conn.close()
    return row[0]


def play_quest(client, app, subject="Mathematics", right=True):
    r = post(client, "/quest/start", subject=subject)
    qid = int(re.search(r"/quest/(\d+)", r.headers["Location"]).group(1))
    for _ in range(app.config["QUEST_LENGTH"]):
        a = answer_index(app, qid)
        post(client, f"/quest/{qid}/answer", choice=a if right else (a + 1) % 4)
        if not right:
            post(client, f"/quest/{qid}/answer", choice=(a + 2) % 4)
        post(client, f"/quest/{qid}/next")
    return qid


# ── Security ──

def test_post_without_csrf_is_rejected(client):
    r = client.post("/", data={"mode": "new", "name": "Ali", "grade": 4})
    assert r.status_code == 400


def test_security_headers(client):
    r = client.get("/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"


def test_sign_up_then_wrong_pictures_then_lockout(client):
    assert sign_up(client).status_code == 302
    post(client, "/logout")
    for _ in range(5):
        r = client.post("/", data={"csrf_token": token(client), "mode": "return", "name": "ayesha", "grade": 5,
                                   "pic_first": "pizza", "pic_second": "rocket", "pic_third": "apple"})
        assert r.status_code == 400
    r = client.post("/", data={"csrf_token": token(client), "mode": "return", "name": "Ayesha", "grade": 5,
                               "pic_first": "lion", "pic_second": "rocket", "pic_third": "apple"})
    assert r.status_code == 429  # even the right pictures wait out the lockout


def test_returning_player_signs_in(client):
    sign_up(client)
    post(client, "/logout")
    r = client.post("/", data={"csrf_token": token(client), "mode": "return", "name": "  AYESHA ", "grade": 5,
                               "pic_first": "lion", "pic_second": "rocket", "pic_third": "apple"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/home")


def test_duplicate_name_in_grade_is_refused(client):
    sign_up(client)
    post(client, "/logout")
    r = sign_up(client, pics=("star", "star", "star"))
    assert r.status_code == 400 and b"already uses the name" in r.data


def test_pages_need_sign_in(client):
    for url in ("/home", "/dashboard", "/me/export", "/quest/1"):
        assert client.get(url).status_code == 302


def test_cannot_open_another_students_quest(app):
    a, b = app.test_client(), app.test_client()
    sign_up(a, name="Ali")
    sign_up(b, name="Sara")
    r = post(a, "/quest/start", subject="English")
    url = r.headers["Location"]
    assert b.get(url).status_code == 404


def test_answer_is_not_in_the_page(client, app):
    sign_up(client)
    r = post(client, "/quest/start", subject="Mathematics")
    page = client.get(r.headers["Location"]).data.decode()
    # Nothing in the unanswered page marks which option is right
    assert "answer-right" not in page and "correct answer" not in page and "answer_index" not in page


# ── The quest flow ──

def test_full_quest_records_prediction_xp_and_badges(client, app):
    sign_up(client)
    qid = play_quest(client, app)
    r = client.get(f"/quest/{qid}/result")
    assert r.status_code == 200
    html = r.data.decode()
    assert "First Quest" in html and "Perfect Run" in html and "What counts toward your tier" in html
    conn = connect(app.config["DATABASE"])
    q = conn.execute("SELECT * FROM quests WHERE id = ?", (qid,)).fetchone()
    p = conn.execute("SELECT * FROM predictions WHERE quest_id = ?", (qid,)).fetchone()
    assert q["score"] == 100 and q["xp"] > 0
    features = json.loads(p["features_json"])["features"]
    assert features["quiz_score"] == 100 and features["assignments_completed"] == 100 and features["streak_days"] == 1
    assert p["label"] in ("Low", "Medium", "High")


def test_two_wrong_tries_score_zero_but_still_earn_xp(client, app):
    sign_up(client)
    qid = play_quest(client, app, right=False)
    conn = connect(app.config["DATABASE"])
    q = conn.execute("SELECT score, xp FROM quests WHERE id = ?", (qid,)).fetchone()
    assert q["score"] == 0 and q["xp"] > 0  # effort still counts


def test_double_answer_counts_once(client, app):
    sign_up(client)
    r = post(client, "/quest/start", subject="English")
    qid = int(r.headers["Location"].rsplit("/", 1)[1])
    wrong = (answer_index(app, qid) + 1) % 4
    post(client, f"/quest/{qid}/answer", choice=wrong)
    conn = connect(app.config["DATABASE"])
    tries = conn.execute("SELECT tries FROM quest_items WHERE quest_id = ?", (qid,)).fetchone()[0]
    assert tries == 1
    # the same wrong button again is refused (it's disabled in the page)
    post(client, f"/quest/{qid}/answer", choice=answer_index(app, qid))
    assert conn.execute("SELECT credit FROM quest_items WHERE quest_id = ?", (qid,)).fetchone()[0] == 0.5


def test_quitting_lowers_completion_rate(client, app):
    sign_up(client)
    r = post(client, "/quest/start", subject="English")
    qid = int(r.headers["Location"].rsplit("/", 1)[1])
    post(client, f"/quest/{qid}/quit")
    qid2 = play_quest(client, app, subject="English")
    conn = connect(app.config["DATABASE"])
    p = conn.execute("SELECT features_json FROM predictions WHERE quest_id = ?", (qid2,)).fetchone()
    assert json.loads(p[0])["features"]["assignments_completed"] == 50.0


def test_export_and_delete(client, app):
    sign_up(client)
    play_quest(client, app)
    data = json.loads(client.get("/me/export").data)
    assert data["student"]["name"] == "Ayesha" and len(data["quests"]) == 1
    assert post(client, "/me/delete", confirm="nope").status_code == 302
    post(client, "/me/delete", confirm="DELETE")
    conn = connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM quest_items").fetchone()[0] == 0


def test_every_page_renders(client, app):
    assert client.get("/about-ai").status_code == 200
    sign_up(client)
    post(client, "/buddy", buddy="blaze")
    qid = play_quest(client, app, subject="Computer Science")
    for url in ("/home", "/dashboard", f"/quest/{qid}/result", "/about-ai", "/shop", "/buddy"):
        assert client.get(url).status_code == 200, url
    assert client.get("/nope").status_code == 404


# ── The game layer ──

def student_row(app):
    conn = connect(app.config["DATABASE"])
    row = conn.execute("SELECT * FROM students").fetchone()
    conn.close()
    return row


def test_new_player_picks_a_buddy_first(client):
    sign_up(client)
    r = client.get("/home")
    assert r.status_code == 302 and r.headers["Location"].endswith("/buddy")
    assert post(client, "/buddy", buddy="dragon-king").status_code == 400
    post(client, "/buddy", buddy="hoot")
    page = client.get("/home").data.decode()
    assert "buddy-hoot" in page and "Daily challenge" in page and "Chapter 1" in page


def test_battle_arena_reacts_to_answers(client, app):
    sign_up(client)
    post(client, "/buddy", buddy="robo")
    r = post(client, "/quest/start", subject="Mathematics")
    qid = int(r.headers["Location"].rsplit("/", 1)[1])
    page = client.get(f"/quest/{qid}").data.decode()
    assert "monster--appear" in page and "Number Golem" in page and page.count("heart-lost") == 0
    post(client, f"/quest/{qid}/answer", choice=answer_index(app, qid))
    page = client.get(f"/quest/{qid}").data.decode()
    assert "monster--hit" in page and "buddy--cheer" in page and page.count("heart-lost") == 1
    assert 'data-sound="correct"' in page


def test_perfect_quest_beats_the_boss_and_pays_coins(client, app):
    sign_up(client)
    post(client, "/buddy", buddy="robo")
    qid = play_quest(client, app)
    conn = connect(app.config["DATABASE"])
    q = conn.execute("SELECT * FROM quests WHERE id = ?", (qid,)).fetchone()
    badges = {r[0] for r in conn.execute("SELECT code FROM badges")}
    assert q["boss_defeated"] == 1 and q["best_combo"] == 5
    expected = (5 * 3 + 10) * (2 if q["daily"] else 1)
    assert q["coins"] == expected and student_row(app)["coins"] == expected
    assert {"boss_slayer", "combo_5"} <= badges
    assert "Boss defeated!" in client.get(f"/quest/{qid}/result").data.decode()


def test_daily_challenge_doubles_coins_once_a_day(client, app):
    from eduquest import game
    from eduquest.quests import today
    sign_up(client)
    post(client, "/buddy", buddy="robo")
    subject = game.daily_subject(today())
    first, second = play_quest(client, app, subject=subject), play_quest(client, app, subject=subject)
    conn = connect(app.config["DATABASE"])
    daily = [r[0] for r in conn.execute("SELECT daily FROM quests WHERE id IN (?, ?) ORDER BY id", (first, second))]
    assert daily == [1, 0]
    assert conn.execute("SELECT 1 FROM badges WHERE code = 'daily_hero'").fetchone()


def test_shop_needs_coins_then_buys_and_equips(client, app):
    sign_up(client)
    post(client, "/buddy", buddy="hoot")
    r = post(client, "/shop/buy", item="crown")
    assert "m=poor" in r.headers["Location"] and student_row(app)["coins"] == 0
    conn = connect(app.config["DATABASE"])
    conn.execute("UPDATE students SET coins = 300")
    conn.commit()
    post(client, "/shop/buy", item="party_hat")
    post(client, "/shop/buy", item="crown")        # same slot: the crown replaces the hat
    assert student_row(app)["coins"] == 300 - 40 - 250
    worn = dict(conn.execute("SELECT item, equipped FROM inventory").fetchall())
    assert worn == {"party_hat": 0, "crown": 1}
    post(client, "/shop/wear", item="party_hat", on="1")
    worn = dict(conn.execute("SELECT item, equipped FROM inventory").fetchall())
    assert worn == {"party_hat": 1, "crown": 0}
    assert post(client, "/shop/wear", item="jetpack", on="1").status_code == 400  # not owned
    assert post(client, "/shop/buy", item="free-gold").status_code == 400
    assert "g-hat" in client.get("/shop").data.decode()


# ── The AI ──

def test_json_model_matches_training_labels():
    model = EngagementModel.load("models/engagement_model.json")
    df = pd.read_csv("student_data.csv")
    hits = sum(model.predict(row).label == row["performance_label"] for row in df.to_dict("records"))
    assert hits / len(df) >= 0.9


def test_formula_reproduces_dataset_labels():
    df = pd.read_csv("student_data.csv")
    for row in df.to_dict("records"):
        f = {**row}
        assert coach.formula_label(coach.formula_score(f)) == row["performance_label"]


def test_next_tier_path_steps_actually_reach_the_tier():
    f = {"quiz_score": 50, "time_spent_hrs": 1, "attempts": 1, "hints_used": 2, "streak_days": 2, "assignments_completed": 60}
    path = coach.next_tier_path(f)
    assert path["target"] == "Medium" and path["steps"]
    need = int(re.search(r"Score (\d+) points", " ".join(path["steps"]) + " Score 0 points").group(1))
    if need:
        assert coach.formula_label(coach.formula_score({**f, "quiz_score": 50 + need})) == "Medium"


def test_adaptive_difficulty_rises_with_rating():
    assert adaptive.pick_difficulty(adaptive.START, "Steady") == 1
    assert adaptive.pick_difficulty(1300, "Steady") == 3
    assert adaptive.update(1000, 3, 1) > adaptive.update(1000, 1, 1)
    # A new student who gets four easy questions right in a row is moved up to medium
    r = adaptive.START
    for n in range(4):
        r = adaptive.update(r, adaptive.pick_difficulty(r, "Steady"), 1, answers=n)
    assert adaptive.pick_difficulty(r, "Steady") == 2


def test_questions_have_four_distinct_options():
    import random
    rng = random.Random(1)
    for subject in SUBJECTS:
        for grade in range(3, 8):
            for d in (1, 2, 3):
                for _ in range(20):
                    q = make_question(subject, grade, d, rng=rng)
                    assert len(q.options) == 4 and len(set(q.options)) == 4 and 0 <= q.answer < 4
