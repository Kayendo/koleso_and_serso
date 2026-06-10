"""Часовой рост: 2 базовых + 2 за каждые полные 10 ч HLTB (округление часов вверх)."""

from backend.items.gameplay import activate_buff_for_next_game
from backend.items.modifiers import apply_completion_points
from backend.models import PlayerGame, User, db
from backend.services.scoring import points_for_completion

from tests.conftest import player, reset_player


def test_hour_growth_39h_gives_10_points(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        activate_buff_for_next_game(u.id, "hour_growth", item_id=48, label="Часовой рост")
        game = PlayerGame(
            user_id=u.id,
            title="Long Game",
            cell_id=1,
            status="active",
            hltb_hours=39.0,
            is_question=False,
        )
        db.session.add(game)
        db.session.commit()

        base = points_for_completion(39.0, None, False)
        assert base == 5

        earn = apply_completion_points(u, game, base, [])
        assert earn == 10
