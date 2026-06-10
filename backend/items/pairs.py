"""Взаимоисключающие пары предметов в инвентаре."""

from __future__ import annotations

from backend.items.catalog import get_item
from backend.models import PlayerModifier, PlayerInventoryItem, db

MUTUAL_DESTROY: list[tuple[int, int]] = [
    (1, 2),  # читерский кубик / хуюбик
    (3, 4),  # очки EZ / повязка Рэмбо
]

PAIR_MOD_KEYS: dict[tuple[int, int], tuple[str, str]] = {
    (3, 4): ("ez_glasses", "rambo_band"),
}


def _effect_active(user_id: int, key: str) -> bool:
    return (
        PlayerModifier.query.filter_by(user_id=user_id, effect_key=key)
        .filter(PlayerModifier.turns_remaining != 0)
        .first()
        is not None
    )


def _has_item(user_id: int, item_id: int) -> bool:
    from backend.items.inventory import has_item

    return has_item(user_id, item_id)


def _side_active(user_id: int, item_id: int, mod_key: str) -> bool:
    return _has_item(user_id, item_id) or _effect_active(user_id, mod_key)


def _clear_mods(user_id: int, *keys: str) -> None:
    for key in keys:
        PlayerModifier.query.filter_by(user_id=user_id, effect_key=key).delete()


def _remove_items(user_id: int, *item_ids: int) -> None:
    for iid in item_ids:
        PlayerInventoryItem.query.filter_by(
            user_id=user_id, item_def_id=iid
        ).delete()


def resolve_conflicts(user_id: int) -> list[str]:
    """Снять взаимоисключающие пары (предметы + модификаторы)."""
    notes: list[str] = []
    for a, b in MUTUAL_DESTROY:
        mods = PAIR_MOD_KEYS.get((a, b))
        if mods:
            mod_a, mod_b = mods
            active = _side_active(user_id, a, mod_a) and _side_active(user_id, b, mod_b)
        else:
            active = _has_item(user_id, a) and _has_item(user_id, b)
        if not active:
            continue
        _remove_items(user_id, a, b)
        if mods:
            _clear_mods(user_id, mod_a, mod_b)
        na = get_item(a)
        nb = get_item(b)
        notes.append(
            f"«{na.name if na else a}» и «{nb.name if nb else b}» уничтожили друг друга"
        )
    if notes:
        db.session.commit()
        from backend.items.inventory import log_item_interaction

        log_item_interaction(
            user_id,
            summary="Конфликт предметов",
            factors=notes,
            extra={"mutualDestroy": True},
        )
    return notes


def use_blocked_by_conflict(user_id: int, item_id: int) -> tuple[bool, list[str]]:
    """Перед использованием EZ/Рэмбо: конфликт → уничтожение без эффекта."""
    for a, b in MUTUAL_DESTROY:
        if item_id not in (a, b):
            continue
        other = b if item_id == a else a
        mods = PAIR_MOD_KEYS.get((a, b))
        if not mods:
            if _has_item(user_id, a) and _has_item(user_id, b):
                return True, resolve_conflicts(user_id)
            return False, []
        mod_a, mod_b = mods
        self_mod, other_mod = (mod_a, mod_b) if item_id == a else (mod_b, mod_a)
        other_active = _side_active(user_id, other, other_mod)
        if not other_active:
            return False, []
        _remove_items(user_id, a, b)
        _clear_mods(user_id, mod_a, mod_b)
        db.session.commit()
        na = get_item(a)
        nb = get_item(b)
        return True, [
            f"«{na.name if na else a}» и «{nb.name if nb else b}» уничтожили друг друга"
        ]
    return False, []
