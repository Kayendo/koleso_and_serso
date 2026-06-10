"""Взрывчатка: 2 заряда, монетка при использовании баффа."""

from backend.items.effects import grant_item_to_player
from backend.items.inventory import grant_inventory_item
from backend.items.use import use_inventory_item
from backend.models import PlayerInventoryItem, User, db

from tests.conftest import player, reset_player


def test_explosives_grants_two_charges(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_item_to_player(u, 7, auto_activate_debuff=False)
        row = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=7).first()
        assert row is not None
        assert row.quantity == 1
        assert row.charges_remaining == 2


def test_explosives_consumes_both_on_fail(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_inventory_item(u.id, 7, 2)
        grant_inventory_item(u.id, 6, 1)
        result = use_inventory_item(u, 6, options={"coinSide": "no"})
        assert result.get("explosivesRoll") == "exploded"
        assert result.get("explosivesMessage") == "ВЫ ВЗОРВАЛИСЬ"
        exp = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=7).first()
        assert exp is not None
        assert exp.quantity == 2
        assert exp.charges_remaining == 3
        orb = PlayerInventoryItem.query.filter_by(user_id=u.id, item_def_id=6).first()
        assert orb is None
