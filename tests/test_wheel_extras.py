"""Доп. колёса приколов (бандит, лепрекон)."""

import pytest

from backend.items.wheel_extras import (
    add_extra_wheel_spins,
    consume_one_extra_wheel_spin,
    extra_wheel_spins_left,
    finish_extra_wheel_chain,
    open_extra_item_wheel,
)
from backend.models import User
from backend.pending_wheels import pending_item_wheel, save_resume_phase

from tests.conftest import player, reset_player


def test_extra_spins_consume_per_wheel(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        add_extra_wheel_spins(u.id, 2, label="тест")
        assert extra_wheel_spins_left(u.id) == 2

        payload = open_extra_item_wheel(u, cell_name="Кайфарик", dice_label="6")
        assert payload is not None
        assert payload["openExtraWheel"]
        assert extra_wheel_spins_left(u.id) == 1
        assert u.id in pending_item_wheel
        assert u.turn_phase == "wheel"

        consume_one_extra_wheel_spin(u.id)
        assert extra_wheel_spins_left(u.id) == 0


def test_bandit_grants_wheel_spins_not_turn_ticks(app):
    with app.app_context():
        from backend.items.gameplay import NO_TICK_ON_TURN
        from backend.items.instant import apply_instant_wheel_effect
        from backend.items.catalog import get_item
        from backend.items.effects import EffectContext
        from backend.items.inventory import grant_inventory_item
        from backend.models import PlayerInventoryItem, PlayerModifier

        u = player("andryuha")
        reset_player(u)
        grant_inventory_item(u.id, 6, 1)
        grant_inventory_item(u.id, 7, 1)
        item = get_item(26)
        ctx = EffectContext(user_id=u.id, item=item, actor_username=u.username)
        apply_instant_wheel_effect(ctx, u)
        mod = PlayerModifier.query.filter_by(
            user_id=u.id, effect_key="wheel_extra_spins"
        ).first()
        assert mod is not None
        assert mod.turns_remaining == 2
        assert "wheel_extra_spins" in NO_TICK_ON_TURN


def test_finish_extra_chain_on_game_cell_goes_idle(app):
    """После доп. колёс на игровой клетке нельзя снова роллить без кубика."""
    with app.app_context():
        u = player("andryuha")
        reset_player(u, phase="wheel_ready", position=5)
        add_extra_wheel_spins(u.id, 2, label="Лепреконий схрон")
        consume_one_extra_wheel_spin(u.id)
        consume_one_extra_wheel_spin(u.id)
        assert extra_wheel_spins_left(u.id) == 0
        finish_extra_wheel_chain(u)
        assert u.turn_phase == "idle"


def test_finish_extra_chain_restores_playing(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u, phase="wheel_ready", position=5)
        save_resume_phase(u.id, "playing")
        add_extra_wheel_spins(u.id, 1, label="бандит")
        consume_one_extra_wheel_spin(u.id)
        restored = finish_extra_wheel_chain(u)
        assert restored == "playing"
        assert u.turn_phase == "playing"


@pytest.mark.parametrize("item_id,expected_spins", [(29, 2), (30, 3)])
def test_stash_items_only_grant_extra_spins(app, actor, item_id, expected_spins):
    """Лепреконий схрон и Заначка — только доп. колёса приколов."""
    with app.app_context():
        from backend.items.admin_wheel import get_active_admin_wheel
        from backend.items.instant import apply_instant_wheel_effect
        from backend.items.catalog import get_item
        from backend.items.effects import EffectContext
        from backend.pending_wheels import pending_admin_wheel

        reset_player(actor, phase="wheel", position=8)
        item = get_item(item_id)
        ctx = EffectContext(
            user_id=actor.id, item=item, actor_username=actor.username
        )
        apply_instant_wheel_effect(ctx, actor)
        assert extra_wheel_spins_left(actor.id) == expected_spins
        assert not get_active_admin_wheel(actor.id)
        assert actor.id not in pending_admin_wheel
        assert actor.turn_phase == "wheel_ready"
