"""Мгновенные эффекты с колеса приколов."""

from __future__ import annotations

from backend.board import BOARD_BY_ID, BOARD_SIZE
from backend.items import inventory as inv
from backend.items.effects import EffectContext
from backend.items.modifiers import _add_mod, count_inventory_debuffs
from backend.models import PlayerInventoryItem, PlayerModifier, User, db
from backend.random_utils import choice, randbelow


def _maybe_set_wheel_ready(user: User) -> None:
    if user.turn_phase != "playing":
        user.turn_phase = "wheel_ready"


def apply_instant_wheel_effect(ctx: EffectContext, user: User) -> None:
    key = ctx.item.effect.split(":")[0] if ctx.item.effect else ""
    name = ctx.item.name

    if key == "wheel_reroll":
        from backend.items.wheel_extras import add_extra_wheel_spins

        add_extra_wheel_spins(user.id, 1, label="Интрига")
        ctx.note("«Интрига»: +1 прокрут колеса приколов")
        db.session.commit()
        return

    if key in ("shop_chat", "shop_leprechaun"):
        from backend.items.wheel_extras import add_extra_wheel_spins, prepare_extra_wheel_turn
        from backend.pending_wheels import set_shop_repick

        mode = "chat" if key == "shop_chat" else "leprechaun"
        add_extra_wheel_spins(user.id, 1, label=name)
        set_shop_repick(user.id, mode, effect_item_id=ctx.item.id)
        prepare_extra_wheel_turn(user)
        hint = (
            "чат голосует между 5 секторами"
            if mode == "chat"
            else "выберите 2 сектора из 5"
        )
        ctx.note(
            f"«{name}»: +1 прокрут колеса приколов; на rerolle {hint}; "
            "предметы выдаёт админ"
        )
        db.session.commit()
        return

    if key == "wheel_extra":
        n = int(ctx.item.effect.split(":")[1] or "1")
        from backend.items.wheel_extras import add_extra_wheel_spins

        add_extra_wheel_spins(user.id, n, label=name)
        if n > 0:
            _maybe_set_wheel_ready(user)
        db.session.commit()
        ctx.note(f"«{name}»: +{n} доп. колёс приколов")
        return

    if key == "bandit":
        rows = PlayerInventoryItem.query.filter_by(user_id=user.id).all()
        count = sum(r.quantity for r in rows)
        phase = user.turn_phase
        PlayerInventoryItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        from backend.items.wheel_extras import add_extra_wheel_spins, prepare_extra_wheel_turn

        add_extra_wheel_spins(user.id, count, label="Однорукий бандит")
        prepare_extra_wheel_turn(user)
        db.session.commit()
        ctx.note(
            f"«Однорукий бандит»: сброшено {count} предметов → {count} доп. колёс"
        )
        return

    if key == "dirtykin":
        eaten = inv.remove_random_buff(user.id)
        ctx.note(
            f"«Грязнулькин»: съел «{eaten}»" if eaten else "«Грязнулькин»: нечего съесть"
        )
        return

    if key == "castling":
        tid = ctx.options.get("targetUserId")
        if not tid:
            ctx.note("«Рокировочка»: укажите игрока")
            return
        other = db.session.get(User, int(tid))
        if not other:
            ctx.note("Игрок не найден")
            return
        user.position, other.position = other.position, user.position
        ctx.note(f"«Рокировочка» с {other.username}")
        db.session.commit()
        return

    if key == "swap_inv_random":
        players = User.query.filter(
            User.is_player == True, User.id != user.id
        ).all()
        if not players:
            ctx.note("Нет других игроков")
            return
        other = choice(players)
        inv.swap_inventories(user.id, other.id)
        ctx.note(f"«Mine now»: обмен с {other.username}")
        return

    if key == "help_laggard":
        ranked = (
            User.query.filter_by(is_player=True)
            .order_by(User.points.desc())
            .all()
        )
        place = next((i for i, u in enumerate(ranked) if u.id == user.id), 0) + 1
        delta = 0
        if place <= 2:
            delta = -2
        elif place <= 4:
            delta = 2
        else:
            delta = 2
            user.points += 1
            ctx.note("«Помощь отстающему»: +1 очко (последнее место)")
        _add_mod(
            user.id,
            "help_laggard",
            str(delta),
            1,
            item_id=34,
            label="Помощь отстающему",
        )
        ctx.note(f"«Помощь отстающему»: {delta:+d} к след. броску")
        db.session.commit()
        return

    if key == "hurry":
        _add_mod(user.id, "hurry", "1", 1, item_id=36, label="Торопыга", polarity="debuff")
        ctx.note("«Торопыга»: след. клетка — 1 базовый поинт")
        return

    if key == "trinity_dice":
        _add_mod(
            user.id,
            "trinity_dice",
            "1",
            1,
            item_id=37,
            label="Бог любит троицу",
        )
        ctx.note("«Бог любит троицу»: на след. ход 3 кубика")
        return

    if key == "base_only_next":
        _add_mod(
            user.id,
            "base_only_next",
            "1",
            1,
            item_id=47,
            label="УВЫ",
            polarity="debuff",
        )
        ctx.note("«УВЫ»: след. игра — только базовые очки")
        return

    if key == "hour_growth":
        _add_mod(user.id, "hour_growth", "1", 1, item_id=48, label="Часовой рост")
        ctx.note("«Часовой рост»: на след. клетке ×2 за 10ч")
        return

    ctx.note(f"«{name}» ({key})")
