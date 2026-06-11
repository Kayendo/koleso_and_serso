"""Колесо предметов (Подлянка / Кайфарик)."""

from __future__ import annotations

from backend.items.catalog import ItemDef, wheel_pool
from backend.items.effects import EffectContext, apply_on_wheel_land
from backend.items.inventory import log_turn
from backend.random_utils import sample
from backend.models import User, db


_recent_wheel_ids: dict[int, list[int]] = {}


def pick_wheel_items(
    count: int = 12,
    *,
    polarity: str | None = None,
    user_id: int | None = None,
) -> list[ItemDef]:
    pool = wheel_pool(polarity=polarity)
    if not pool:
        return []
    avoid: set[int] = set()
    if user_id is not None:
        avoid = set(_recent_wheel_ids.get(user_id, []))
    preferred = [i for i in pool if i.id not in avoid] if avoid else pool
    if len(preferred) < count:
        preferred = pool
    n = min(count, len(preferred))
    picked = sample(preferred, n)
    if user_id is not None:
        prev = _recent_wheel_ids.get(user_id, [])
        merged = (prev + [i.id for i in picked])[-36:]
        _recent_wheel_ids[user_id] = merged
    return picked


def wheel_labels(items: list[ItemDef]) -> list[str]:
    return [i.wheel_label for i in items]


def _finalize_wheel_phase(user: User) -> None:
    from backend.items.wheel_extras import extra_wheel_spins_left, prepare_extra_wheel_turn

    prepare_extra_wheel_turn(user)
    if extra_wheel_spins_left(user.id) <= 0 and user.turn_phase not in (
        "wheel_ready",
        "wheel",
        "playing",
        "reward_items",
    ):
        user.turn_phase = "idle"


def apply_wheel_result(
    user: User,
    item_id: int,
    *,
    dice_label: str,
    cell_name: str,
) -> dict:
    from backend.items.catalog import get_item

    item = get_item(item_id)
    if not item:
        return {"error": "Неизвестный предмет"}

    ctx = EffectContext(
        user_id=user.id,
        item=item,
        actor_username=user.username,
        dice_label=dice_label,
        cell_name=cell_name,
    )
    ctx.note(f"Клетка: {cell_name}")
    ctx.note(f"Кубик: {dice_label}")
    ctx.note(f"Выпало: #{item.id} {item.name}")

    apply_on_wheel_land(ctx, user, db)
    _finalize_wheel_phase(user)
    db.session.commit()

    summary = f"Подлянка: {item.name}"
    log_turn(
        user.id,
        summary=summary,
        factors=ctx.factors,
        dice_label=dice_label,
        cell_name=cell_name,
        extra={"itemId": item.id, "wheelType": "item"},
    )

    return {
        "item": item.to_dict(),
        "factors": ctx.factors,
        "user": user.to_public_dict(),
    }


def apply_wheel_items_bundle(
    user: User,
    item_ids: list[int],
    *,
    dice_label: str,
    cell_name: str,
    summary: str,
    header: str,
    extra: dict | None = None,
) -> dict:
    from backend.items.catalog import get_item

    if not item_ids:
        return {"error": "Не выбраны предметы"}

    all_factors: list[str] = [f"Клетка: {cell_name}", f"Кубик: {dice_label}", header]
    items_out: list[dict] = []

    for item_id in item_ids:
        item = get_item(item_id)
        if not item:
            continue
        ctx = EffectContext(
            user_id=user.id,
            item=item,
            actor_username=user.username,
            dice_label=dice_label,
            cell_name=cell_name,
        )
        ctx.note(f"Засчитано: #{item.id} {item.name}")
        apply_on_wheel_land(ctx, user, db)
        all_factors.extend(ctx.factors)
        items_out.append(item.to_dict())

    _finalize_wheel_phase(user)
    db.session.commit()

    log_extra = {"itemIds": item_ids, "wheelType": "item", **(extra or {})}
    log_turn(
        user.id,
        summary=summary,
        factors=all_factors,
        dice_label=dice_label,
        cell_name=cell_name,
        extra=log_extra,
    )

    return {
        "items": items_out,
        "item": items_out[0] if items_out else None,
        "factors": all_factors,
        "user": user.to_public_dict(),
    }
