"""Дебафф с колеса: инвентарь + мгновенная активация."""

from backend.items.effects import EffectContext, apply_on_wheel_land
from backend.items.catalog import get_item
from backend.items.inventory import has_item
from backend.models import User, db

from tests.conftest import mod_keys, player, reset_player


def test_huubik_wheel_grants_inventory_and_activates(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        item = get_item(2)
        assert item
        ctx = EffectContext(user_id=u.id, item=item, actor_username=u.username)
        apply_on_wheel_land(ctx, u, db)
        assert has_item(u.id, 2)
        assert "huubik_dice_ready" in mod_keys(u.id)
