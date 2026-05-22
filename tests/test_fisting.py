"""Рука для fisting: 1 ловушка, дебафф 5 срабатываний по 5-му очку."""

from backend.items.modifiers import apply_completion_points
from backend.items.use import use_inventory_item
from backend.models import PlayerGame, PlayerModifier, User, db
from backend.services.turn_service import create_player_game

from tests.conftest import grant_item, mod_keys, player, reset_player


def test_fisting_transfers_on_every_fifth_point(app, actor, second_player):
    with app.app_context():
        reset_player(actor)
        reset_player(second_player)
        actor.points = 0
        second_player.points = 0
        grant_item(actor.id, 19, 1)
        use_inventory_item(actor, 19, target_user_id=second_player.id)

        slave = PlayerModifier.query.filter_by(
            user_id=second_player.id, effect_key="slave"
        ).first()
        assert slave
        assert slave.turns_remaining == 5

        game = create_player_game(second_player, "G", second_player.position, "?")
        earn = apply_completion_points(second_player, game, 7, [])
        assert earn == 6
        actor = player(actor.username)
        assert actor.points == 1
        slave = PlayerModifier.query.filter_by(
            user_id=second_player.id, effect_key="slave"
        ).first()
        assert slave
        assert slave.turns_remaining == 4
        assert slave.description == "2"
