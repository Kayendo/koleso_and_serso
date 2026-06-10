"""Клетка «Дурка» без дропа: выбор направления."""

from backend.board import DURKA_CELL_ID
from backend.models import User, db
from backend.turn_actions import durka_step_for_user

from tests.conftest import player, reset_player


def test_landing_on_durka_sets_choice_phase(app):
    with app.app_context():
        from unittest.mock import patch

        from backend.turn_actions import _animate_and_finish

        u = player("andryuha")
        reset_player(u)
        u.position = 29
        u.turn_phase = "rolling"
        u.in_durka = False
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
        assert u.position == DURKA_CELL_ID
        assert u.turn_phase == "durka_choice"
        assert not u.in_durka


def test_durka_step_forward_opens_wheel(app):
    with app.app_context():
        from unittest.mock import patch

        u = player("andryuha")
        reset_player(u)
        u.position = DURKA_CELL_ID
        u.turn_phase = "durka_choice"
        u.in_durka = False
        db.session.commit()

        with patch("backend.turn_actions._emit"):
            result = durka_step_for_user(u, "forward")
        assert not isinstance(result, tuple), result
        assert result.get("wheel") or result.get("source")
        u = player("andryuha")
        assert u.position == 31
        assert u.turn_phase == "wheel"
