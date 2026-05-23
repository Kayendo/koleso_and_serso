"""Корона колесного короля: не снимается после броска кубика."""

from backend.items.gameplay import activate_buff_for_next_game
from backend.items.modifiers import _has_mod
from backend.services.turn_service import roll_dice
from backend.turn_actions import roll_dice_for_user
from backend.items.inventory import tick_modifiers_after_turn

from tests.conftest import mod_keys, reset_player


def test_crown_survives_dice_roll_and_tick(app, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id,
            "wheel_crown_pick",
            item_id=8,
            label="Корона",
            turns=1,
        )
        d1, d2, _ = roll_dice()
        from backend.items.modifiers import apply_dice_roll

        apply_dice_roll(actor, d1, d2)
        tick_modifiers_after_turn(actor.id)
        assert "wheel_crown_pick" in mod_keys(actor.id)


def test_crown_survives_full_roll_flow(app, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id,
            "wheel_crown_pick",
            item_id=8,
            label="Корона",
            turns=1,
        )
        result = roll_dice_for_user(actor, {})
        assert "error" not in result
        assert result.get("rawDice")
        assert result["rawDice"][0] + result["rawDice"][1] == sum(result["rawDice"])
        assert "wheel_crown_pick" in mod_keys(actor.id)
