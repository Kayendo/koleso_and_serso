"""Колёса предметов после прохождения игры (кубик 1–3)."""

from __future__ import annotations

from backend.items.inventory import log_turn
from backend.items.wheel import pick_wheel_items, wheel_labels
from backend.models import User, db
from backend.random_utils import randint
from backend.turn_logic import require_phase

_pending_item_wheel_reward: dict[int, list[dict]] = {}
_reward_wheel_active: dict[int, bool] = {}


def _sync_user_reward(user: User, *, spins: int | None = None, dice_ready: bool | None = None) -> None:
    if spins is not None:
        user.pending_reward_spins = max(0, int(spins))
    if dice_ready is not None:
        user.reward_dice_ready = bool(dice_ready)
    db.session.commit()


def _spins_left(user: User) -> int:
    return max(0, int(user.pending_reward_spins or 0))


def reward_spins_left(user_id: int) -> int:
    user = db.session.get(User, user_id)
    return _spins_left(user) if user else 0


def is_reward_wheel(user_id: int) -> bool:
    return _reward_wheel_active.get(user_id, False)


def hydrate_reward_state() -> None:
    """После перезапуска: восстановить фазу награды из БД."""
    for user in User.query.all():
        spins = _spins_left(user)
        if user.turn_phase == "reward_items" and spins <= 0:
            user.pending_reward_spins = max(1, spins)
            user.reward_dice_ready = False
            db.session.commit()
            continue
        if spins <= 0:
            continue
        if user.turn_phase == "wheel" and user.id not in _reward_wheel_active:
            user.turn_phase = "reward_items"
            if not user.reward_dice_ready and spins > 0:
                user.reward_dice_ready = False
            db.session.commit()


def recovery_payload_for_user(user: User) -> dict | None:
    """Данные для клиента после перезагрузки в фазе награды."""
    if user.turn_phase != "reward_items":
        return None
    spins = _spins_left(user)
    if spins <= 0:
        return None
    return {
        "username": user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "rewardItemSpins": spins,
        "rewardDiceReady": bool(user.reward_dice_ready),
        "user": user.to_public_dict(),
    }


def start_reward_item_wheels(user: User, *, emit) -> dict:
    """После завершения игры: 1d3 колёс предметов подряд."""
    n = randint(1, 3)
    user.turn_phase = "reward_items"
    _sync_user_reward(user, spins=n, dice_ready=False)
    payload = {
        "username": user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "rewardItemSpins": n,
        "rewardDiceReady": False,
        "user": user.to_public_dict(),
    }
    emit("reward_wheels_started", payload)
    return payload


def roll_reward_dice_for_user(user: User) -> dict | tuple[dict, int]:
    err = require_phase(user, "reward_items")
    if err:
        return {"error": err}, 400
    n = _spins_left(user)
    if n <= 0:
        return {"error": "Нет призовых колёс"}, 400
    _sync_user_reward(user, dice_ready=True)
    return {
        "username": user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "rewardDice": [n],
        "rewardItemSpins": n,
        "rewardDiceReady": True,
        "user": user.to_public_dict(),
    }


def recovery_reward_wheel_payload(user: User) -> dict | None:
    """Восстановление призового колеса после F5."""
    if not _reward_wheel_active.get(user.id):
        return None
    items = _pending_item_wheel_reward.get(user.id, [])
    if not items:
        return None
    from backend.pending_wheels import pending_spin

    payload = {
        "username": user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "wheel": [i.get("wheelLabel") or i.get("name") for i in items],
        "wheelType": "reward_item",
        "wheelItems": items,
        "rewardSpinsRemaining": _spins_left(user),
        "rewardSpinIndex": _spins_left(user),
        "source": {"itemWheel": True, "rewardWheel": True},
        "cellName": "Награда за игру",
        "recovered": True,
        "user": user.to_public_dict(),
    }
    spin = pending_spin.get(user.id)
    if spin:
        payload["targetIndex"] = spin.get("targetIndex")
        if spin.get("selectedItemId") is not None:
            payload["selectedItemId"] = spin["selectedItemId"]
        if spin.get("selectedItemName"):
            payload["selectedItemName"] = spin["selectedItemName"]
    return payload


