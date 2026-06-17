"""Ловушки, авто-заряд Рэмбо, штраф за старт после дурки."""

from backend.items.catalog import get_item
from backend.items.gameplay import tick_buffs_after_game
from backend.items.inventory import charges_per_unit, grant_inventory_item, has_item
from backend.models import User
from backend.services.turn_service import apply_start_bonus, mark_durka_drop_lap, send_to_durka


def _mods(user_id):
    from backend.models import PlayerModifier

    return [m.effect_key for m in PlayerModifier.query.filter_by(user_id=user_id).all()]


def test_fisting_trap_one_charge(app, actor):
    with app.app_context():
        item = get_item(19)
        assert item is not None
        assert charges_per_unit(19) == 1
        grant_inventory_item(actor.id, 19, 1)
        from backend.items.inventory import PlayerInventoryItem

        row = PlayerInventoryItem.query.filter_by(
            user_id=actor.id, item_def_id=19
        ).first()
        assert row.charges_remaining == 1


def test_rambo_auto_reapply_second_charge(app, actor):
    with app.app_context():
        from backend.items.use import use_inventory_item

        grant_inventory_item(actor.id, 4, 1)
        use_inventory_item(actor, 4)
        assert "rambo_band" in _mods(actor.id)
        notes = tick_buffs_after_game(actor.id)
        assert "rambo_band" not in _mods(actor.id)
        assert any("следующую игру" in n for n in notes)
        assert "rambo_band" in _mods(actor.id)


def test_no_start_bonus_after_durka_drop(app, actor):
    with app.app_context():
        actor.points = 10
        send_to_durka(actor)
        assert actor.no_start_bonus_lap is True
        bonus = apply_start_bonus(actor, passed=True)
        assert bonus == 0
        assert actor.points == 10
        assert actor.no_start_bonus_lap is False


def test_start_bonus_normal_without_durka_flag(app, actor):
    with app.app_context():
        from backend.config import PASS_START_POINTS

        actor.points = 0
        actor.no_start_bonus_lap = False
        bonus = apply_start_bonus(actor, passed=True)
        assert bonus == PASS_START_POINTS
        assert actor.points == PASS_START_POINTS
