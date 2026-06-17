"""Дурка: ролл при фазе wheel_ready (админский сброс / реролл)."""

from backend.board import DURKA_CELL_ID
from backend.turn_actions import open_wheel_for_user


def test_open_wheel_in_durka_with_wheel_ready_phase(app, actor):
    with app.app_context():
        actor.position = DURKA_CELL_ID
        actor.in_durka = True
        actor.turn_phase = "wheel_ready"
        from backend.models import db

        db.session.commit()

        result = open_wheel_for_user(actor)
        assert not isinstance(result, tuple), result
        assert result.get("wheel"), result
        assert len(result["wheel"]) >= 1
        assert result["source"]["durka"] is True
        assert actor.turn_phase == "wheel"
