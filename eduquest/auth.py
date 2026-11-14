"""Sign-in for children: a name, a grade and a picture password (three pictures in order).

Picture passwords are easier for 8-year-olds than typed ones, are hashed like any
password, and wrong guesses are rate-limited per device and per name.
"""
import functools
import re
import sqlite3

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, now
from .security import RateLimiter

bp = Blueprint("auth", __name__)

PICTURES = [
    ("lion", "🦁"), ("rocket", "🚀"), ("apple", "🍎"),
    ("ball", "⚽"), ("rainbow", "🌈"), ("turtle", "🐢"),
    ("star", "⭐"), ("guitar", "🎸"), ("pizza", "🍕"),
]
PICTURE_NAMES = {name for name, _ in PICTURES}
SLOTS = ("first", "second", "third")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{0,29}$")

# 5 wrong picture passwords per name, or 20 per device, in 10 minutes
limiter = RateLimiter(limit=5, window_s=600)
device_limiter = RateLimiter(limit=20, window_s=600)


@functools.cache
def _dummy_hash():
    return generate_password_hash("not-a-real-picture-password")


def name_key(name):
    return " ".join(name.split()).casefold()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.student is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@bp.before_app_request
def load_student():
    g.student = None
    sid = session.get("student_id")
    if sid is not None:
        g.student = get_db().execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
        if g.student is None:
            session.clear()


def _form_values():
    name = " ".join(request.form.get("name", "").split())
    try:
        grade = int(request.form.get("grade", ""))
    except ValueError:
        grade = None
    pics = [request.form.get(f"pic_{s}", "") for s in SLOTS]
    return name, grade, pics


def _validate(name, grade, pics):
    if not NAME_RE.match(name):
        return "Type your first name using letters (you can add an initial, like 'Ali K')."
    if grade not in range(3, 8):
        return "Pick your grade, from 3 to 7."
    if any(p not in PICTURE_NAMES for p in pics):
        return "Pick one picture in each of the three rows."
    return None


def _start_session(student_id):
    session.clear()          # a fresh session on every sign-in prevents session fixation
    session.permanent = True
    session["student_id"] = student_id


@bp.route("/", methods=["GET", "POST"])
def login():
    if g.student is not None and request.method == "GET":
        return redirect(url_for("quests.home"))
    if request.method == "GET":
        return render_template("login.html", pictures=PICTURES, slots=SLOTS, form={}, mode="return")

    name, grade, pics = _form_values()
    mode = "new" if request.form.get("mode") == "new" else "return"
    form = {"name": name, "grade": grade}
    error = _validate(name, grade, pics)
    key, device = f"name:{name_key(name)}:{grade}", f"ip:{request.remote_addr}"
    code = "-".join(pics)
    db = get_db()

    if not error and (limiter.blocked(key) or device_limiter.blocked(device)):
        return render_template("login.html", pictures=PICTURES, slots=SLOTS, form=form, mode=mode,
                               error="Too many tries. Wait 10 minutes, or ask your teacher for help."), 429

    if not error and mode == "new":
        try:
            with db:
                cur = db.execute(
                    "INSERT INTO students (name, name_key, grade, secret_hash, created_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, name_key(name), grade, generate_password_hash(code), now(), now()))
            _start_session(cur.lastrowid)
            return redirect(url_for("quests.home", welcome=1))
        except sqlite3.IntegrityError:
            error = f"Someone in Grade {grade} already uses the name {name}. Add your initial, like '{name} K'."

    if not error:
        row = db.execute("SELECT * FROM students WHERE name_key = ? AND grade = ?", (name_key(name), grade)).fetchone()
        # Check a hash even when the name is unknown, so timing doesn't reveal which names exist
        ok = check_password_hash(row["secret_hash"] if row else _dummy_hash(), code)
        if row is not None and ok:
            limiter.reset(key)
            with db:
                db.execute("UPDATE students SET last_seen_at = ? WHERE id = ?", (now(), row["id"]))
            _start_session(row["id"])
            return redirect(url_for("quests.home"))
        limiter.fail(key)
        device_limiter.fail(device)
        error = "We couldn't find that name, grade and pictures together. Check the order of your pictures."

    return render_template("login.html", pictures=PICTURES, slots=SLOTS, form=form, mode=mode, error=error), 400


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def require_owner(row):
    if row is None or row["student_id"] != g.student["id"]:
        abort(404)
    return row
