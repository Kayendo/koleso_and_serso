"""Ремонтный набор: +1 заряд выбранному предмету."""

from backend.items.use import use_inventory_item
from backend.models import PlayerInventoryItem, User, db

from tests.conftest import grant_item, player, reset_player


def test_repair_kit_adds_charge_to_cheat_dice(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_item(u.id, 9, 1)
        grant_item(u.id, 1, 1)
        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=1).first()
        assert row.quantity == 1
        assert row.charges_remaining == 1

        result = use_inventory_item(u, 9, options={"targetItemId": 1})
        assert "error" not in result

        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=1).first()
        assert row.quantity == 2
        assert row.charges_remaining == 2
        repair = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=9).first()
        assert repair is None
