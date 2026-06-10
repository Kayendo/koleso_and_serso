"""Дополнительные прокруты колеса приколов (бандит, лепрекон и т.д.)."""

from __future__ import annotations

from backend.items.modifiers import _add_mod, _consume_mod, _has_mod
from backend.items.wheel import pick_wheel_items, wheel_labels
from backend.models import User, db

EXTRA_WHEEL_KEY = "wheel_extra_spins"


def add_extra_wheel_spins(user_id: int, count: int, *, label: str = "Доп. колёса") -> None:
    if count <= 0:
        return
    existing = _has_mod(user_id, EXTRA_WHEEL_KEY)
    if existing:
        total = max(0, int(existing.turns_remaining or 0)) + count
        existing.turns_remaining = total
        existing.effect_value = str(total)
    else:
        _add_mod(
            user_id,
            EXTRA_WHEEL_KEY,
            str(count),
            count,
            label=label,
            polarity="buff",
        )


def extra_wheel_spins_left(user_id: int) -> int:
    mod = _has_mod(user_id, EXTRA_WHEEL_KEY)
    if not mod:
        return 0
    return max(0, int(mod.turns_remaining or 0))


def consume_one_extra_wheel_spin(user_id: int) -> int:
    """Списать одно доп. колесо. Возвращает оставшееся число."""
    mod = _has_mod(user_id, EXTRA_WHEEL_KEY)
    if not mod or mod.turns_remaining <= 0:
        return 0
    mod.turns_remaining -= 1
    left = max(0, int(mod.turns_remaining))
    if left <= 0:
        _consume_mod(mod)
    db.session.commit()
    return left


def chain_extra_item_wheel(
    user: User,
    *,
    cell_name: str,
    dice_label: str,
    emit=None,
) -> dict | None:
    """Открыть доп. колесо приколов, если остались прокруты."""
    if extra_wheel_spins_left(user.id) <= 0:
        return None
    extra = open_extra_item_wheel(
        user,
        cell_name=cell_name,
        dice_label=dice_label,
    )
    if extra and emit:
        emit("wheel_opened", extra)
    return extra


def resume_reward_phase_if_pending(user: User) -> bool:
    """Вернуть игрока к призовым колёсам после доп. прокрутов."""
    spins = int(getattr(user, "pending_reward_spins", 0) or 0)
    if spins <= 0 or extra_wheel_spins_left(user.id) > 0:
        return False
    user.turn_phase = "reward_items"
    user.reward_dice_ready = False
    db.session.commit()
    return True


def prepare_extra_wheel_turn(user: User) -> None:
    """Если есть доп. прокруты — сохранить фазу и показать кнопку колеса."""
    from backend.pending_wheels import save_resume_phase

    if extra_wheel_spins_left(user.id) <= 0:
        return
    if user.turn_phase in ("playing", "reward_items"):
        save_resume_phase(user.id, user.turn_phase)
    user.turn_phase = "wheel_ready"


def finish_extra_wheel_chain(user: User) -> str | None:
    """После цепочки доп. колёс вернуть сохранённую фазу или завершить ход."""
    from backend.pending_wheels import pop_resume_phase

    if extra_wheel_spins_left(user.id) > 0:
        return None
    phase = pop_resume_phase(user.id)
    if phase:
        user.turn_phase = phase
        db.session.commit()
        return phase

    # Доп. колёса приколов — не дают повторный ролл клетки без нового кубика.
    from backend.items.admin_item_grant import get_admin_item_grant
    from backend.items.admin_wheel import get_active_admin_wheel
    from backend.pending_wheels import get_shop_repick

    if (
        get_active_admin_wheel(user.id)
        or get_shop_repick(user.id)
        or get_admin_item_grant(user.id)
    ):
        if user.turn_phase == "wheel":
            user.turn_phase = "wheel_ready"
            db.session.commit()
        return None

    if user.turn_phase in ("wheel_ready", "wheel"):
        user.turn_phase = "idle"
        db.session.commit()
    return None


def open_extra_wheel_for_user(user: User) -> dict | tuple[dict, int]:
    """HTTP: открыть доп. колесо приколов вне клетки."""
    from backend.turn_logic import require_phase

    if extra_wheel_spins_left(user.id) <= 0:
        return {"error": "Нет дополнительных прокрутов колеса"}, 400
    err = require_phase(user, "wheel_ready")
    if err and user.turn_phase not in ("wheel_ready", "idle", "playing"):
        return {"error": err}, 400
    prepare_extra_wheel_turn(user)
    cell = user.position
    from backend.board import BOARD_BY_ID

    extra = open_extra_item_wheel(
        user,
        cell_name=BOARD_BY_ID[cell].name if cell in BOARD_BY_ID else "?",
        dice_label="?",
    )
    if not extra:
        return {"error": "Не удалось открыть колесо"}, 400
    return extra


def open_extra_item_wheel(
    user: User,
    *,
    cell_name: str,
    dice_label: str,
    username: str | None = None,
) -> dict | None:
    """Открыть ещё одно колесо приколов (списывает 1 доп. прокрут)."""
    if extra_wheel_spins_left(user.id) <= 0:
        return None

    from backend.pending_wheels import pending_item_wheel

    consume_one_extra_wheel_spin(user.id)
    picked = pick_wheel_items(12, user_id=user.id)
    pending_item_wheel[user.id] = [i.to_dict() for i in picked]
    user.turn_phase = "wheel"
    db.session.commit()

    from backend.items.gameplay import collect_vote_banners

    left = extra_wheel_spins_left(user.id)
    return {
        "username": username or user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "wheel": wheel_labels(picked),
        "wheelType": "item",
        "wheelItems": pending_item_wheel[user.id],
        "source": {"itemWheel": True, "extraWheel": True},
        "cellName": cell_name,
        "diceLabel": dice_label,
        "extraWheelSpinsRemaining": left,
        "openExtraWheel": True,
        "user": user.to_public_dict(),
        "voteLabels": collect_vote_banners(user.id),
    }
