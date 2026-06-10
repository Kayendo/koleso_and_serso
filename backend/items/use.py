"""Использование предметов из инвентаря."""

from __future__ import annotations

from backend.items.catalog import get_item
from backend.items.effects import EffectContext, apply_item_effect
from backend.items.inventory import consume_inventory_item, log_turn
from backend.models import PlayerGame, PlayerInventoryItem, User, db


def _explosives_roll(user_id: int, options: dict) -> bool:
    side = options.get("coinSide")
    if side in ("yes", "да", "success", "1"):
        return True
    if side in ("no", "нет", "fail", "0"):
        return False
    import secrets

    return secrets.randbelow(2) == 0


def _try_explosives_on_buff_use(user: User, item: "ItemDef", options: dict) -> str | None:
    """Списать заряд взрывчатки и вернуть 'survived' | 'exploded' | None."""
    if item.polarity != "buff" or item.kind != "item":
        return None
    from backend.items.inventory import consume_inventory_item, has_item

    if not has_item(user.id, 7):
        return None
    if not consume_inventory_item(user.id, 7, 1):
        return None
    return "survived" if _explosives_roll(user.id, options) else "exploded"


def use_inventory_item(
    user: User,
    item_id: int,
    *,
    target_user_id: int | None = None,
    options: dict | None = None,
) -> dict | tuple[dict, int]:
    item = get_item(item_id)
    if not item:
        return {"error": "Неизвестный предмет"}, 400

    options = options or {}
    is_trap = item.kind == "trap"

    if is_trap and not target_user_id:
        return {"error": "Укажите цель для ловушки"}, 400

    row = PlayerInventoryItem.query.filter_by(
        user_id=user.id, item_def_id=item_id
    ).first()
    from backend.items.inventory import _ensure_charges

    if not row:
        return {"error": "Предмета нет в инвентаре"}, 400
    _ensure_charges(row)
    if row.charges_remaining < 1:
        return {"error": "Предмета нет в инвентаре"}, 400

    from backend.items.pairs import use_blocked_by_conflict

    blocked, conflict_notes = use_blocked_by_conflict(user.id, item_id)
    if blocked:
        ctx = EffectContext(
            user_id=user.id,
            item=item,
            actor_username=user.username,
            options=options,
        )
        ctx.factors.extend(conflict_notes)
        log_turn(
            user.id,
            summary=f"Предмет: {item.name}",
            factors=ctx.factors,
            extra={"itemId": item.id, "mutualDestroy": True},
        )
        return {
            "ok": True,
            "factors": ctx.factors,
            "user": user.to_public_dict(),
        }

    if item.id == 9:
        tid = options.get("targetItemId")
        if tid is None:
            return {"error": "Выберите предмет для ремонта (не Шоколад)"}, 400
        try:
            tid = int(tid)
        except (TypeError, ValueError):
            return {"error": "Некорректный предмет для ремонта"}, 400
        if tid == 15:
            return {"error": "Шоколад нельзя чинить ремонтным набором"}, 400
        target_row = PlayerInventoryItem.query.filter_by(
            user_id=user.id, item_def_id=tid
        ).first()
        from backend.items.inventory import _ensure_charges

        if not target_row:
            return {"error": "Этого предмета нет в вашем инвентаре"}, 400
        _ensure_charges(target_row)
        if target_row.charges_remaining < 1:
            return {"error": "Этого предмета нет в вашем инвентаре"}, 400

    if item.id == 11:
        from backend.items.modifiers import _has_mod
        from backend.items.resolve_user import resolve_user_id

        partner_id = options.get("partnerUserId")
        if partner_id is None:
            pid, perr = resolve_user_id(username=options.get("partnerUsername"))
            if perr:
                return {"error": perr}, 400
            partner_id = pid
        if not partner_id:
            return {"error": "Укажите партнёра для колец"}, 400
        partner = db.session.get(User, int(partner_id))
        if not partner or partner.id == user.id:
            return {"error": "Некорректный партнёр"}, 400
        if _has_mod(user.id, "time_ring_partner"):
            return {"error": "У вас уже активны кольца"}, 400
        if _has_mod(partner.id, "time_ring_partner"):
            return {
                "error": f"У {partner.username} уже есть связь колец",
            }, 400

    if item.id == 15:
        if user.turn_phase != "wheel_ready":
            return {
                "error": "Шоколад можно использовать только после броска кубика, перед колесом игр",
            }, 400
        genre_raw = options.get("genreId")
        if genre_raw is None:
            from backend.board import GENRE_LABELS, GENRE_SHORT_LABELS

            return {
                "error": "Выберите категорию игр",
                "needsGenrePick": True,
                "genres": [
                    {
                        "id": gid,
                        "label": GENRE_LABELS[gid],
                        "shortLabel": GENRE_SHORT_LABELS.get(gid, GENRE_LABELS[gid]),
                        "buttonLabel": GENRE_SHORT_LABELS.get(gid, GENRE_LABELS[gid]),
                    }
                    for gid in sorted(GENRE_LABELS)
                ],
            }, 400
        try:
            genre_id = int(genre_raw)
        except (TypeError, ValueError):
            return {"error": "Некорректная категория игр"}, 400
        from backend.board import GENRE_LABELS

        if genre_id not in GENRE_LABELS:
            return {"error": "Неизвестная категория игр"}, 400

    if item.id in (24, 25):
        if user.turn_phase != "wheel_ready":
            return {
                "error": "Используйте после броска кубика, перед колесом приколов",
            }, 400

    if item.id in (40, 41):
        if user.turn_phase != "wheel_ready":
            return {
                "error": "Используйте после броска кубика, перед колесом игр",
            }, 400
        from backend.board import BOARD_BY_ID

        if BOARD_BY_ID[user.position].cell_type == "trap_joy":
            return {"error": "На клетке предметов законы не используются"}, 400

    explosives_roll = _try_explosives_on_buff_use(user, item, options)

    if not consume_inventory_item(user.id, item_id):
        return {"error": "Не удалось списать предмет"}, 400

    target = db.session.get(User, int(target_user_id)) if target_user_id else None
    subject = target or user
    ctx = EffectContext(
        user_id=subject.id,
        item=item,
        actor_username=user.username,
        target_user_id=target.id if target else None,
        options=options,
    )
    ctx.note(f"{user.username}: «{item.name}»")

    apply_effect = explosives_roll != "exploded"
    if apply_effect:
        if item.id == 5:
            from backend.items.gameplay import clear_gameplay_modifiers_for_reroll

            active = (
                PlayerGame.query.filter_by(user_id=user.id, status="active")
                .order_by(PlayerGame.id.desc())
                .first()
            )
            cleared = clear_gameplay_modifiers_for_reroll(user.id)
            ctx.factors.extend(cleared)
            if active:
                active.gameplay_tags = "[]"
                user.turn_phase = "wheel_ready"
                ctx.note("«Свиток реролла»: откройте колесо заново")
                db.session.commit()
        elif item.id == 15:
            from backend.board import GENRE_LABELS
            from backend.pending_wheels import set_chocolate_genre

            gid = int(options["genreId"])
            set_chocolate_genre(user.id, gid)
            label = GENRE_LABELS.get(gid, f"Жанр {gid}")
            ctx.note(f"«Шоколад»: колесо — категория «{label}»")
        else:
            apply_item_effect(ctx, subject, db)
    elif explosives_roll == "exploded":
        ctx.note("«Взрывчатка»: ВЫ ВЗОРВАЛИСЬ — эффект предмета не сработал")

    log_turn(
        user.id,
        summary=f"Предмет: {item.name}",
        factors=ctx.factors,
        extra={
            "itemId": item.id,
            "targetUserId": target_user_id,
            "explosivesRoll": explosives_roll,
        },
    )
    if apply_effect and target and target.id != user.id:
        from backend.items.inventory import log_target_effect

        log_target_effect(
            target.id,
            actor_username=user.username,
            item_name=item.name,
            factors=ctx.factors,
            item_id=item.id,
        )

    payload = {
        "ok": apply_effect,
        "factors": ctx.factors,
        "user": user.to_public_dict(),
        "targetUser": target.to_public_dict() if target else None,
    }
    if explosives_roll:
        payload["explosivesRoll"] = explosives_roll
        payload["explosivesMessage"] = (
            "ВЫ УЦЕЛЕЛИ" if explosives_roll == "survived" else "ВЫ ВЗОРВАЛИСЬ"
        )
    return payload
