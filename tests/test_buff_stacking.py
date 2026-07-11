"""Повторное выпадение мгновенных эффектов колеса продлевает срок, а не дублирует бафф."""

from __future__ import annotations

from backend.items.gameplay import tick_buffs_after_game
from backend.items.instant import apply_instant_wheel_effect
from backend.items.modifiers import _has_mod
from backend.models import PlayerModifier
from tests.conftest import reset_player
from tests.test_all_items import _ctx


def _mods_count(user_id: int, key: str) -> int:
    return PlayerModifier.query.filter_by(user_id=user_id, effect_key=key).count()


def _instant_twice(app, actor, item_id: int) -> None:
    with app.app_context():
        reset_player(actor)
        apply_instant_wheel_effect(_ctx(actor, item_id), actor)
        apply_instant_wheel_effect(_ctx(actor, item_id), actor)


def test_hurry_stacks_duration(app, actor):
    with app.app_context():
        _instant_twice(app, actor, 36)
        assert _mods_count(actor.id, "hurry") == 1
        mod = _has_mod(actor.id, "hurry")
        assert mod is not None
        assert mod.turns_remaining == 2


def test_hour_growth_stacks_duration(app, actor):
    with app.app_context():
        _instant_twice(app, actor, 48)
        assert _mods_count(actor.id, "hour_growth") == 1
        mod = _has_mod(actor.id, "hour_growth")
        assert mod is not None
        assert mod.turns_remaining == 2


def test_base_only_stacks_duration(app, actor):
    with app.app_context():
        _instant_twice(app, actor, 47)
        assert _mods_count(actor.id, "base_only_next") == 1
        mod = _has_mod(actor.id, "base_only_next")
        assert mod is not None
        assert mod.turns_remaining == 2


def test_trinity_dice_stacks_duration(app, actor):
    with app.app_context():
        _instant_twice(app, actor, 37)
        assert _mods_count(actor.id, "trinity_dice") == 1
        mod = _has_mod(actor.id, "trinity_dice")
        assert mod is not None
        assert mod.turns_remaining == 2


def test_help_laggard_stacks_duration(app, actor):
    with app.app_context():
        _instant_twice(app, actor, 34)
        assert _mods_count(actor.id, "help_laggard") == 1
        mod = _has_mod(actor.id, "help_laggard")
        assert mod is not None
        assert mod.turns_remaining == 2


def test_stacked_hurry_ticks_once_per_game(app, actor):
    with app.app_context():
        _instant_twice(app, actor, 36)
        tick_buffs_after_game(actor.id)
        mod = _has_mod(actor.id, "hurry")
        assert mod is not None
        assert mod.turns_remaining == 1
        tick_buffs_after_game(actor.id)
        assert _has_mod(actor.id, "hurry") is None
