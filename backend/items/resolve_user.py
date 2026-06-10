"""Поиск игрока по id или имени."""

from __future__ import annotations

from sqlalchemy import or_

from backend.models import User


def resolve_user_id(
    *,
    user_id: int | None = None,
    username: str | None = None,
) -> tuple[int | None, str | None]:
    """Вернуть (user_id, error_message)."""
    if user_id is not None:
        u = User.query.get(int(user_id))
        if not u:
            return None, "Игрок не найден"
        return u.id, None

    name = (username or "").strip()
    if not name:
        return None, None

    u = User.query.filter(
        or_(
            User.username.ilike(name),
            User.display_name.ilike(name),
        )
    ).first()
    if not u:
        return None, f"Игрок «{name}» не найден"
    return u.id, None
