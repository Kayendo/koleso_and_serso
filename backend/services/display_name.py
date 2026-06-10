"""Смена отображаемого имени (логин не меняется)."""

from __future__ import annotations

import re

from sqlalchemy import func, or_

from backend.models import User, db

_DISPLAY_NAME_RE = re.compile(r"^[\w\u0400-\u04FF][\w\u0400-\u04FF \-']*$", re.UNICODE)


def validate_display_name(raw: str | None) -> tuple[str | None, str | None]:
    name = (raw or "").strip()
    if len(name) < 2:
        return None, "Имя короче 2 символов"
    if len(name) > 24:
        return None, "Имя длиннее 24 символов"
    if not _DISPLAY_NAME_RE.match(name):
        return None, "Допустимы буквы, цифры, пробел, дефис, апостроф и _"
    return name, None


def rename_display_name(user: User, raw: str) -> tuple[User | None, str | None]:
    new_name, err = validate_display_name(raw)
    if err:
        return None, err
    current = user.public_name()
    if new_name.lower() == current.lower():
        return user, None
    taken = (
        User.query.filter(User.id != user.id)
        .filter(
            or_(
                func.lower(User.username) == new_name.lower(),
                func.lower(User.display_name) == new_name.lower(),
            )
        )
        .first()
    )
    if taken:
        return None, "Это имя уже занято"
    user.display_name = new_name
    db.session.commit()
    return user, None
