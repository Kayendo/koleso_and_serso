"""Бросок кубика: читерский, троица, кольца."""

from __future__ import annotations

from backend.items.gameplay import activate_buff_for_next_game
from backend.items.inventory import grant_inventory_item
from backend.items.modifiers import _has_mod, apply_dice_roll
from backend.models import User, db
from backend.turn_actions import (
    _pending_dice_choice,
    confirm_dice_physics_for_user,
    confirm_dice_roll_for_user,
    roll_dice_for_user,
)

from tests.conftest import grant_item, mod_keys, reset_player, use_item_api


def test_cheat_dice_roll_then_replace(app, player_client, actor, second_player):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 1)
        r = use_item_api(player_client, 1)
        assert r.status_code == 200
        assert "cheat_dice_ready" in mod_keys(actor.id)

        result = roll_dice_for_user(actor, {})
        assert result.get("awaitingPhysics") is True
        assert "awaitingCheat" not in result
        assert "steps" not in result
        assert actor.turn_phase == "rolling"

        cheat_pending = confirm_dice_physics_for_user(actor, {"dice": [2, 3]})
        assert cheat_pending.get("awaitingCheat") is True
        assert cheat_pending["dice"] == [2, 3]
        assert "steps" not in cheat_pending
        assert actor.turn_phase == "dice_choice"
        assert actor.id in _pending_dice_choice

        result2 = confirm_dice_roll_for_user(
            actor, {"cheatDie": 1, "cheatValue": 6}
        )
        assert "steps" in result2
        assert result2["dice"] == [6, 3]
        assert _has_mod(actor.id, "cheat_dice_ready") is None
        _pending_dice_choice.pop(actor.id, None)


def test_cheat_replaces_die_value(app, player_client, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id, "cheat_dice_ready", item_id=1, label="Чит"
        )
        _pending_dice_choice[actor.id] = {
            "d1": 2,
            "d2": 3,
            "type": "cheat",
            "dice": [2, 3],
        }
        actor.turn_phase = "dice_choice"
        db.session.commit()
        result = confirm_dice_roll_for_user(
            actor, {"cheatDie": 2, "cheatValue": 6}
        )
        assert result["dice"] == [2, 6]
        assert result["steps"] == 8


def test_trinity_requires_pick(app, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id, "trinity_dice", item_id=37, label="Троица"
        )
        result = roll_dice_for_user(actor, {})
        assert result.get("awaitingPhysics") is True
        assert result.get("diceCount") == 3
        assert "steps" not in result
        assert actor.turn_phase == "rolling"

        tri_pending = confirm_dice_physics_for_user(actor, {"dice": [2, 4, 6]})
        assert tri_pending.get("awaitingTrinityPick") is True
        assert tri_pending["dice"] == [2, 4, 6]
        assert "steps" not in tri_pending
        assert actor.turn_phase == "dice_choice"

        from backend.turn_actions import reveal_trinity_dice_for_user

        revealed = reveal_trinity_dice_for_user(actor)
        assert len(revealed["dice"]) == 3

        final = confirm_dice_roll_for_user(actor, {"trinityPick": [2, 4]})
        assert "steps" in final
        assert final["steps"] == 6
        assert _has_mod(actor.id, "trinity_dice") is None


def test_huubik_bigger_die_becomes_one(app, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id, "huubik_dice_ready", item_id=2, label="Хуюбик"
        )
        result = roll_dice_for_user(actor, {})
        assert result.get("awaitingPhysics") is True

        final = confirm_dice_physics_for_user(actor, {"dice": [5, 2]})
        assert final["dice"] == [1, 2]
        assert final["steps"] == 3
        assert _has_mod(actor.id, "huubik_dice_ready") is None


def test_huubik_not_applied_on_trinity_throw(app, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id, "trinity_dice", item_id=37, label="Троица"
        )
        activate_buff_for_next_game(
            actor.id, "huubik_dice_ready", item_id=2, label="Хуюбик"
        )
        roll_dice_for_user(actor, {})
        confirm_dice_physics_for_user(actor, {"dice": [5, 2, 1]})
        final = confirm_dice_roll_for_user(actor, {"trinityPick": [5, 2]})
        assert final["dice"] == [5, 2]
        assert final["steps"] == 7
        assert _has_mod(actor.id, "huubik_dice_ready") is not None


def test_time_rings_link_by_partner_username(
    app, player_client, actor, second_player
):
    with app.app_context():
        reset_player(actor)
        reset_player(second_player)
        grant_item(actor.id, 11, 4)
        r = use_item_api(
            player_client,
            11,
            partner_username=second_player.username,
        )
        assert r.status_code == 200, r.get_json()
        assert "time_ring_partner" in mod_keys(actor.id)
        assert "time_ring_partner" in mod_keys(second_player.id)


def test_time_rings_partner_user_id(app, player_client, actor, second_player):
    with app.app_context():
        reset_player(actor)
        reset_player(second_player)
        grant_item(actor.id, 11)
        r = use_item_api(
            player_client,
            11,
            partner_user_id=second_player.id,
        )
        assert r.status_code == 200
        assert "time_ring_partner" in mod_keys(actor.id)


def test_time_rings_adds_step(app, actor):
    with app.app_context():
        reset_player(actor)
        activate_buff_for_next_game(
            actor.id,
            "time_ring_partner",
            label="Кольца",
            turns=4,
        )
        d1, d2, steps, *_ = apply_dice_roll(actor, 2, 2)
        assert steps == 5
        ring = _has_mod(actor.id, "time_ring_partner")
        assert ring is not None
        assert ring.turns_remaining == 3


def test_time_rings_use_links_four_turns_each(app, actor, second_player):
    with app.app_context():
        from backend.items.modifiers import _has_mod
        from backend.items.use import use_inventory_item
        from backend.models import PlayerInventoryItem

        reset_player(actor)
        reset_player(second_player)
        grant_inventory_item(actor.id, 11, 1)
        result = use_inventory_item(
            actor,
            11,
            options={"partnerUserId": second_player.id},
        )
        assert result.get("ok")
        assert PlayerInventoryItem.query.filter_by(
            user_id=actor.id, item_def_id=11
        ).first() is None
        owner_ring = _has_mod(actor.id, "time_ring_partner")
        partner_ring = _has_mod(second_player.id, "time_ring_partner")
        assert owner_ring is not None
        assert partner_ring is not None
        assert owner_ring.turns_remaining == 4
        assert partner_ring.turns_remaining == 4
