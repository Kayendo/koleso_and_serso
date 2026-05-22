"""Выдача предметов из админки."""

from backend.items.effects import grant_item_to_player
from backend.items.inventory import has_item

from tests.conftest import mod_keys, player, reset_player


def test_admin_grant_huubik_activates_and_stays_in_inventory(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        notes = grant_item_to_player(u, 2, 1)
        assert has_item(u.id, 2)
        assert "huubik_dice_ready" in mod_keys(u.id)
        assert any("хуюбик" in n.lower() or "активирован" in n.lower() for n in notes)
