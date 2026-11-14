"""CSRF protection, security headers, the secret key and a small rate limiter."""
import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from flask import abort, request, session

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data:",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'none'",
    "object-src 'none'",
])


def load_secret_key(instance_path):
    """EDUQUEST_SECRET_KEY if set, otherwise a random key kept in instance/secret_key."""
    if os.environ.get("EDUQUEST_SECRET_KEY"):
        return os.environ["EDUQUEST_SECRET_KEY"]
    path = os.path.join(instance_path, "secret_key")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        key = secrets.token_hex(32)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(key)
        return key


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


class RateLimiter:
    """Counts failures per key in a sliding window (in memory, so per process)."""

    def __init__(self, limit, window_s):
        self.limit, self.window = limit, window_s
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def _trim(self, key):
        q, cutoff = self.hits[key], time.monotonic() - self.window
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def blocked(self, *keys):
        with self.lock:
            return any(len(self._trim(k)) >= self.limit for k in keys)

    def fail(self, *keys):
        with self.lock:
            for k in keys:
                self._trim(k).append(time.monotonic())

    def reset(self, *keys):
        with self.lock:
            for k in keys:
                self.hits.pop(k, None)


def init_app(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
            expected = session.get("_csrf", "")
            if not sent or not hmac.compare_digest(sent.encode(), expected.encode()):
                abort(400, description="This page was open too long. Go back, reload it and try again.")

    @app.after_request
    def set_headers(response):
        h = response.headers
        h.setdefault("Content-Security-Policy", CSP)
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.endpoint != "static":
            # Pages show a child's results: keep them out of shared caches and the back-forward cache
            h["Cache-Control"] = "no-store"
        if app.config.get("SESSION_COOKIE_SECURE"):
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
