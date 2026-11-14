"""Choosing a buddy and the gear shop."""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from . import game, gamify
from .auth import login_required
from .db import get_db, now

bp = Blueprint("world", __name__)


@bp.app_context_processor
def player():
    """Buddy, gear, coins and level for every page (the nav shows coins)."""
    if getattr(g, "student", None) is None:
        return {"buddy": None}
    db, sid = get_db(), g.student["id"]
    xp = db.execute("SELECT COALESCE(SUM(xp), 0) FROM quests WHERE student_id = ?", (sid,)).fetchone()[0]
    level = gamify.level_for(xp)
    code = g.student["buddy"] or game.DEFAULT_BUDDY
    return {"buddy": {"code": code, **game.BUDDIES[code], "gear": game.equipped(db, sid),
                      "stage": game.stage_for(level["level"])},
            "coins": g.student["coins"], "player_level": level}


@bp.route("/buddy", methods=["GET", "POST"])
@login_required
def choose():
    if request.method == "POST":
        code = request.form.get("buddy")
        if code not in game.BUDDIES:
            abort(400, description="Pick one of the three buddies.")
        with get_db() as db:
            db.execute("UPDATE students SET buddy = ? WHERE id = ?", (code, g.student["id"]))
        return redirect(url_for("quests.home", met=code))
    return render_template("buddy.html", buddies=game.BUDDIES, first=g.student["buddy"] is None)


@bp.get("/shop")
@login_required
def shop():
    db = get_db()
    mine = game.owned(db, g.student["id"])
    items = [{"code": c, "slot": s, "name": n, "price": p, "owned": c in mine, "on": mine.get(c, False)}
             for c, (s, n, p) in game.ITEMS.items()]
    return render_template("shop.html", items=items, message=request.args.get("m"))


@bp.post("/shop/buy")
@login_required
def buy():
    code = request.form.get("item")
    if code not in game.ITEMS:
        abort(400, description="That item isn't in the shop.")
    slot, name, price = game.ITEMS[code]
    sid = g.student["id"]
    with get_db() as db:
        if code in game.owned(db, sid):
            return redirect(url_for("world.shop", m="owned"))
        # The WHERE clause makes the purchase atomic: no coins, no item
        cur = db.execute("UPDATE students SET coins = coins - ? WHERE id = ? AND coins >= ?", (price, sid, price))
        if not cur.rowcount:
            return redirect(url_for("world.shop", m="poor"))
        db.execute("UPDATE inventory SET equipped = 0 WHERE student_id = ? AND item IN (%s)"
                   % ",".join("?" * len(_same_slot(slot))), (sid, *_same_slot(slot)))
        db.execute("INSERT INTO inventory (student_id, item, equipped, bought_at) VALUES (?, ?, 1, ?)", (sid, code, now()))
        gamify.grant(db, sid, "shopper")
    return redirect(url_for("world.shop", m="bought") + "#buddy-preview")


@bp.post("/shop/wear")
@login_required
def wear():
    code = request.form.get("item")
    on = request.form.get("on") == "1"
    sid = g.student["id"]
    with get_db() as db:
        if code not in game.owned(db, sid):
            abort(400, description="You don't own that yet.")
        if on:
            slot = game.ITEMS[code][0]
            db.execute("UPDATE inventory SET equipped = 0 WHERE student_id = ? AND item IN (%s)"
                       % ",".join("?" * len(_same_slot(slot))), (sid, *_same_slot(slot)))
        db.execute("UPDATE inventory SET equipped = ? WHERE student_id = ? AND item = ?", (int(on), sid, code))
    return redirect(url_for("world.shop") + "#buddy-preview")


def _same_slot(slot):
    return [c for c, (s, _n, _p) in game.ITEMS.items() if s == slot]
