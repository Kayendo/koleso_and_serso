"""Инвентарь, баффы/дебаффы, журнал хода."""

from __future__ import annotations

import json

from backend.items.catalog import ItemDef, get_item
from backend.items.pairs import MUTUAL_DESTROY
from backend.models import PlayerInventoryItem, PlayerModifier, TurnLog, User, db


def _charges_from_effect(item: ItemDef) -> int:
    if not item.effect or ":" not in item.effect:
        return 1
    _, val = item.effect.split(":", 1)
    try:
        return max(1, int(val.strip()))
    except ValueError:
        return 1


def grant_inventory_item(
    user_id: int,
    item_def_id: int,
    quantity: int | None = None,
    *,
    is_trap: bool = False,
) -> list[str]:
    """Вернуть заметки о взаимоисключениях."""
    notes: list[str] = []
    defn = get_item(item_def_id)
    if not defn:
        return notes
    if quantity is None:
        quantity = _charges_from_effect(defn)
    if defn.kind == "trap":
        is_trap = True

    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    if row:
        row.quantity += quantity
        row.is_trap = row.is_trap or is_trap
    else:
        db.session.add(
            PlayerInventoryItem(
                user_id=user_id,
                item_def_id=item_def_id,
                quantity=quantity,
                is_trap=is_trap,
            )
        )
    db.session.commit()
    notes.extend(_mutual_destroy(user_id, item_def_id))
    return notes


def _mutual_destroy(user_id: int, new_id: int) -> list[str]:
    notes = []
    for a, b in MUTUAL_DESTROY:
        other = b if new_id == a else a if new_id == b else None
        if other is None:
            continue
        if has_item(user_id, new_id) and has_item(user_id, other):
            remove_all(user_id, new_id)
            remove_all(user_id, other)
            na = get_item(a)
            nb = get_item(b)
            notes.append(
                f"«{na.name if na else a}» и «{nb.name if nb else b}» уничтожили друг друга"
            )
    return notes


def has_item(user_id: int, item_def_id: int) -> bool:
    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    return bool(row and row.quantity > 0)


def remove_all(user_id: int, item_def_id: int) -> None:
    PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).delete()
    db.session.commit()


def remove_random_buff(user_id: int) -> str | None:
    rows = PlayerInventoryItem.query.filter_by(user_id=user_id).all()
    buffs = []
    for row in rows:
        d = get_item(row.item_def_id)
        if d and d.polarity == "buff" and d.kind == "item" and row.quantity > 0:
            buffs.append(row)
    if not buffs:
        return None
    from backend.random_utils import choice

    row = choice(buffs)
    name = get_item(row.item_def_id).name if get_item(row.item_def_id) else "?"
    row.quantity -= 1
    if row.quantity <= 0:
        db.session.delete(row)
    db.session.commit()
    return name


def remove_random_item(user_id: int) -> str | None:
    rows = [
        r
        for r in PlayerInventoryItem.query.filter_by(user_id=user_id).all()
        if r.quantity > 0
    ]
    if not rows:
        return None
    from backend.random_utils import choice

    row = choice(rows)
    name = get_item(row.item_def_id).name if get_item(row.item_def_id) else "?"
    row.quantity -= 1
    if row.quantity <= 0:
        db.session.delete(row)
    db.session.commit()
    return name


def add_status_from_item(user_id: int, item: ItemDef) -> None:
    if item.duration_turns <= 0:
        return
    db.session.add(
        PlayerModifier(
            user_id=user_id,
            source_item_id=item.id,
            polarity=item.polarity,
            label=item.name,
            description=item.description,
            effect_key=item.effect.split(":")[0] if item.effect else "",
            effect_value=item.effect.split(":", 1)[1] if ":" in item.effect else "",
            turns_remaining=item.duration_turns,
        )
    )
    db.session.commit()


def add_user_modifier(
    user_id: int,
    effect_key: str,
    effect_value: int | str,
    turns: int,
    *,
    source_item_id: int | None = None,
    label: str = "",
    description: str = "",
    polarity: str = "buff",
) -> None:
    db.session.add(
        PlayerModifier(
            user_id=user_id,
            source_item_id=source_item_id,
            polarity=polarity,
            label=label or effect_key,
            description=description,
            effect_key=effect_key,
            effect_value=str(effect_value),
            turns_remaining=turns if turns > 0 else 99,
        )
    )
    db.session.commit()


def log_turn(
    user_id: int,
    *,
    summary: str,
    factors: list[str],
    dice_label: str = "",
    cell_name: str = "",
    extra: dict | None = None,
) -> TurnLog:
    payload = {
        "dice": dice_label,
        "cell": cell_name,
        "factors": factors,
        **(extra or {}),
    }
    row = TurnLog(
        user_id=user_id,
        summary=summary,
        factors_json=json.dumps(payload, ensure_ascii=False),
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_inventory_state(user_id: int, *, include_history: bool = False) -> dict:
    items_out = []
    for row in PlayerInventoryItem.query.filter_by(user_id=user_id).all():
        defn = get_item(row.item_def_id)
        if not defn:
            continue
        items_out.append(
            {
                "itemId": row.item_def_id,
                "name": defn.name,
                "description": defn.description,
                "quantity": row.quantity,
                "charges": row.quantity,
                "isTrap": row.is_trap,
                "polarity": defn.polarity,
                "kind": defn.kind,
                "effect": defn.effect,
            }
        )

    from backend.items.gameplay import enrich_modifier_entry

    buffs, debuffs = [], []
    for mod in PlayerModifier.query.filter_by(user_id=user_id).order_by(
        PlayerModifier.id.desc()
    ).all():
        entry = enrich_modifier_entry(mod)
        if mod.polarity == "debuff":
            debuffs.append(entry)
        else:
            buffs.append(entry)

    out: dict = {
        "items": items_out,
        "buffs": buffs,
        "debuffs": debuffs,
    }
    if include_history:
        logs = (
            TurnLog.query.filter_by(user_id=user_id)
            .order_by(TurnLog.id.desc())
            .limit(50)
            .all()
        )
        out["turnHistory"] = [t.to_dict() for t in logs]
    return out


def tick_modifiers_after_turn(user_id: int) -> list[str]:
    from backend.items.gameplay import NO_TICK_ON_TURN, TICK_ON_GAME_END

    notes = []
    for mod in PlayerModifier.query.filter_by(user_id=user_id).all():
        if mod.turns_remaining <= 0:
            continue
        if (
            mod.effect_key in TICK_ON_GAME_END
            or mod.effect_key in NO_TICK_ON_TURN
            or mod.effect_key.endswith("_wait")
        ):
            continue
        if mod.effect_key == "slave":
            continue
        mod.turns_remaining -= 1
        if mod.turns_remaining <= 0:
            notes.append(f"Снят эффект «{mod.label}»")
            db.session.delete(mod)
    db.session.commit()
    return notes


def consume_inventory_item(user_id: int, item_def_id: int, amount: int = 1) -> bool:
    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    if not row or row.quantity < amount:
        return False
    row.quantity -= amount
    if row.quantity <= 0:
        db.session.delete(row)
    db.session.commit()
    return True


def swap_inventories(user_a: int, user_b: int) -> None:
    rows_a = PlayerInventoryItem.query.filter_by(user_id=user_a).all()
    rows_b = PlayerInventoryItem.query.filter_by(user_id=user_b).all()
    for r in rows_a:
        r.user_id = user_b
    for r in rows_b:
        r.user_id = user_a
    db.session.commit()
