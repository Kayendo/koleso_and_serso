"""Мгновенные эффекты с колеса приколов."""

from __future__ import annotations

from backend.board import BOARD_BY_ID, BOARD_SIZE
from backend.items import inventory as inv
from backend.items.effects import EffectContext
from backend.items.modifiers import _add_mod, count_inventory_debuffs
from backend.models import PlayerInventoryItem, PlayerModifier, User, db
from backend.random_utils import choice, randbelow


def apply_instant_wheel_effect(ctx: EffectContext, user: User) -> None:
    key = ctx.item.effect.split(":")[0] if ctx.item.effect else ""
    name = ctx.item.name

    if key == "wheel_reroll":
        ctx.note("«Интрига»: реролл колеса — откройте колесо снова")
        user.turn_phase = "wheel_ready"
        db.session.commit()
        return

    if key == "two_for_one":
        ctx.note("«Два по цене одного»: примените верхний и нижний соседние пункты (вручную)")
        user.turn_phase = "wheel_ready"
        db.session.commit()
        return

    if key in ("shop_chat", "shop_leprechaun"):
        ctx.note(f"«{name}»: выбор соседей/голосование — зафиксируйте вручную")
        return

    if key == "oops_neighbor":
        ctx.note(
            "«Ой, извините»: пункт недоступен — при подтверждении колеса выберите соседний сектор"
        )
        return

    if key == "wheel_extra":
        n = int(ctx.item.effect.split(":")[1] or "1")
        _add_mod(user.id, "wheel_extra_spins", str(n), n, label=name)
        ctx.note(f"«{name}»: +{n} прокрут(а) колеса")
        return

    if key == "bandit":
        rows = PlayerInventoryItem.query.filter_by(user_id=user.id).all()
        count = sum(r.quantity for r in rows)
        PlayerInventoryItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        ctx.note(f"«Однорукий бандит»: сброшено {count} предметов → {count} колёс")
        _add_mod(user.id, "wheel_extra_spins", str(count), count, label="Бандит")
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

    if key == "first_aid":
        mode = ctx.options.get("mode")
        if mode == "drop_debuff":
            from backend.items.gameplay import PROTECTED_DEBUFF_KEYS

            mods = [
                m
                for m in PlayerModifier.query.filter_by(
                    user_id=user.id, polarity="debuff"
                ).all()
                if m.effect_key not in PROTECTED_DEBUFF_KEYS
            ]
            if mods:
                db.session.delete(mods[0])
                user.points = max(0, user.points - 1)
                ctx.note("Аптечка: сброшен дебафф, −1 очко")
            else:
                ctx.note("Нет дебаффа для сброса")
        elif mode == "drop_buff":
            mods = PlayerModifier.query.filter_by(
                user_id=user.id, polarity="buff"
            ).all()
            if mods:
                db.session.delete(mods[0])
                user.points += 1
                ctx.note("Аптечка: сброшен бафф, +1 очко")
            else:
                buff_row = PlayerInventoryItem.query.filter_by(user_id=user.id).first()
                if buff_row:
                    inv.consume_inventory_item(user.id, buff_row.item_def_id)
                    user.points += 1
                    ctx.note("Аптечка: сброшен предмет-бафф, +1 очко")
        else:
            ctx.note("«Аптечка»: выберите режим (drop_debuff / drop_buff)")
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

    if key == "lucky_loser":
        n = count_inventory_debuffs(user.id)
        _add_mod(
            user.id,
            "lucky_loser",
            str(n),
            1,
            item_id=35,
            label="Удачный неудачник",
        )
        ctx.note(f"«Удачный неудачник»: +{n} к броску за дебаффы")
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

    if key == "coin_dice":
        side = ctx.options.get("side") or ("орёл" if randbelow(2) else "решка")
        delta = 2 if side in ("орёл", "heads", "+") else -2
        _add_mod(
            user.id,
            "coin_dice",
            str(delta),
            1,
            item_id=38,
            label="Орел или решка",
        )
        ctx.note(f"«Орел или решка»: {side} → {delta:+d} к броску")
        return

    if key == "where_am_i":
        players = User.query.filter(
            User.is_player == True, User.id != user.id
        ).all()
        if not players:
            return
        other = choice(players)
        cell = BOARD_BY_ID.get(other.position)
        cid = other.position
        even_or_corner = cid % 2 == 0 or cid in (0, 10, 20, 30)
        if even_or_corner:
            other.points += 1
            ctx.note(f"«А где это я?»: {other.username} +1 (чётная/угловая)")
        else:
            other.points = max(0, other.points - 1)
            ctx.note(f"«А где это я?»: {other.username} −1")
        db.session.commit()
        return

    if key in ("chat_law", "i_am_law"):
        ctx.note(f"«{name}»: выбор категории/игры — следующий ход вручную")
        _add_mod(user.id, key, "1", 1, item_id=ctx.item.id, label=name)
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
