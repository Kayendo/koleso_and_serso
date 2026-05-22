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

    user.turn_phase = "idle"
    db.session.commit()

    log_turn(
        user.id,
        summary=f"Подлянка: {item.name}",
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
