"""Законы из инвентаря: бафф → категория слева → ролл."""

from backend.items.admin_wheel import get_active_admin_wheel
from backend.items.use import use_inventory_item
from backend.models import db

from tests.conftest import grant_item, mod_keys, reset_player


def test_law_use_sets_buff_without_genre(app, actor):
    with app.app_context():
        reset_player(actor, phase="wheel_ready", position=5)
        db.session.commit()
        grant_item(actor.id, 40)
        use_inventory_item(actor, 40)
        assert "chat_law_buff" in mod_keys(actor.id)
        fx = get_active_admin_wheel(actor.id)
        assert fx and fx.get("itemId") == 40
        assert fx.get("genreId") is None
