"""Дроп игры и предметы Туалетка / Парашют."""

from __future__ import annotations

import math

from backend.board import START_CELL_ID
from backend.items import inventory as inv
from backend.items.modifiers import _add_mod
from backend.models import PlayerGame, User, db
from backend.services.turn_service import after_drop


def handle_drop(
    user: User,
    game: PlayerGame,
    *,
    on_durka_cell: bool,
    use_toilet: bool,
) -> list[str]:
    factors: list[str] = []

    if inv.has_item(user.id, 17) and not use_toilet:
        inv.consume_inventory_item(user.id, 17)
        penalty = 2
        if game.is_question:
            penalty = math.ceil(2 * 1.5)
        user.points = max(0, user.points - penalty)
        user.position = START_CELL_ID
        _add_mod(
            user.id,
            "no_points_next_game",
            "1",
            1,
            item_id=17,
            label="Дырявый парашют",
            polarity="debuff",
        )
        game.status = "dropped"
        from backend.models import utcnow

        game.finished_at = utcnow()
        user.dropped_count += 1
        user.turn_phase = "idle"
        db.session.commit()
        q_note = " (клетка «?» ×1.5)" if game.is_question else ""
        factors.append(
            f"Дроп с «Дырявым парашютом»: Старт, −{penalty} очка{q_note}"
        )
        factors.append("Следующая игра: без очков за прохождение")
        _log_drop(user, game, factors, parachute=True, penalty=penalty)
        return factors

    if use_toilet and inv.has_item(user.id, 16):
        inv.consume_inventory_item(user.id, 16)
        prev = user.last_position
        if prev is not None:
            user.position = prev
        game.status = "dropped"
        from backend.models import utcnow

        game.finished_at = utcnow()
        user.dropped_count += 1
        user.turn_phase = "playing"
        db.session.commit()
        factors.append("«Туалетка»: возврат на клетку прошлого хода")
        _log_drop(user, game, factors, toilet=True)
        return factors

    after_drop(user, on_durka_cell=on_durka_cell)
    factors.append("Дроп: отправка в дурку" if not on_durka_cell else "Дроп в дурке: −2 очка")
    from backend.items.gameplay import tick_buffs_after_game

    factors.extend(tick_buffs_after_game(user.id))
    _log_drop(user, game, factors)
    return factors


def _log_drop(
    user: User,
    game: PlayerGame,
    factors: list[str],
    *,
    parachute: bool = False,
    toilet: bool = False,
    penalty: int = 0,
) -> None:
    from backend.items.inventory import log_turn

    kind = "парашют" if parachute else "туалетка" if toilet else "обычный"
    log_turn(
        user.id,
        summary=f"Дроп: {game.title}",
        factors=factors,
        cell_name=game.cell_name or "",
        extra={
            "gameId": game.id,
            "drop": True,
            "dropKind": kind,
            "parachute": parachute,
            "penalty": penalty,
            "isQuestion": game.is_question,
        },
    )
