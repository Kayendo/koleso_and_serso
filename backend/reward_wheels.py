"""Колёса предметов после прохождения игры (кубик 1–3)."""

from __future__ import annotations

from backend.items.inventory import log_turn
from backend.items.wheel import pick_wheel_items, wheel_labels
from backend.models import User, db
from backend.random_utils import randint
from backend.turn_logic import require_phase

_pending_reward_spins: dict[int, int] = {}
_reward_wheel_active: dict[int, bool] = {}
_pending_item_wheel_reward: dict[int, list[dict]] = {}
_reward_dice_ready: dict[int, bool] = {}


def reward_spins_left(user_id: int) -> int:
    return _pending_reward_spins.get(user_id, 0)


def is_reward_wheel(user_id: int) -> bool:
    return _reward_wheel_active.get(user_id, False)


def start_reward_item_wheels(user: User, *, emit) -> dict:
    """После завершения игры: 1d3 колёс предметов подряд."""
    n = randint(1, 3)
    _pending_reward_spins[user.id] = n
    user.turn_phase = "reward_items"
    db.session.commit()
    _reward_dice_ready[user.id] = False
    payload = {
        "username": user.username,
        "userId": user.id,
        "rewardItemSpins": n,
        "user": user.to_public_dict(),
    }
    emit("reward_wheels_started", payload)
    return payload


def roll_reward_dice_for_user(user: User) -> dict | tuple[dict, int]:
    err = require_phase(user, "reward_items")
    if err:
        return {"error": err}, 400
    n = _pending_reward_spins.get(user.id, 0)
    if n <= 0:
        return {"error": "Нет призовых колёс"}, 400
    _reward_dice_ready[user.id] = True
    return {
        "username": user.username,
        "userId": user.id,
        "rewardDice": [n],
        "rewardItemSpins": n,
        "user": user.to_public_dict(),
    }


def open_reward_wheel_for_user(user: User, *, emit) -> dict | tuple[dict, int]:
    err = require_phase(user, "reward_items")
    if err:
        return {"error": err}, 400
    left = _pending_reward_spins.get(user.id, 0)
    if left <= 0:
        return {"error": "Нет оставшихся колёс награды"}, 400
    if not _reward_dice_ready.get(user.id):
        return {"error": "Сначала бросьте призовой кубик"}, 400

    picked = pick_wheel_items(12, user_id=user.id)
    _pending_item_wheel_reward[user.id] = [i.to_dict() for i in picked]
    _reward_wheel_active[user.id] = True
    user.turn_phase = "wheel"
    db.session.commit()

    payload = {
        "username": user.username,
        "userId": user.id,
        "wheel": wheel_labels(picked),
        "wheelType": "reward_item",
        "wheelItems": _pending_item_wheel_reward[user.id],
        "rewardSpinsRemaining": left,
        "rewardSpinIndex": _pending_reward_spins[user.id] - left + 1,
        "source": {"itemWheel": True, "rewardWheel": True},
        "cellName": "Награда за игру",
        "user": user.to_public_dict(),
    }
    emit("wheel_opened", payload)
    return payload


def spin_reward_wheel_for_user(user: User, *, emit) -> dict | tuple[dict, int]:
    err = require_phase(user, "wheel")
    if err:
        return {"error": err}, 400
    if not _reward_wheel_active.get(user.id):
        return {"error": "Это не колесо награды"}, 400

    items = _pending_item_wheel_reward.get(user.id, [])
    if not items:
        return {"error": "Нет предметов для колеса"}, 400

    from backend.random_utils import randbelow

    target_index = randbelow(len(items))
    chosen = items[target_index]
    payload = {
        "username": user.username,
        "userId": user.id,
        "targetIndex": target_index,
        "wheelType": "reward_item",
        "wheel": [i.get("wheelLabel") or i.get("name") for i in items],
        "wheelItems": items,
        "selectedItemId": chosen.get("id"),
        "selectedItemName": chosen.get("name"),
        "rewardSpinsRemaining": _pending_reward_spins.get(user.id, 0),
        "user": user.to_public_dict(),
    }
    emit("wheel_spin", payload)
    return payload


def confirm_reward_wheel_for_user(
    user: User, data: dict | None, *, emit
) -> dict | tuple[dict, int]:
    err = require_phase(user, "wheel")
    if err:
        return {"error": err}, 400
    if not _reward_wheel_active.get(user.id):
        return {"error": "Это не колесо награды"}, 400

    data = data or {}
    items = _pending_item_wheel_reward.get(user.id, [])
    item_id = data.get("selectedItemId")
    if item_id is None:
        idx = data.get("targetIndex")
        if idx is not None and 0 <= int(idx) < len(items):
            item_id = items[int(idx)].get("id")
    if not item_id:
        return {"error": "Не выбран предмет"}, 400

    from backend.items.catalog import get_item
    from backend.items.effects import EffectContext, apply_on_wheel_land

    item = get_item(int(item_id))
    if not item:
        return {"error": "Неизвестный предмет"}, 400

    ctx = EffectContext(
        user_id=user.id,
        item=item,
        actor_username=user.username,
        dice_label=str(data.get("diceLabel") or "награда"),
        cell_name="Награда за игру",
    )
    ctx.note("Награда за прохождение игры")
    ctx.note(f"Выпало: #{item.id} {item.name}")
    apply_on_wheel_land(ctx, user, db)

    left = max(0, _pending_reward_spins.get(user.id, 1) - 1)
    _pending_reward_spins[user.id] = left
    _pending_item_wheel_reward.pop(user.id, None)
    _reward_wheel_active.pop(user.id, None)

    if left > 0:
        user.turn_phase = "reward_items"
    else:
        _pending_reward_spins.pop(user.id, None)
        _reward_dice_ready.pop(user.id, None)
        user.turn_phase = "idle"
    db.session.commit()

    log_turn(
        user.id,
        summary=f"Награда: {item.name}",
        factors=ctx.factors,
        cell_name="Награда за игру",
        extra={
            "itemId": item.id,
            "wheelType": "reward_item",
            "rewardSpinsRemaining": left,
        },
    )

    payload = {
        "username": user.username,
        "userId": user.id,
        "item": item.to_dict(),
        "factors": ctx.factors,
        "wheelType": "reward_item",
        "rewardSpinsRemaining": left,
        "user": user.to_public_dict(),
    }
    emit("reward_wheel_resolved", payload)
    return payload
