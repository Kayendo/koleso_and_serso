"""«Ой, извините» на колесе подлянки."""

from backend.items.wheel import pick_wheel_items
from backend.turn_actions import (
    _pending_item_wheel,
    _pending_oops_pick,
    confirm_wheel_for_user,
    open_wheel_for_user,
    spin_wheel_for_user,
)
from backend.models import User, db

from tests.conftest import player, reset_player


def _noop_emit(event, payload):
    pass


def test_oops_pick_on_item_wheel(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        from backend.board import BOARD_BY_ID

        for cid, cell in BOARD_BY_ID.items():
            if cell.cell_type == "trap_joy":
                u.position = cid
                break
        u.turn_phase = "wheel_ready"
        db.session.commit()

        items = [
            {"id": i, "name": f"Item{i}", "wheelLabel": f"#{i}"}
            for i in range(1, 9)
        ]
        items[3] = {"id": 32, "name": "Ой, извините", "wheelLabel": "#32 Ой"}
        _pending_item_wheel[u.id] = items

        _pending_item_wheel[u.id] = items
        u.turn_phase = "wheel"
        db.session.commit()

        from unittest.mock import patch

        with patch("backend.turn_actions.randbelow", return_value=3):
            result = spin_wheel_for_user(u)
        assert int(items[3]["id"]) == 32

        assert result.get("oopsPick")
        assert u.id in _pending_oops_pick
        assert not result.get("selectedItemId")

        bad = confirm_wheel_for_user(u, {"wheelType": "item", "selectedItemId": 32})
        assert bad[0].get("error") if isinstance(bad, tuple) else bad.get("error")
        assert u.id in _pending_oops_pick

        good = confirm_wheel_for_user(
            u, {"wheelType": "item", "oopsChoiceIndex": 0}
        )
        payload = good[0] if isinstance(good, tuple) else good
        assert payload.get("item") or payload.get("factors")
