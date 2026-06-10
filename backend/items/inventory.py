"""Инвентарь, баффы/дебаффы, журнал хода."""

from __future__ import annotations

import json
import math

from backend.items.catalog import ItemDef, get_item
from backend.items.pairs import resolve_conflicts
from backend.models import PlayerInventoryItem, PlayerModifier, TurnLog, User, db


def _effect_key_val(item: ItemDef) -> tuple[str, str]:
    if not item.effect or ":" not in item.effect:
        return item.effect or "", ""
    key, val = item.effect.split(":", 1)
    return key.strip(), val.strip()


def charges_per_unit(item_def_id: int) -> int:
    defn = get_item(item_def_id)
    if not defn:
        return 1
    key, _ = _effect_key_val(defn)
    if key == "time_rings":
        return 1
    return _charges_from_effect(defn)


def effect_duration_turns(item_def_id: int) -> int:
    """Число после «:» для time_rings — длительность баффа в бросках, не заряды."""
    defn = get_item(item_def_id)
    if not defn:
        return 1
    key, val = _effect_key_val(defn)
    if key == "time_rings":
        try:
            return max(1, int(val))
        except ValueError:
            return 4
    return max(1, defn.duration_turns or 1)


def _charges_from_effect(item: ItemDef) -> int:
    if not item.effect or ":" not in item.effect:
        return 1
    key, val = _effect_key_val(item)
    if key == "time_rings":
        return 1
    try:
        return max(1, int(val))
    except ValueError:
        return 1


def _sync_quantity_from_charges(row: PlayerInventoryItem, per_unit: int) -> None:
    if row.charges_remaining is None:
        row.charges_remaining = row.quantity * per_unit
    if row.charges_remaining <= 0:
        row.quantity = 0
    else:
        row.quantity = max(1, math.ceil(row.charges_remaining / per_unit))


def _ensure_charges(row: PlayerInventoryItem) -> int:
    per = charges_per_unit(row.item_def_id)
    if row.charges_remaining is None:
        row.charges_remaining = max(0, row.quantity) * per
    return per


def grant_inventory_item(
    user_id: int,
    item_def_id: int,
    quantity: int | None = None,
    *,
    is_trap: bool = False,
) -> list[str]:
    """quantity — число предметов (не зарядов)."""
    notes: list[str] = []
    defn = get_item(item_def_id)
    if not defn:
        return notes
    item_count = max(1, int(quantity if quantity is not None else 1))
    per = _charges_from_effect(defn)
    add_charges = item_count * per
    if defn.kind == "trap":
        is_trap = True

    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    if row:
        per = _ensure_charges(row)
        row.charges_remaining = int(row.charges_remaining or 0) + add_charges
        _sync_quantity_from_charges(row, per)
        row.is_trap = row.is_trap or is_trap
    else:
        db.session.add(
            PlayerInventoryItem(
                user_id=user_id,
                item_def_id=item_def_id,
                quantity=item_count,
                charges_remaining=add_charges,
                is_trap=is_trap,
            )
        )
    db.session.commit()
    notes.extend(resolve_conflicts(user_id))
    return notes


def log_item_received(
    user_id: int,
    item: ItemDef,
    *,
    quantity: int = 1,
    source: str = "выдача",
    extra_notes: list[str] | None = None,
) -> TurnLog:
    per = _charges_from_effect(item)
    total_charges = quantity * per
    factors = [
        f"Получен: «{item.name}» ×{quantity}",
        f"Зарядов: {total_charges}",
        f"Источник: {source}",
    ]
    if extra_notes:
        factors.extend(extra_notes)
    return log_turn(
        user_id,
        summary=f"Предмет: {item.name}",
        factors=factors,
        extra={"itemId": item.id, "itemReceived": True, "source": source},
    )


def log_item_interaction(
    user_id: int,
    *,
    summary: str,
    factors: list[str],
    extra: dict | None = None,
) -> TurnLog:
    return log_turn(user_id, summary=summary, factors=factors, extra=extra)


def has_item(user_id: int, item_def_id: int) -> bool:
    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    if not row:
        return False
    _ensure_charges(row)
    return int(row.charges_remaining or 0) > 0


