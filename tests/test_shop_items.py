"""Магазины с чатом / Лепреконом: доп. колесо и выдача админом."""

from backend.items.admin_item_grant import get_admin_item_grant
from backend.items.use import use_inventory_item
from backend.items.wheel import apply_wheel_result
from backend.items.wheel_extras import extra_wheel_spins_left
from backend.models import TurnLog, db
from backend.pending_wheels import get_shop_repick, pending_item_wheel
from backend.turn_actions import confirm_wheel_for_user, spin_wheel_for_user

from tests.conftest import grant_item, reset_player


def test_shop_from_inventory_grants_extra_spin(app, actor):
    with app.app_context():
        reset_player(actor, phase="wheel_ready", position=5)
        grant_item(actor.id, 24)
        use_inventory_item(actor, 24)
        assert extra_wheel_spins_left(actor.id) == 1
        repick = get_shop_repick(actor.id)
        assert repick and repick.get("mode") == "chat"


def test_shop_drop_then_admin_grant_log(app, actor):
    with app.app_context():
        reset_player(actor, position=8)
        apply_wheel_result(actor, 25, dice_label="3+4", cell_name="Кайфарик")
        assert extra_wheel_spins_left(actor.id) == 1
        assert get_shop_repick(actor.id)

        items = [
            {"id": i, "name": f"It{i}", "wheelLabel": f"#{i}"}
            for i in range(1, 13)
        ]
        pending_item_wheel[actor.id] = items
        actor.turn_phase = "wheel"
        db.session.commit()

        from unittest.mock import patch

        with patch("backend.turn_actions.randbelow", return_value=4):
            spin_wheel_for_user(actor)

        result = confirm_wheel_for_user(
            actor,
            {
                "wheelType": "item",
                "shopChoiceIndexes": [0, 2],
                "diceLabel": "3+4",
            },
        )
        payload = result[0] if isinstance(result, tuple) else result
        assert payload.get("adminItemGrantPending")
        grant = get_admin_item_grant(actor.id)
        assert grant and grant.get("effectItemId") == 25
        assert len(grant.get("sectors") or []) == 2

        log = (
            TurnLog.query.filter_by(user_id=actor.id)
            .order_by(TurnLog.id.desc())
            .first()
        )
        assert log
        log_data = log.to_dict()
        assert "админ" in (log_data["summary"] or "").lower() or "ждёт" in (
            log_data["summary"] or ""
        ).lower()
        assert any(
            "выдаёт админ" in (f or "") for f in (log_data.get("factors") or [])
        )
