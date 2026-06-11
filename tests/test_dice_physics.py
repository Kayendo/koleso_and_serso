"""Физический бросок: confirm-dice-physics."""

from backend.turn_actions import (
    confirm_dice_physics_for_user,
    roll_dice_for_user,
)

from tests.conftest import reset_player


def test_roll_waits_for_physics_confirm(app, actor):
    with app.app_context():
        reset_player(actor)
        result = roll_dice_for_user(actor, {})
        assert result.get("awaitingPhysics") is True
        assert "steps" not in result
        assert actor.turn_phase == "rolling"

        finished = confirm_dice_physics_for_user(actor, {"dice": [4, 2]})
        assert finished["dice"] == [4, 2]
        assert finished["steps"] == 6
