"""Дроп с парашютом: история, дебафф без очков, клетка «?»."""

from backend.items.drop import handle_drop
from backend.items.inventory import tick_modifiers_after_turn
from backend.items.modifiers import apply_completion_points
from backend.models import TurnLog
from backend.services.scoring import points_for_completion
from backend.services.turn_service import create_player_game

from tests.conftest import grant_item, mod_keys, player, reset_player


def test_parachute_drop_keeps_no_points_debuff(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_item(u.id, 17)
        game = create_player_game(u, "Drop Test", u.position, "2+2", is_question=False)
        u.turn_phase = "playing"
        from backend.models import db

        db.session.commit()

        factors = handle_drop(u, game, on_durka_cell=False, use_toilet=False)
        assert "no_points_next_game" in mod_keys(u.id)
        assert any("парашют" in f.lower() for f in factors)

        logs = TurnLog.query.filter_by(user_id=u.id).order_by(TurnLog.id.desc()).all()
        assert logs
        assert "Дроп" in logs[0].summary

        tick_modifiers_after_turn(u.id)
        assert "no_points_next_game" in mod_keys(u.id)

        game2 = create_player_game(u, "Next", u.position, "3+3", is_question=False)
        attach_tags = game2._parse_gameplay_tags()
        assert any(t.get("key") == "no_points_next_game" for t in attach_tags)

        base = points_for_completion(10.0, None, is_question=False)
        earn = apply_completion_points(u, game2, base, [])
        assert earn == 0
        assert "no_points_next_game" not in mod_keys(u.id)


def test_parachute_penalty_fixed_on_question_cell(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        u.points = 10
        grant_item(u.id, 17)
        game = create_player_game(
            u, "Q Drop", u.position, "2+2", is_question=True
        )
        u.turn_phase = "playing"
        from backend.models import db

        db.session.commit()

        handle_drop(u, game, on_durka_cell=False, use_toilet=False)
        u = player("andryuha")
        assert u.points == 8
