"""Туалетка: бафф при использовании, возврат на прошлую клетку при дропе."""

from backend.items.drop import handle_drop
from backend.items.effects import EffectContext, apply_item_effect
from backend.items.inventory import grant_inventory_item
from backend.items.modifiers import _has_mod
from backend.models import PlayerGame, User, db
from backend.services.turn_service import create_player_game

from tests.conftest import player, reset_player


def test_toilet_use_grants_buff(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_inventory_item(u.id, 16)
        from backend.items.catalog import get_item

        item = get_item(16)
        ctx = EffectContext(user_id=u.id, item=item, actor_username=u.username)
        apply_item_effect(ctx, u, db)
        assert _has_mod(u.id, "toilet_paper_ready")


def test_toilet_drop_returns_to_last_position(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.position = 5
        u.last_position = 3
        game = create_player_game(u, "Drop Me", 5, "2+2")
        u.turn_phase = "playing"
        db.session.commit()

        from backend.items.modifiers import _add_mod

        _add_mod(u.id, "toilet_paper_ready", "1", 1, item_id=16, label="Туалетка")
        factors = handle_drop(u, game, on_durka_cell=False, use_toilet=False)
        u = player("andryuha")
        assert u.position == 3
        assert u.turn_phase == "idle"
        assert u.in_durka is False
        assert any("Туалетка" in f for f in factors)
