"""Восстановление колеса после перезагрузки (фаза wheel)."""

from backend.turn_actions import _pending_wheel, open_wheel_for_user
from backend.models import db

from tests.conftest import player, reset_player


def test_open_wheel_recovers_pending_games(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.turn_phase = "wheel"
        _pending_wheel[u.id] = ["Game A", "Game B", "Game C"]
        db.session.commit()

        out = open_wheel_for_user(u)
        payload = out[0] if isinstance(out, tuple) else out
        assert payload.get("recovered") is True
        assert payload.get("wheel") == ["Game A", "Game B", "Game C"]
        assert u.turn_phase == "wheel"