def open_reward_wheel_for_user(user: User, *, emit) -> dict | tuple[dict, int]:
    err = require_phase(user, "reward_items")
    if err:
        return {"error": err}, 400
    left = _spins_left(user)
    if left <= 0:
        return {"error": "Нет оставшихся колёс награды"}, 400
    if not user.reward_dice_ready:
        return {"error": "Сначала бросьте призовой кубик"}, 400

    picked = pick_wheel_items(12, user_id=user.id)
    _pending_item_wheel_reward[user.id] = [i.to_dict() for i in picked]
    _reward_wheel_active[user.id] = True
    user.turn_phase = "wheel"
    db.session.commit()

    payload = {
        "username": user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "wheel": wheel_labels(picked),
        "wheelType": "reward_item",
        "wheelItems": _pending_item_wheel_reward[user.id],
        "rewardSpinsRemaining": left,
        "rewardSpinIndex": left,
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
        "displayName": user.public_name(),
        "userId": user.id,
        "targetIndex": target_index,
        "wheelType": "reward_item",
        "wheel": [i.get("wheelLabel") or i.get("name") for i in items],
        "wheelItems": items,
        "selectedItemId": chosen.get("id"),
        "selectedItemName": chosen.get("name"),
        "rewardSpinsRemaining": _spins_left(user),
        "user": user.to_public_dict(),
    }
    from backend.pending_wheels import pending_spin

    pending_spin[user.id] = {
        "targetIndex": target_index,
        "selectedItemId": chosen.get("id"),
        "selectedItemName": chosen.get("name"),
        "wheelType": "reward_item",
    }
    emit("wheel_spin", payload)
    return payload


def confirm_reward_wheel_for_user(
    user: User, data: dict | None, *, emit
) -> dict | tuple[dict, int]:
    from backend.pending_wheels import pending_spin

    data = data or {}
    items_pending = _pending_item_wheel_reward.get(user.id, [])
    spin_pending = pending_spin.get(user.id)
    allowed = user.turn_phase == "wheel" or (
        user.turn_phase == "reward_items"
        and spin_pending
        and spin_pending.get("wheelType") == "reward_item"
        and items_pending
    )
    if not allowed:
        err = require_phase(user, "wheel")
        return {"error": err}, 400

    if user.turn_phase == "reward_items":
        user.turn_phase = "wheel"
        if not _reward_wheel_active.get(user.id) and items_pending:
            _reward_wheel_active[user.id] = True
        db.session.commit()

    if not _reward_wheel_active.get(user.id):
        if items_pending:
            _reward_wheel_active[user.id] = True
        else:
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

    left = max(0, _spins_left(user) - 1)
    _sync_user_reward(user, spins=left, dice_ready=left > 0)
    _pending_item_wheel_reward.pop(user.id, None)
    _reward_wheel_active.pop(user.id, None)
    from backend.pending_wheels import pending_spin

    pending_spin.pop(user.id, None)

    from backend.items.wheel_extras import chain_extra_item_wheel

    extra = chain_extra_item_wheel(
        user,
        cell_name="Награда за игру",
        dice_label=str(data.get("diceLabel") or "награда"),
        emit=emit,
    )
    if extra:
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
            "displayName": user.public_name(),
            "userId": user.id,
            "item": item.to_dict(),
            "factors": ctx.factors,
            "wheelType": "reward_item",
            "rewardSpinsRemaining": left,
            "rewardDiceReady": False,
            "openExtraWheel": True,
            "user": user.to_public_dict(),
            **{
                k: extra[k]
                for k in (
                    "wheel",
                    "wheelItems",
                    "wheelType",
                    "source",
                    "cellName",
                    "extraWheelSpinsRemaining",
                )
                if k in extra
            },
        }
        emit("reward_wheel_resolved", payload)
        return payload

    if left > 0:
        user.turn_phase = "reward_items"
    else:
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
        "displayName": user.public_name(),
        "userId": user.id,
        "item": item.to_dict(),
        "factors": ctx.factors,
        "wheelType": "reward_item",
        "rewardSpinsRemaining": left,
        "rewardDiceReady": left > 0,
        "user": user.to_public_dict(),
    }
    emit("reward_wheel_resolved", payload)
    return payload
