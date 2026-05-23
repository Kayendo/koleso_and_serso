"""Фикстуры для автотестов Kolesoblya."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URI", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("COMMENTATOR_ENABLED", "0")
os.environ.setdefault("AI_COMMENTATOR_ENABLED", "0")

from backend.accounts import PLAYER_ACCOUNTS
from backend.app import create_app
from backend.models import PlayerModifier, User, db


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{db_file}")
    application = create_app()
    application.config["TESTING"] = True

    def _noop(*_a, **_k):
        return None

    application.extensions["socketio"].start_background_task = _noop

    with application.app_context():
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, username: str, password: str):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


@pytest.fixture
def player_client(client):
    acc = PLAYER_ACCOUNTS[0]
    r = _login(client, acc["username"], acc["password"])
    assert r.status_code == 200
    return client


@pytest.fixture
def second_player(client, app):
    with app.app_context():
        return User.query.filter_by(username=PLAYER_ACCOUNTS[1]["username"]).first()


@pytest.fixture
def actor(app):
    with app.app_context():
        return User.query.filter_by(username=PLAYER_ACCOUNTS[0]["username"]).first()


def grant_item(user_id: int, item_id: int, qty: int = 1) -> None:
    from backend.items.inventory import grant_inventory_item

    grant_inventory_item(user_id, item_id, qty)


def use_item_api(
    client,
    item_id: int,
    *,
    target_username: str | None = None,
    partner_username: str | None = None,
    partner_user_id: int | None = None,
    mode: str | None = None,
):
    body = {"itemId": item_id}
    if target_username:
        body["targetUsername"] = target_username
    if partner_username:
        body["partnerUsername"] = partner_username
    if partner_user_id is not None:
        body["partnerUserId"] = partner_user_id
    if mode:
        body["mode"] = mode
    return client.post("/api/inventory/use", json=body)


def mod_keys(user_id: int) -> set[str]:
    return {
        m.effect_key
        for m in PlayerModifier.query.filter_by(user_id=user_id).all()
        if m.turns_remaining != 0
    }


def reset_player(user: User, *, phase: str = "idle", position: int = 0) -> None:
    user.turn_phase = phase
    user.position = position
    user.in_durka = False
    user.points = 10
    db.session.commit()


def player(username: str) -> User:
    u = User.query.filter_by(username=username).first()
    assert u
    return u
