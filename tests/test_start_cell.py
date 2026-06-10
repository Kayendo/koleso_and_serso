"""Старт: повторный бросок кубика, без колеса игр."""

from backend.board import START_CELL_ID
from backend.models import User, db
from backend.services.turn_service import cell_game_source
from backend.turn_actions import open_wheel_for_user

from tests.conftest import player, reset_player


def test_start_cell_source_has_no_game_wheel(app):
    with app.app_context():
        src = cell_game_source(START_CELL_ID)
        assert src.get("startReroll") is True
        assert not src.get("genreId")
        assert not src.get("itemWheel")


def test_landing_on_start_sets_idle_not_wheel_ready(app):
    with app.app_context():
        from unittest.mock import patch

        from backend.turn_actions import _animate_and_finish

        u = player("andryuha")
        reset_player(u)
        u.position = 39
        u.turn_phase = "rolling"
        db.session.commit()

        with patch("backend.turn_actions._emit"):
            _animate_and_finish(
                u.id,
                1,
                "1+2",
                {"backward": False},
                [],
                app,
            )
        db.session.expire_all()
        u = player("andryuha")
        assert u.position == START_CELL_ID
        assert u.turn_phase == "idle"


def test_open_wheel_on_start_rejected(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.position = START_CELL_ID
        u.turn_phase = "wheel_ready"
        db.session.commit()

        result = open_wheel_for_user(u)
        assert isinstance(result, tuple)
        assert "старт" in result[0]["error"].lower()
        u = player("andryuha")
        assert u.turn_phase == "idle"
