"""Награда после прохождения: кубик 1–3 и колёса предметов."""

from backend.models import PlayerGame, User, db
from backend.reward_wheels import (
    _pending_reward_spins,
    confirm_reward_wheel_for_user,
    open_reward_wheel_for_user,
    roll_reward_dice_for_user,
    start_reward_item_wheels,
)
from backend.services.turn_service import create_player_game

from tests.conftest import player, reset_player


def _noop_emit(event, payload):
    pass


def test_complete_starts_reward_spins(app, player_client):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        game = create_player_game(u, "Reward Test", u.position, "2+2")
        game.review = "ok"
        game.rating = 8
        u.turn_phase = "playing"
        db.session.commit()

        r = player_client.post(
            f"/api/games/{game.id}/complete",
            json={"review": "ok", "rating": 8},
        )
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert 1 <= data["rewardItemSpins"] <= 3
        u = player("andryuha")
        assert data["user"]["turnPhase"] == "reward_items"
        assert u.turn_phase == "reward_items"


def test_reward_wheel_chain(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        start_reward_item_wheels(u, emit=_noop_emit)
        n = _pending_reward_spins[u.id]
        assert 1 <= n <= 3

        roll_reward_dice_for_user(u)
        for i in range(n):
            open_reward_wheel_for_user(u, emit=_noop_emit)
            items = __import__(
                "backend.reward_wheels", fromlist=["_pending_item_wheel_reward"]
            )._pending_item_wheel_reward.get(u.id, [])
            assert items
            confirm_reward_wheel_for_user(
                u,
                {"selectedItemId": items[0]["id"]},
                emit=_noop_emit,
            )

        assert _pending_reward_spins.get(u.id, 0) == 0
        u = player("andryuha")
        assert u.turn_phase == "idle"
