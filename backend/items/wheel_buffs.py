"""Баффы на колесо из инвентаря (магазины, законы)."""

from __future__ import annotations

from backend.board import BOARD_BY_ID
from backend.items.effects import EffectContext
from backend.items.wheel_extras import add_extra_wheel_spins, prepare_extra_wheel_turn
from backend.models import User, db


def activate_shop_buff(ctx: EffectContext, user: User, *, mode: str) -> None:
    from backend.items.modifiers import _add_mod
    from backend.pending_wheels import set_shop_repick

    if user.turn_phase != "wheel_ready":
        ctx.note("Используйте после броска кубика, перед колесом приколов")
        return

    key = "shop_chat_buff" if mode == "chat" else "shop_leprechaun_buff"
    label = ctx.item.name
    add_extra_wheel_spins(user.id, 1, label=label)
    _add_mod(
        user.id,
        key,
        mode,
        1,
        item_id=ctx.item.id,
        label=label,
        desc="Следующий ролл колеса приколов — эффект магазина",
    )
    set_shop_repick(user.id, mode, effect_item_id=ctx.item.id)
    prepare_extra_wheel_turn(user)
    hint = (
        "чат выберет из 5 секторов"
        if mode == "chat"
        else "выберите 2 сектора из 5"
    )
    ctx.note(
        f"«{label}»: +1 прокрут колеса приколов; на rerolle {hint}; "
        "предметы выдаёт админ"
    )
    db.session.commit()


def activate_law_buff(ctx: EffectContext, user: User) -> None:
    from backend.items.admin_wheel import activate_law_buff_pending

    if user.turn_phase != "wheel_ready":
        ctx.note("Используйте после броска кубика, перед колесом игр")
        return
    cell = BOARD_BY_ID[user.position]
    if cell.cell_type == "trap_joy":
        ctx.note("На клетке предметов законы не активируются")
        return

    activate_law_buff_pending(ctx, user)
