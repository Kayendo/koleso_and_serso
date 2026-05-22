"""Корона: pending не теряется при ошибочном подтверждении."""

from backend.items.gameplay import activate_buff_for_next_game
from backend.turn_actions import (
    _pending_crown_pick,
    _pending_wheel,
    confirm_wheel_for_user,
    spin_wheel_for_user,
)
from backend.models import db

from tests.conftest import player, reset_player


def test_crown_pending_survives_bad_confirm(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        activate_buff_for_next_game(u.id, "wheel_crown_pick", item_id=8, label="Корона")
        _pending_wheel[u.id] = ["A", "B", "C", "D"]
        u.turn_phase = "wheel"
        db.session.commit()

        from unittest.mock import patch

        with patch("backend.turn_actions.randbelow", return_value=1):
            spin_wheel_for_user(u)

        assert u.id in _pending_crown_pick

        bad = confirm_wheel_for_user(u, {"selectedGame": "Несуществующая"})
        assert (bad[0] if isinstance(bad, tuple) else bad).get("error")
        assert u.id in _pending_crown_pick

        good = confirm_wheel_for_user(
            u, {"crownChoiceIndex": 0, "selectedGame": "A"}
        )
        payload = good[0] if isinstance(good, tuple) else good
        assert payload.get("game")
        assert u.id not in _pending_crown_pick


def test_crown_confirm_by_game_title(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        activate_buff_for_next_game(u.id, "wheel_crown_pick", item_id=8, label="Корона")
        _pending_wheel[u.id] = ["A", "B", "C", "D"]
        u.turn_phase = "wheel"
        db.session.commit()

        from unittest.mock import patch

        with patch("backend.turn_actions.randbelow", return_value=1):
            spin_wheel_for_user(u)

        ok = confirm_wheel_for_user(u, {"selectedGame": "B"})
        payload = ok[0] if isinstance(ok, tuple) else ok
        assert payload.get("game")
        assert u.id not in _pending_crown_pick
