"""EduQuest AI: a gamified learning platform for grades 3 to 7."""
import os
from datetime import timedelta

from flask import Flask, render_template

from . import db, security
from .ai.model import EngagementModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(test_config=None):
    app = Flask(__name__, instance_path=os.path.join(ROOT, "instance"))
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "eduquest.db"),
        MODEL_PATH=os.path.join(ROOT, "models", "engagement_model.json"),
        QUEST_LENGTH=5,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("EDUQUEST_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=32 * 1024,
    )
    app.config.update(test_config or {})
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = security.load_secret_key(app.instance_path)

    db.init_app(app)
    security.init_app(app)
    app.extensions["engagement_model"] = EngagementModel.load(app.config["MODEL_PATH"])

    from . import auth, dashboard, quests
    app.register_blueprint(auth.bp)
    app.register_blueprint(quests.bp)
    app.register_blueprint(dashboard.bp)

    for code, title in {400: "That didn't work", 403: "Not allowed", 404: "Page not found",
                        413: "That was too much", 429: "Slow down", 500: "Something broke"}.items():
        app.register_error_handler(code, _error_page(code, title))
    return app


def _error_page(code, title):
    def handler(error):
        description = getattr(error, "description", None) if code != 500 else None
        return render_template("error.html", code=code, title=title, description=description), code
    return handler
