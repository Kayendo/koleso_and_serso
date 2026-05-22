"""УВЫ: только базовые очки, не перебивается часовым ростом."""

from backend.items.gameplay import activate_buff_for_next_game
from backend.items.modifiers import apply_completion_points
from backend.models import PlayerGame, User, db
from backend.services.scoring import points_for_completion

from tests.conftest import player, reset_player


def test_uvy_ignores_hltb_and_hour_growth(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        activate_buff_for_next_game(u.id, "base_only_next", item_id=47, label="УВЫ")
        activate_buff_for_next_game(u.id, "hour_growth", item_id=48, label="Часовой рост")
        game = PlayerGame(
            user_id=u.id,
            title="Test",
            cell_id=1,
            status="active",
            hltb_hours=40.0,
            is_question=False,
        )
        db.session.add(game)
        db.session.commit()

        base = points_for_completion(40.0, None, False)
        assert base > 2

        earn = apply_completion_points(u, game, base, [])
        expected = points_for_completion(None, None, False)
        assert earn == expected
        assert earn < base
