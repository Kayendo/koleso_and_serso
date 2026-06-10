"""Количество предметов и зарядов в инвентаре — разные величины."""

from backend.items.inventory import (
    consume_inventory_item,
    get_inventory_state,
    grant_inventory_item,
)
from backend.models import PlayerInventoryItem

from tests.conftest import player, reset_player


def test_one_explosive_is_one_item_two_charges(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_inventory_item(u.id, 7, 1)
        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=7).first()
        assert row.quantity == 1
        assert row.charges_remaining == 2

        state = get_inventory_state(u.id)
        assert state["items"][0]["quantity"] == 1
        assert state["items"][0]["charges"] == 2
        assert state["items"][0]["chargesPerUnit"] == 2


def test_two_explosives_four_charges_consume_one_by_one(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_inventory_item(u.id, 7, 2)
        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=7).first()
        assert row.quantity == 2
        assert row.charges_remaining == 4

        assert consume_inventory_item(u.id, 7, 1)
        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=7).first()
        assert row.quantity == 2
        assert row.charges_remaining == 3

        assert consume_inventory_item(u.id, 7, 1)
        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=7).first()
        assert row.quantity == 1
        assert row.charges_remaining == 2
