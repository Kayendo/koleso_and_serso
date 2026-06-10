"""Blazerd: выбор жанра и колесо игр."""

from backend.board import BOARD_BY_ID
from backend.models import User, db
from backend.turn_actions import open_wheel_for_user

from tests.conftest import player, reset_player

BLAZERD_CELL = next(c.id for c in BOARD_BY_ID.values() if c.company_key == "blazerd")


def test_blazerd_requires_genre_pick(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.position = BLAZERD_CELL
        u.turn_phase = "wheel_ready"
        db.session.commit()

        result = open_wheel_for_user(u)
        assert not isinstance(result, tuple), result
        assert result.get("needsGenrePick") is True
        assert len(result.get("genres") or []) == 9
        assert result["genres"][0].get("buttonLabel")


def test_blazerd_opens_wheel_with_genre(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.position = BLAZERD_CELL
        u.turn_phase = "wheel_ready"
        db.session.commit()

        result = open_wheel_for_user(u, genre_id=3)
        assert not isinstance(result, tuple), result
        assert result.get("wheel"), "колесо должно содержать игры"
        assert result["source"]["genreId"] == 3
        assert result["source"].get("needsGenrePick") is False
        assert result.get("blazerdGenreLabel")
        u = player("andryuha")
        assert u.turn_phase == "wheel"
