"""Проверка истории игр игрока."""

from __future__ import annotations

from backend.models import PlayerGame, User, db

TERMINAL_GAME_STATUSES = frozenset({"completed", "dropped"})


def normalize_game_title(title: str) -> str:
    return " ".join(str(title or "").strip().lower().split())


def player_has_game_title(user_id: int, title: str) -> bool:
    norm = normalize_game_title(title)
    if not norm:
        return False
    rows = (
        PlayerGame.query.filter_by(user_id=user_id)
        .with_entities(PlayerGame.title)
        .all()
    )
    return any(normalize_game_title(r.title) == norm for r in rows)


def get_ongoing_game(user_id: int) -> PlayerGame | None:
    """Игра в процессе: любой статус, кроме completed и dropped."""
    return (
        PlayerGame.query.filter_by(user_id=user_id)
        .filter(PlayerGame.status.notin_(TERMINAL_GAME_STATUSES))
        .order_by(PlayerGame.id.desc())
        .first()
    )


def public_ongoing_game(user_id: int) -> dict | None:
    game = get_ongoing_game(user_id)
    if not game:
        return None
    return {
        "id": game.id,
        "title": game.title,
        "status": game.status,
        "cellName": game.cell_name,
        "genreLabel": game.genre_label,
    }


def ensure_turn_phase_matches_ongoing_game(user: User) -> PlayerGame | None:
    """Если есть незавершённая игра, игрок не может быть в idle."""
    ongoing = get_ongoing_game(user.id)
    if ongoing and user.turn_phase == "idle":
        user.turn_phase = "playing"
        db.session.commit()
    return ongoing


def block_new_turn_if_in_progress(user: User) -> str | None:
    ongoing = ensure_turn_phase_matches_ongoing_game(user)
    if not ongoing:
        return None
    if ongoing.status == "pending_admin":
        return "Ожидайте назначения игры админом"
    return "Сначала завершите или дропните текущую игру"
