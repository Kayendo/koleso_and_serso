"""Шоколад, бандит во время игры."""

from backend.items.effects import grant_item_to_player
from backend.items.instant import apply_instant_wheel_effect
from backend.items.catalog import get_item
from backend.items.effects import EffectContext
from backend.items.wheel_extras import extra_wheel_spins_left
from backend.models import db
from backend.pending_wheels import consume_chocolate_genre, set_chocolate_genre
from backend.services.scoring import points_for_totem
from backend.services.turn_service import create_player_game
from backend.turn_actions import open_wheel_for_user

from tests.conftest import grant_item, player, reset_player
from tests.test_all_items import _instant, _use


def test_chocolate_use_sets_genre_for_wheel(app, actor):
    with app.app_context():
        reset_player(actor)
        actor.turn_phase = "wheel_ready"
        actor.position = 5
        db.session.commit()
        grant_item(actor.id, 15)
        _use(actor, 15, genreId=3)
        assert consume_chocolate_genre(actor.id) == 3

        actor.turn_phase = "wheel_ready"
        db.session.commit()
        set_chocolate_genre(actor.id, 3)
        payload = open_wheel_for_user(actor)
        assert "error" not in payload
        assert payload["source"]["genreId"] == 3
        assert payload["source"].get("chocolateOverride")
        assert len(payload["wheel"]) > 0


def test_chocolate_wrong_phase_rejected(app, actor):
    with app.app_context():
        reset_player(actor)
        actor.turn_phase = "idle"
        db.session.commit()
        grant_item(actor.id, 15)
        from backend.items.use import use_inventory_item

        data, code = use_inventory_item(actor, 15, options={"genreId": 1})
        assert code == 400
        assert "кубика" in data["error"]


def test_admin_grant_law_goes_to_inventory(app, actor):
    with app.app_context():
        reset_player(actor)
        from backend.items.admin_wheel import get_active_admin_wheel
        from backend.items.inventory import has_item

        notes = grant_item_to_player(actor, 40, source="админ")
        assert has_item(actor.id, 40)
        assert not get_active_admin_wheel(actor.id)
        assert any("инвентар" in n.lower() for n in notes)


def test_bandit_during_playing_keeps_phase(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 6)
        create_player_game(actor, "Bandit", actor.position, "2+2")
        actor.turn_phase = "playing"
        db.session.commit()
        from backend.items.wheel import apply_wheel_result
        from backend.items.wheel_extras import extra_wheel_spins_left
        from backend.pending_wheels import pop_resume_phase

        apply_wheel_result(actor, 26, dice_label="2+2", cell_name="Кайфарик")
        assert extra_wheel_spins_left(actor.id) == 1
        assert actor.turn_phase == "wheel_ready"
        assert pop_resume_phase(actor.id) == "playing"


def test_totem_14_3_hours(app):
    with app.app_context():
        assert points_for_totem(14.3, None) == 4
