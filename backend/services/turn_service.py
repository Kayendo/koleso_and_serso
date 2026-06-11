from __future__ import annotations

from typing import Any

from backend.random_utils import randint

from backend.board import BOARD_BY_ID, BOARD_SIZE, resolve_genre_for_cell
from backend.config import (
    DURKA_CELL_ID,
    LOTTERY_CELL_ID,
    PASS_START_POINTS,
    START_CELL_ID,
    TRALLALERO_CELL_ID,
)
from backend.models import PlayerGame, User, db
from backend.services import game_lists
from backend.services.hltb_service import fetch_hltb_hours


def _schedule_hltb_lookup(game_id: int, title: str) -> None:
    try:
        from flask import current_app

        app = current_app._get_current_object()
        socketio = app.extensions["socketio"]
        socketio.start_background_task(_hltb_background, game_id, title, app)
    except RuntimeError:
        pass


def _hltb_background(game_id: int, title: str, app) -> None:
    hours = fetch_hltb_hours(title)
    if hours is None:
        return
    with app.app_context():
        game = db.session.get(PlayerGame, game_id)
        if game and game.hltb_hours is None:
            game.hltb_hours = hours
            db.session.commit()


def roll_dice() -> tuple[int, int, str]:
    from backend.services.true_random import fetch_integers

    vals = fetch_integers(2, 1, 6)
    if vals and len(vals) >= 2:
        a, b = vals[0], vals[1]
    else:
        a, b = randint(1, 6), randint(1, 6)
    return a, b, f"{a}+{b}"


def move_position(current: int, steps: int) -> tuple[int, bool]:
    """Возвращает (новая позиция, прошёл ли через старт)."""
    passed_start = False
    pos = current
    for _ in range(steps):
        next_pos = (pos + 1) % BOARD_SIZE
        if next_pos == START_CELL_ID and pos != START_CELL_ID:
            passed_start = True
        pos = next_pos
    return pos, passed_start


def cell_game_source(cell_id: int) -> dict[str, Any]:
    cell = BOARD_BY_ID[cell_id]
    result: dict[str, Any] = {
        "cellId": cell_id,
        "cellName": cell.name,
        "cellType": cell.cell_type,
        "genreLabel": cell.genre_label,
        "genreId": None,
        "blazerdGenre": None,
        "wheelGenres": None,
        "lottery": False,
        "trallalero": False,
        "question": False,
    }
    if cell.cell_type == "lottery":
        result["lottery"] = True
        return result
    if cell.cell_type == "trallalero":
        result["trallalero"] = True
        return result
    if cell.cell_type == "question":
        result["question"] = True
        return result
    if cell.cell_type == "trap_joy":
        result["itemWheel"] = True
        return result
    if cell.cell_type == "start":
        result["startReroll"] = True
        return result
    if cell.cell_type == "durka":
        result["durkaCell"] = True
        return result
    if cell.company_key == "blazerd":
        result["needsGenrePick"] = True
        return result
    gid = resolve_genre_for_cell(cell_id)
    result["genreId"] = gid
    return result


def create_player_game(
    user: User,
    title: str,
    cell_id: int,
    dice_label: str,
    *,
    is_durka: bool = False,
    is_question: bool = False,
    lottery_url: str = "",
) -> PlayerGame:
    cell = BOARD_BY_ID[cell_id]
    game = PlayerGame(
        user_id=user.id,
        title=title,
        cell_id=cell_id,
        cell_name=cell.name,
        genre_label=cell.genre_label or "",
        dice_roll=dice_label,
        is_durka=is_durka,
        is_question=is_question,
        hltb_hours=None,
        lottery_url=lottery_url,
        status="active",
    )
    db.session.add(game)
    user.turn_phase = "playing"
    db.session.flush()
    from backend.items.gameplay import attach_gameplay_to_game

    attach_gameplay_to_game(game, user)
    _schedule_hltb_lookup(game.id, title)
    return game


def apply_start_bonus(user: User, passed: bool) -> int:
    if not passed:
        return 0
    user.points += PASS_START_POINTS
    if user.position == START_CELL_ID:
        user.laps += 1
    db.session.commit()
    return PASS_START_POINTS


def send_to_durka(user: User) -> None:
    user.position = DURKA_CELL_ID
    user.in_durka = True
    user.turn_phase = "durka"
    db.session.commit()


def after_drop(user: User, on_durka_cell: bool) -> None:
    from backend.config import DROP_PENALTY

    active = (
        PlayerGame.query.filter_by(user_id=user.id, status="active")
        .order_by(PlayerGame.id.desc())
        .first()
    )
    if active:
        active.status = "dropped"
        from backend.models import utcnow

        active.finished_at = utcnow()
        user.dropped_count += 1

    if on_durka_cell or user.in_durka:
        user.points = max(0, user.points - DROP_PENALTY)
        user.turn_phase = "durka"
    else:
        send_to_durka(user)
    db.session.commit()
