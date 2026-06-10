"""Законы: игрок в прохождении до complete/drop."""

from backend.accounts import ADMIN_ACCOUNT
from backend.models import PlayerGame, db
from backend.turn_actions import confirm_wheel_for_user, open_wheel_for_user, roll_dice_for_user

from tests.conftest import grant_item, reset_player


def _login(client, username, password):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def _law_roll_to_pending(actor):
    grant_item(actor.id, 41)
    from backend.items.use import use_inventory_item

    use_inventory_item(actor, 41)
    open_wheel_for_user(actor, genre_id=2)
    actor.turn_phase = "wheel"
    db.session.commit()
    confirm_wheel_for_user(
        actor,
        {"selectedGame": "Law Game", "genreId": 2, "diceLabel": "3+4"},
    )


def test_law_stub_sets_playing_phase(app, actor):
    with app.app_context():
        reset_player(actor, phase="wheel_ready", position=5)
        _law_roll_to_pending(actor)
        assert actor.turn_phase == "playing"
        game = PlayerGame.query.filter_by(user_id=actor.id).first()
        assert game.status == "pending_admin"


def test_cannot_roll_dice_while_pending_admin(app, actor):
    with app.app_context():
        reset_player(actor, phase="wheel_ready", position=5)
        _law_roll_to_pending(actor)
        actor.turn_phase = "idle"
        db.session.commit()
        result = roll_dice_for_user(actor)
        payload = result[0] if isinstance(result, tuple) else result
        assert payload.get("error")
        assert actor.turn_phase == "playing"


def test_cannot_roll_dice_while_active_game(app, actor):
    with app.app_context():
        reset_player(actor, phase="playing", position=5)
        game = PlayerGame(
            user_id=actor.id,
            title="Active One",
            cell_id=5,
            cell_name="X",
            status="active",
        )
        db.session.add(game)
        actor.turn_phase = "idle"
        db.session.commit()
        result = roll_dice_for_user(actor)
        payload = result[0] if isinstance(result, tuple) else result
        assert payload.get("error")
        assert actor.turn_phase == "playing"


def test_admin_activate_sets_playing(app, actor, client):
    with app.app_context():
        reset_player(actor, phase="wheel_ready", position=5)
        _law_roll_to_pending(actor)
        game = PlayerGame.query.filter_by(user_id=actor.id).first()
        game_id = game.id
        actor.turn_phase = "idle"
        db.session.commit()

    _login(client, ADMIN_ACCOUNT["username"], ADMIN_ACCOUNT["password"])
    resp = client.patch(
        f"/api/admin/games/{game_id}",
        json={"status": "active", "title": "Final Law Game"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "active"
    assert data["user"]["turnPhase"] == "playing"
    assert data["user"]["ongoingGame"]["status"] == "active"
