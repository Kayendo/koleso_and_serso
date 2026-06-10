"""Админ-эффекты колеса: жанр → ролл игры → заглушка для админа."""

from backend.items.admin_item_grant import get_admin_item_grant
from backend.items.admin_wheel import get_active_admin_wheel
from backend.items.effects import apply_on_wheel_land
from backend.items.inventory import has_item
from backend.items.use import use_inventory_item
from backend.items.wheel import apply_wheel_result
from backend.models import db
from backend.turn_actions import confirm_wheel_for_user, open_wheel_for_user, spin_wheel_for_user

from tests.conftest import reset_player
from tests.test_all_items import _ctx


def test_law_wheel_drop_goes_to_inventory(app, actor):
    with app.app_context():
        reset_player(actor, position=3)
        ctx = _ctx(actor, 40)
        apply_on_wheel_land(ctx, actor, db)
        assert has_item(actor.id, 40)
        assert not get_active_admin_wheel(actor.id)


def test_law_wheel_drop_on_item_cell(app, actor):
    with app.app_context():
        reset_player(actor, position=8)
        ctx = _ctx(actor, 40)
        apply_on_wheel_land(ctx, actor, db)
        assert has_item(actor.id, 40)
        assert not get_active_admin_wheel(actor.id)


def test_law_apply_wheel_result_inventory(app, actor):
    with app.app_context():
        reset_player(actor, position=3)
        apply_wheel_result(actor, 41, dice_label="2+2", cell_name="Клетка")
        assert has_item(actor.id, 41)
        assert not get_active_admin_wheel(actor.id)


def test_shop_rerolls_item_wheel(app, actor):
    with app.app_context():
        reset_player(actor, position=8)
        from backend.items.wheel_extras import extra_wheel_spins_left
        from backend.pending_wheels import get_shop_repick

        apply_wheel_result(actor, 24, dice_label="2+2", cell_name="Кайфарик")
        repick = get_shop_repick(actor.id)
        assert repick and repick.get("mode") == "chat"
        assert extra_wheel_spins_left(actor.id) == 1
        assert not get_active_admin_wheel(actor.id)


def test_two_for_one_admin_pending(app, actor):
    with app.app_context():
        reset_player(actor, position=8)
        from backend.items.wheel_extras import extra_wheel_spins_left
        from backend.pending_wheels import has_two_for_one, pending_item_wheel
        from backend.turn_actions import _pending_item_wheel

        apply_wheel_result(actor, 23, dice_label="2+2", cell_name="Кайфарик")
        assert extra_wheel_spins_left(actor.id) == 1
        assert has_two_for_one(actor.id)

        items = [
            {"id": i, "name": f"It{i}", "wheelLabel": f"#{i}"}
            for i in range(1, 9)
        ]
        _pending_item_wheel[actor.id] = items
        actor.turn_phase = "wheel"
        db.session.commit()

        from unittest.mock import patch

        with patch("backend.turn_actions.randbelow", return_value=3):
            spin_wheel_for_user(actor)

        result = confirm_wheel_for_user(
            actor, {"wheelType": "item", "targetIndex": 3, "diceLabel": "2+2"}
        )
        payload = result[0] if isinstance(result, tuple) else result
        assert payload.get("adminItemGrantPending")
        grant = get_admin_item_grant(actor.id)
        assert grant
        sectors = grant.get("sectors") or []
        assert len(sectors) == 2
        assert {s.get("wheelIndex") for s in sectors} == {2, 4}
        assert 3 not in {s.get("wheelIndex") for s in sectors}
        assert actor.turn_phase == "idle"


def test_admin_wheel_flow_stub_game(app, actor):
    with app.app_context():
        from backend.models import PlayerGame

        reset_player(actor)
        actor.turn_phase = "wheel_ready"
        actor.position = 5
        db.session.commit()
        from tests.conftest import grant_item

        grant_item(actor.id, 41)
        use_inventory_item(actor, 41)
        assert get_active_admin_wheel(actor.id)
        assert "i_am_law_buff" in __import__(
            "tests.conftest", fromlist=["mod_keys"]
        ).mod_keys(actor.id)

        opened = open_wheel_for_user(actor, genre_id=2)
        assert opened.get("wheel")

        actor.turn_phase = "wheel"
        db.session.commit()
        result = confirm_wheel_for_user(
            actor,
            {"selectedGame": "Test Game X", "genreId": 2, "diceLabel": "3+4"},
        )
        payload = result[0] if isinstance(result, tuple) else result
        assert payload.get("adminWheelResolved")
        assert not get_active_admin_wheel(actor.id)
        game = PlayerGame.query.filter_by(user_id=actor.id).order_by(PlayerGame.id.desc()).first()
        assert game.status == "pending_admin"
        assert game.title == "Test Game X"
        assert not game.review
        assert game.rating is None
        assert actor.turn_phase == "playing"


def test_intrigue_grants_extra_wheel(app, actor):
    with app.app_context():
        reset_player(actor)
        from backend.items.wheel_extras import extra_wheel_spins_left

        apply_wheel_result(actor, 22, dice_label="2+2", cell_name="Кайфарик")
        assert extra_wheel_spins_left(actor.id) == 1
        assert actor.turn_phase == "wheel_ready"
