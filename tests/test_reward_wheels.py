"""Награда после прохождения: кубик 1–3 и колёса предметов."""

from unittest.mock import patch

from backend.items.catalog import get_item
from backend.models import PlayerGame, User, db
from backend.reward_wheels import (
    confirm_reward_wheel_for_user,
    hydrate_reward_state,
    open_reward_wheel_for_user,
    reward_spins_left,
    roll_reward_dice_for_user,
    start_reward_item_wheels,
)
from backend.services.turn_service import create_player_game

from tests.conftest import player, reset_player


def _noop_emit(event, payload):
    pass


def _stable_reward_wheel(*_args, **_kwargs):
    """Предсказуемые сектора без мгновенных доп. колёс и голосований."""
    item = get_item(6)
    return [item] * 12


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
        assert u.pending_reward_spins >= 1


def test_reward_wheel_chain(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        with patch(
            "backend.reward_wheels.pick_wheel_items", _stable_reward_wheel
        ):
            start_reward_item_wheels(u, emit=_noop_emit)
            n = u.pending_reward_spins
            assert 1 <= n <= 3

            roll_reward_dice_for_user(u)
            assert u.reward_dice_ready

            for _ in range(n):
                roll_reward_dice_for_user(u)
                open_result = open_reward_wheel_for_user(u, emit=_noop_emit)
                assert not isinstance(open_result, tuple), open_result
                items = __import__(
                    "backend.reward_wheels", fromlist=["_pending_item_wheel_reward"]
                )._pending_item_wheel_reward.get(u.id, [])
                assert items
                confirm_reward_wheel_for_user(
                    u,
                    {"selectedItemId": items[0]["id"]},
                    emit=_noop_emit,
                )

            assert reward_spins_left(u.id) == 0
            u = player("andryuha")
            assert u.turn_phase == "idle"


def test_reward_persists_after_hydrate(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.turn_phase = "reward_items"
        u.pending_reward_spins = 2
        u.reward_dice_ready = True
        db.session.commit()

        hydrate_reward_state()
        u = player("andryuha")
        assert u.turn_phase == "reward_items"
        assert u.pending_reward_spins == 2
        assert u.reward_dice_ready

        result = roll_reward_dice_for_user(u)
        assert "error" not in result
        assert reward_spins_left(u.id) == 2
