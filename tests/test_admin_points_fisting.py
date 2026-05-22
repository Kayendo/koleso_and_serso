"""Админское изменение очков + fisting + история."""

from backend.accounts import ADMIN_ACCOUNT
from backend.items.effects import _trap_fisting, EffectContext
from backend.items.gameplay import attach_gameplay_to_game
from backend.items.catalog import get_item
from backend.items.points import grant_points
from backend.models import TurnLog, User, db
from backend.services.turn_service import create_player_game

from tests.conftest import mod_keys, player, reset_player


def _login(client, username, password):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def test_grant_points_fisting_split(app):
    with app.app_context():
        master = player("andryuha")
        victim = User.query.filter(User.username != master.username).first()
        reset_player(master)
        reset_player(victim)
        master.points = 0
        victim.points = 0
        db.session.commit()

        item = get_item(19)
        ctx = EffectContext(
            user_id=victim.id,
            item=item,
            actor_username=master.username,
            target_user_id=victim.id,
        )
        _trap_fisting(ctx, victim)

        factors: list[str] = []
        gained = grant_points(victim, 5, factors)
        assert gained == 4
        assert victim.points == 4
        assert master.points == 1
        assert any("fisting" in f for f in factors)


def test_admin_points_fisting_split_and_log(app, client):
    with app.app_context():
        master = player("andryuha")
        victim = User.query.filter(User.username != master.username).first()
        assert victim
        reset_player(master)
        reset_player(victim)
        master.points = 0
        victim.points = 0
        db.session.commit()

        item = get_item(19)
        ctx = EffectContext(
            user_id=victim.id,
            item=item,
            actor_username=master.username,
            target_user_id=victim.id,
        )
        _trap_fisting(ctx, victim)

        acc = ADMIN_ACCOUNT
        assert _login(client, acc["username"], acc["password"]).status_code == 200

        r = client.patch(
            f"/api/admin/users/{victim.id}",
            json={"points": victim.points + 5},
        )
        assert r.status_code == 200, r.get_json()

        victim = player(victim.username)
        master = player(master.username)
        assert victim.points == 4
        assert master.points == 1

        log_v = TurnLog.query.filter_by(user_id=victim.id).order_by(TurnLog.id.desc()).first()
        assert log_v
        assert "Админ" in log_v.summary

        log_m = TurnLog.query.filter_by(user_id=master.id).order_by(TurnLog.id.desc()).first()
        assert log_m
        assert "fisting" in log_m.summary.lower()


def test_no_points_survives_game_assign(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        from backend.items.modifiers import _add_mod

        _add_mod(
            u.id,
            "no_points_next_game",
            "1",
            1,
            label="Парашют",
            polarity="debuff",
        )
        game = create_player_game(u, "T", u.position, "?")
        attach_gameplay_to_game(game, u)
        from tests.conftest import mod_keys

        assert "no_points_next_game" in mod_keys(u.id)
