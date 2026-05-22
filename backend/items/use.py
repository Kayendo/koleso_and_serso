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
    if not row or row.quantity < 1:
        return {"error": "Предмета нет в инвентаре"}, 400

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
        if not target_row or target_row.quantity < 1:
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

    if item.polarity == "buff":
        exp = PlayerInventoryItem.query.filter_by(user_id=user.id, item_def_id=7).first()
        if exp and exp.quantity > 0:
            exp.quantity -= 1
            if exp.quantity <= 0:
                db.session.delete(exp)
            db.session.commit()
            if not _explosives_roll(user.id, options):
                return {
                    "ok": False,
                    "message": "Взрывчатка: эффект не сработал",
                    "user": user.to_public_dict(),
                }

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

    if item.id == 5:
        active = (
            PlayerGame.query.filter_by(user_id=user.id, status="active")
            .order_by(PlayerGame.id.desc())
            .first()
        )
        if active:
            user.turn_phase = "wheel_ready"
            ctx.note("«Свиток реролла»: откройте колесо заново")
            db.session.commit()
    elif item.id == 6:
        ctx.note("«Шар всезнания»: гайд/спидран разрешён")
    elif item.id == 15 and options.get("genreId"):
        ctx.note(f"«Шоколад»: жанр {options['genreId']}")
    else:
        apply_item_effect(ctx, subject, db)

    log_turn(
        user.id,
        summary=f"Предмет: {item.name}",
        factors=ctx.factors,
        extra={"itemId": item.id, "targetUserId": target_user_id},
    )

    return {
        "ok": True,
        "factors": ctx.factors,
        "user": user.to_public_dict(),
        "targetUser": target.to_public_dict() if target else None,
    }