def remove_all(user_id: int, item_def_id: int) -> None:
    PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).delete()
    db.session.commit()


def _remove_one_item_unit(row: PlayerInventoryItem) -> None:
    per = _ensure_charges(row)
    if row.charges_remaining <= 0:
        return
    rem = int(row.charges_remaining) % per
    deduct = rem if rem != 0 else per
    row.charges_remaining -= deduct
    _sync_quantity_from_charges(row, per)
    if row.charges_remaining <= 0:
        db.session.delete(row)


def remove_random_buff(user_id: int) -> str | None:
    rows = PlayerInventoryItem.query.filter_by(user_id=user_id).all()
    buffs = []
    for row in rows:
        d = get_item(row.item_def_id)
        _ensure_charges(row)
        if d and d.polarity == "buff" and d.kind == "item" and row.charges_remaining > 0:
            buffs.append(row)
    if not buffs:
        return None
    from backend.random_utils import choice

    row = choice(buffs)
    name = get_item(row.item_def_id).name if get_item(row.item_def_id) else "?"
    _remove_one_item_unit(row)
    db.session.commit()
    return name


def remove_random_item(user_id: int) -> str | None:
    rows = []
    for r in PlayerInventoryItem.query.filter_by(user_id=user_id).all():
        _ensure_charges(r)
        if r.charges_remaining > 0:
            rows.append(r)
    if not rows:
        return None
    from backend.random_utils import choice

    row = choice(rows)
    name = get_item(row.item_def_id).name if get_item(row.item_def_id) else "?"
    _remove_one_item_unit(row)
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


def log_target_effect(
    target_user_id: int,
    *,
    actor_username: str,
    item_name: str,
    factors: list[str],
    item_id: int | None = None,
) -> TurnLog | None:
    if not target_user_id:
        return None
    lines = [f"{actor_username} использовал «{item_name}» на вас"]
    lines.extend(factors)
    return log_turn(
        target_user_id,
        summary=f"На вас: «{item_name}»",
        factors=lines,
        extra={"itemId": item_id, "actorUsername": actor_username},
    )


def get_inventory_state(user_id: int, *, include_history: bool = False) -> dict:
    items_out = []
    for row in PlayerInventoryItem.query.filter_by(user_id=user_id).all():
        defn = get_item(row.item_def_id)
        if not defn:
            continue
        per = _ensure_charges(row)
        if row.charges_remaining <= 0:
            continue
        items_out.append(
            {
                "itemId": row.item_def_id,
                "name": defn.name,
                "flavor": defn.flavor,
                "description": defn.description,
                "quantity": row.quantity,
                "charges": row.charges_remaining,
                "chargesPerUnit": per,
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
    from backend.items.gameplay import (
        NO_TICK_ON_TURN,
        PERSIST_ON_PLAYER_UNTIL_USED,
        TICK_ON_GAME_END,
    )

    skip = TICK_ON_GAME_END | NO_TICK_ON_TURN | PERSIST_ON_PLAYER_UNTIL_USED
    notes = []
    for mod in PlayerModifier.query.filter_by(user_id=user_id).all():
        if mod.turns_remaining <= 0:
            continue
        if mod.effect_key in skip or mod.effect_key.endswith("_wait"):
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
    """Списать заряд(ы); количество предметов пересчитывается автоматически."""
    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    if not row:
        return False
    per = _ensure_charges(row)
    if row.charges_remaining < amount:
        return False
    row.charges_remaining -= amount
    _sync_quantity_from_charges(row, per)
    if row.charges_remaining <= 0:
        db.session.delete(row)
    db.session.commit()
    return True


def add_item_charges(user_id: int, item_def_id: int, amount: int = 1) -> bool:
    """Ремонтный набор и т.п.: +N зарядов к стопке."""
    row = PlayerInventoryItem.query.filter_by(
        user_id=user_id, item_def_id=item_def_id
    ).first()
    if not row:
        return False
    per = _ensure_charges(row)
    row.charges_remaining = int(row.charges_remaining or 0) + amount
    _sync_quantity_from_charges(row, per)
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
