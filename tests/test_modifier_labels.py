"""Подписи баффов и дебаффов в инвентаре."""

from backend.items.gameplay import enrich_modifier_entry
from backend.items.modifiers import _add_mod
from backend.models import PlayerModifier

from tests.conftest import player, reset_player


def test_wheel_extra_display_line_no_duplication(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        _add_mod(
            u.id,
            "wheel_extra_spins",
            "2",
            2,
            label="Однорукий бандит",
            polarity="buff",
        )
        mod = PlayerModifier.query.filter_by(
            user_id=u.id, effect_key="wheel_extra_spins"
        ).first()
        entry = enrich_modifier_entry(mod)
        assert entry["name"] == "Однорукий бандит"
        assert entry["durationLabel"] == "2 колёс"
        assert entry["displayLine"] == "Однорукий бандит · 2 колёс"
        assert "не ходы" not in (entry["gameplayHint"] or "")
        assert entry["gameplayHint"] == "Докрутите колесо приколов"
