"""Повторная игра на колесе — рерол вместо принятия."""

from backend.models import PlayerGame, User, db
from backend.services.turn_service import create_player_game
from backend.turn_actions import confirm_wheel_for_user, spin_wheel_for_user

from tests.conftest import player, reset_player


def test_spin_marks_duplicate_game(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.position = 4
        game = create_player_game(u, "Portal 2", 4, "2+2")
        game.status = "completed"
        u.turn_phase = "wheel_ready"
        db.session.commit()

        from backend.turn_actions import open_wheel_for_user

        opened = open_wheel_for_user(u)
        assert not isinstance(opened, tuple), opened
        spin = spin_wheel_for_user(u)
        assert not isinstance(spin, tuple), spin
        if spin.get("selectedGame") == "Portal 2":
            assert spin.get("duplicateGame") is True


def test_confirm_rejects_duplicate_game(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        game = create_player_game(u, "Half-Life", u.position, "2+2")
        game.status = "completed"
        u.turn_phase = "wheel"
        db.session.commit()

        result = confirm_wheel_for_user(
            u, {"selectedGame": "Half-Life", "diceLabel": "2+2"}
        )
        assert isinstance(result, tuple)
        assert result[1] == 400
        assert result[0].get("duplicateGame") is True
