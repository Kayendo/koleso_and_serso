"""Тотем мошны, EZ/Рэмбо, свиток реролла."""

from backend.items.effects import grant_item_to_player
from backend.items.gameplay import clear_gameplay_modifiers_for_reroll
from backend.items.modifiers import apply_completion_points
from backend.models import PlayerGame, TurnLog, db
from backend.services.scoring import points_for_totem
from backend.services.turn_service import create_player_game

from backend.items.inventory import has_item
from tests.conftest import grant_item, mod_keys, player, reset_player
from tests.test_all_items import _use


def test_totem_points_base_plus_hltb(app):
    with app.app_context():
        assert points_for_totem(14.3, None) == 4  # 3 + 1 за 10 ч (14→10)
        assert points_for_totem(15.0, None) == 5  # 3 + 2 за 10 и 20 ч
        assert points_for_totem(15.9, None) == 5  # 15→20
        assert points_for_totem(None, None) == 3


def test_totem_completion(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 20)
        _use(actor, 20)
        game = create_player_game(actor, "Totem", actor.position, "2+2")
        game.hltb_hours = 20.0
        db.session.commit()
        earn = apply_completion_points(actor, game, 0, [])
        assert earn == 5  # 3 + 2 за 20ч


def test_totem_on_active_game(app, actor):
    with app.app_context():
        reset_player(actor)
        game = create_player_game(actor, "Active Totem", actor.position, "2+2")
        grant_item(actor.id, 20)
        _use(actor, 20)
        tags = game._parse_gameplay_tags()
        assert any(t.get("key") == "totem_moshnya" for t in tags)
        game.hltb_hours = 15.0
        db.session.commit()
        earn = apply_completion_points(actor, game, 0, [])
        assert earn == 5


def test_rambo_grant_with_ez_mod_no_debuff(app, actor):
    with app.app_context():
        reset_player(actor)
        from backend.items.gameplay import activate_buff_for_next_game

        activate_buff_for_next_game(
            actor.id, "ez_glasses", item_id=3, label="Очки EZ", polarity="buff"
        )
        notes = grant_item_to_player(actor, 4)
        assert "rambo_band" not in mod_keys(actor.id)
        assert "ez_glasses" not in mod_keys(actor.id)
        assert any("уничтожили" in n.lower() for n in notes)


def test_rambo_grant_with_ez_logs_on_wheel(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 3)
        notes = grant_item_to_player(actor, 4)
        assert any("уничтожили" in n.lower() for n in notes)
        assert "rambo_band" not in mod_keys(actor.id)


def test_reroll_clears_gameplay_mods(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_item(u.id, 5)
        grant_item(u.id, 20)
        _use(u, 20)
        game = create_player_game(u, "Reroll", u.position, "2+2")
        u.turn_phase = "playing"
        db.session.commit()
        assert "totem_moshnya" in mod_keys(u.id)

        _use(u, 5)
        u = player("andryuha")
        assert u.turn_phase == "wheel_ready"
        assert "totem_moshnya" not in mod_keys(u.id)
        game = db.session.get(PlayerGame, game.id)
        assert game.gameplay_tags == "[]"

        logs = TurnLog.query.filter_by(user_id=u.id).order_by(TurnLog.id.desc()).all()
        assert any("реролл" in (log.summary + log.factors_json).lower() for log in logs[:3])
