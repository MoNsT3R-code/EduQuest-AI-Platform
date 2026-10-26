import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eduquest import auth, create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    auth.limiter.hits.clear()
    auth.device_limiter.hits.clear()
    return create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


def token(client):
    client.get("/")
    with client.session_transaction() as s:
        return s["_csrf"]


def sign_up(client, name="Ayesha", grade=5, pics=("lion", "rocket", "apple")):
    return client.post("/", data={
        "csrf_token": token(client), "mode": "new", "name": name, "grade": grade,
        "pic_first": pics[0], "pic_second": pics[1], "pic_third": pics[2]})


def post(client, url, **data):
    with client.session_transaction() as s:
        t = s.get("_csrf")
    if t is None:
        client.get("/home")
        with client.session_transaction() as s:
            t = s["_csrf"]
    return client.post(url, data={"csrf_token": t, **data})
