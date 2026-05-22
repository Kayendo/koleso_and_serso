"""Колесо предметов: меньше повторов подряд."""

from backend.items.wheel import _recent_wheel_ids, pick_wheel_items

from tests.conftest import player, reset_player


def test_pick_wheel_avoids_recent_ids(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        first = pick_wheel_items(12, user_id=u.id)
        first_ids = {i.id for i in first}
        second = pick_wheel_items(12, user_id=u.id)
        second_ids = {i.id for i in second}
        overlap = first_ids & second_ids
        assert len(overlap) < 12
