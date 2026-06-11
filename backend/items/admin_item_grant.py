"""Ролл колеса приколов → предметы выдаёт админ (магазины)."""

from __future__ import annotations

from backend.items.catalog import get_item
from backend.items.effects import EffectContext
from backend.models import User, db

ADMIN_ITEM_EFFECT_IDS = frozenset({24, 25})

ADMIN_ITEM_BANNERS: dict[int, str] = {
    24: "Админ выдаст предмет по выбору чата",
    25: "Админ выдаст 2 предмета по вашему выбору",
}


def is_admin_item_effect(item_id: int) -> bool:
    return int(item_id) in ADMIN_ITEM_EFFECT_IDS


def set_admin_item_grant(user_id: int, data: dict) -> None:
    from backend.pending_wheels import set_admin_item_grant as _set

    _set(user_id, data)


def get_admin_item_grant(user_id: int) -> dict | None:
    from backend.pending_wheels import get_admin_item_grant as _get

    return _get(user_id)


def pop_admin_item_grant(user_id: int) -> dict | None:
    from backend.pending_wheels import pop_admin_item_grant as _pop

    return _pop(user_id)


def public_admin_item_grant(user_id: int) -> dict | None:
    return get_admin_item_grant(user_id)


def _clear_shop_buff_mod(user_id: int) -> None:
    from backend.items.modifiers import _consume_mod, _has_mod

    for key in ("shop_chat_buff", "shop_leprechaun_buff"):
        mod = _has_mod(user_id, key)
        if mod:
            _consume_mod(mod)


def resolve_admin_item_wheel(
    user: User,
    effect_item_id: int,
    sectors: list[dict],
    *,
    dice_label: str,
    cell_name: str,
    note: str = "",
) -> dict:
    """Зафиксировать секторы для админа, предметы не применяются."""
    from backend.items.inventory import log_turn

    item = get_item(effect_item_id)
    name = item.name if item else f"#{effect_item_id}"
    banner = ADMIN_ITEM_BANNERS.get(int(effect_item_id), name)

    sector_lines = [
        f"  • {s.get('wheelLabel') or s.get('name') or '?'}"
        + (f" (#{s.get('itemId')})" if s.get("itemId") else "")
        for s in sectors
    ]
    factors = [
        f"Клетка: {cell_name}",
        f"Кубик: {dice_label}",
        f"«{name}»: {banner}",
        note,
        "Секторы для выдачи админом:",
        *sector_lines,
        "Предметы выдаёт админ",
    ]
    factors = [f for f in factors if f]

    set_admin_item_grant(
        user.id,
        {
            "effectItemId": int(effect_item_id),
            "effectName": name,
            "banner": banner,
            "sectors": sectors,
            "cellName": cell_name,
            "diceLabel": dice_label,
        },
    )

    _clear_shop_buff_mod(user.id)
    from backend.pending_wheels import pop_shop_repick

    pop_shop_repick(user.id)

    from backend.items.wheel_extras import (
        consume_one_extra_wheel_spin,
        extra_wheel_spins_left,
        finish_extra_wheel_chain,
    )

    # Reroll магазина расходует выделенный доп. прокрут.
    if extra_wheel_spins_left(user.id) > 0:
        consume_one_extra_wheel_spin(user.id)

    if extra_wheel_spins_left(user.id) <= 0:
        finish_extra_wheel_chain(user)
        if user.turn_phase not in ("playing", "reward_items"):
            user.turn_phase = "idle"
    db.session.commit()

    log_turn(
        user.id,
        summary=f"Ролл: {name} → ждёт админа",
        factors=factors,
        dice_label=dice_label,
        cell_name=cell_name,
        extra={
            "adminItemGrant": True,
            "effectItemId": effect_item_id,
            "sectors": sectors,
        },
    )

    return {
        "adminItemGrantPending": True,
        "effectName": name,
        "sectors": sectors,
        "factors": factors,
        "user": user.to_public_dict(),
    }
