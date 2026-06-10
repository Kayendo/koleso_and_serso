"""In-memory состояние открытых колёс (до подтверждения)."""

from __future__ import annotations

pending_item_wheel: dict[int, list[dict]] = {}
pending_wheel: dict[int, list[str]] = {}
pending_dice_choice: dict[int, dict] = {}
pending_crown_pick: dict[int, dict] = {}
# Результат спина до подтверждения (восстановление после F5)
pending_spin: dict[int, dict] = {}
# Шоколад: выбранный жанр для следующего колеса игр
pending_chocolate_genre: dict[int, int] = {}
# Админ-эффект (законы, магазины): без модификатора в UI
pending_admin_wheel: dict[int, dict] = {}
# Плашка на одно следующее колесо (игры)
pending_wheel_banner: dict[int, str] = {}
# Фаза до цепочки доп. колёс (playing и т.д.)
pending_resume_phase: dict[int, str] = {}
# «Два по цене одного»: на след. подтверждении — центр + 2 соседа
pending_two_for_one: dict[int, bool] = {}
# Магазины / «Два по цене одного»: rerolл → админ выдаёт предметы
pending_shop_repick: dict[int, dict] = {}
pending_shop_pick: dict[int, dict] = {}
# Ожидает выдачи предметов админом (магазины, два по одному)
pending_admin_item_grant: dict[int, dict] = {}


def set_two_for_one(user_id: int) -> None:
    pending_two_for_one[user_id] = True


def has_two_for_one(user_id: int) -> bool:
    return pending_two_for_one.get(user_id, False)


def pop_two_for_one(user_id: int) -> bool:
    return pending_two_for_one.pop(user_id, False)


def set_shop_repick(user_id: int, mode: str, *, effect_item_id: int) -> None:
    pending_shop_repick[user_id] = {
        "mode": mode,
        "effectItemId": int(effect_item_id),
    }


def get_shop_repick(user_id: int) -> dict | None:
    raw = pending_shop_repick.get(user_id)
    if raw is None:
        return None
    if isinstance(raw, str):
        return {"mode": raw, "effectItemId": 24 if raw == "chat" else 25}
    return raw


def pop_shop_repick(user_id: int) -> dict | None:
    raw = pending_shop_repick.pop(user_id, None)
    if raw is None:
        return None
    if isinstance(raw, str):
        return {"mode": raw, "effectItemId": 24 if raw == "chat" else 25}
    return raw


def set_shop_pick(user_id: int, data: dict) -> None:
    pending_shop_pick[user_id] = dict(data)


def pop_shop_pick(user_id: int) -> dict | None:
    return pending_shop_pick.pop(user_id, None)


def set_admin_item_grant(user_id: int, data: dict) -> None:
    pending_admin_item_grant[user_id] = dict(data)


def get_admin_item_grant(user_id: int) -> dict | None:
    return pending_admin_item_grant.get(user_id)


def pop_admin_item_grant(user_id: int) -> dict | None:
    return pending_admin_item_grant.pop(user_id, None)


def set_chocolate_genre(user_id: int, genre_id: int) -> None:
    pending_chocolate_genre[user_id] = int(genre_id)


def consume_chocolate_genre(user_id: int) -> int | None:
    return pending_chocolate_genre.pop(user_id, None)


def set_admin_wheel(user_id: int, data: dict) -> None:
    pending_admin_wheel[user_id] = dict(data)


def get_admin_wheel(user_id: int) -> dict | None:
    return pending_admin_wheel.get(user_id)


def pop_admin_wheel(user_id: int) -> dict | None:
    return pending_admin_wheel.pop(user_id, None)


def set_wheel_banner(user_id: int, label: str) -> None:
    pending_wheel_banner[user_id] = label


def pop_wheel_banner(user_id: int) -> str | None:
    return pending_wheel_banner.pop(user_id, None)


def get_wheel_banner(user_id: int) -> str | None:
    return pending_wheel_banner.get(user_id)


def save_resume_phase(user_id: int, phase: str) -> None:
    if user_id not in pending_resume_phase:
        pending_resume_phase[user_id] = phase


def pop_resume_phase(user_id: int) -> str | None:
    return pending_resume_phase.pop(user_id, None)
