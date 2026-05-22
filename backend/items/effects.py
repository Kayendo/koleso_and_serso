"""Применение эффектов предметов."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.board import BOARD_BY_ID
from backend.items.catalog import ItemDef, get_item
from backend.items import inventory as inv
from backend.items.modifiers import (
    _add_mod,
    _has_mod,
    apply_completion_points,
    count_inventory_debuffs,
    place_slime_trail,
)
from backend.models import PlayerGame, PlayerInventoryItem, User, db
from backend.random_utils import choice, randbelow


@dataclass
class EffectContext:
    user_id: int
    item: ItemDef
    actor_username: str = ""
    target_user_id: int | None = None
    dice_label: str = ""
    cell_name: str = ""
    options: dict = field(default_factory=dict)
    factors: list[str] = field(default_factory=list)

    def note(self, text: str) -> None:
        self.factors.append(text)


def _key_val(effect: str) -> tuple[str, str]:
    if not effect:
        return "", ""
    if ":" in effect:
        k, v = effect.split(":", 1)
        return k.strip(), v.strip()
    return effect.strip(), ""


def _charges(item: ItemDef) -> int:
    _, v = _key_val(item.effect)
    try:
        return max(1, int(v))
    except ValueError:
        return 1


def apply_item_effect(ctx: EffectContext, user: User, db_sess) -> None:
    key, val = _key_val(ctx.item.effect)
    name = ctx.item.name
    iid = ctx.item.id

    handlers = {
        "cheat_dice": _activate_dice_item,
        "huubik_dice": _activate_dice_item,
        "ez_glasses": _activate_charge_buff,
        "rambo_band": _activate_charge_buff,
        "reroll_game": _activate_simple_use,
        "guide_orb": _activate_simple_use,
        "explosives": _activate_simple_use,
        "wheel_crown": _wheel_crown_activate,
        "repair_kit": _repair_kit,
        "reverse_boots": _activate_charge_buff,
        "time_rings": _time_rings,
        "trap_shawarma": _trap_shawarma,
        "four_leaf": _four_leaf,
        "trap_choker": _trap_choker,
        "chocolate": _activate_simple_use,
        "toilet_paper": _activate_simple_use,
        "leaky_parachute": _activate_simple_use,
        "lucky_thimble": _activate_simple_use,
        "trap_fisting": _trap_fisting,
        "totem_moshnya": _activate_charge_buff,
        "plus_notebook": _grant_passive,
        "trap_rust": _trap_rust,
        "trap_pig": _trap_pig,
        "trap_rake": _trap_rake,
        "trap_slime": _trap_slime,
        "trap_rat": _trap_rat,
    }
    fn = handlers.get(key)
    if fn:
        fn(ctx, user)
        return
    if key.startswith("wheel_") or key in (
        "two_for_one",
        "shop_chat",
        "shop_leprechaun",
        "bandit",
        "dirtykin",
        "castling",
        "first_aid",
        "oops_neighbor",
        "swap_inv_random",
        "help_laggard",
        "lucky_loser",
        "hurry",
        "trinity_dice",
        "coin_dice",
        "where_am_i",
        "chat_law",
        "i_am_law",
        "base_only_next",
        "hour_growth",
    ):
        from backend.items.instant import apply_instant_wheel_effect

        apply_instant_wheel_effect(ctx, user)
        return
    ctx.note(f"«{name}»: эффект {key} (уточните реализацию)")


def _grant_charges(ctx: EffectContext, user: User) -> None:
    """Только пополнение инвентаря (колесо и т.п.), без активации."""
    inv.grant_inventory_item(user.id, ctx.item.id)
    ctx.note(f"«{ctx.item.name}» → инвентарь ({_charges(ctx.item)} зар.)")


def _activate_simple_use(ctx: EffectContext, user: User) -> None:
    ctx.note(f"«{ctx.item.name}» использован (заряд списан)")


def _wheel_crown_activate(ctx: EffectContext, user: User) -> None:
    _add_mod(
        user.id,
        "wheel_crown_pick",
        "1",
        1,
        item_id=ctx.item.id,
        label=ctx.item.name,
        desc="После вращения колеса игр выберите выпавшую игру или соседнюю",
        polarity="buff",
    )
    ctx.note(
        "«Корона колесного короля»: на следующем колесе игр — выбор из трёх соседних игр"
    )


def _activate_dice_item(ctx: EffectContext, user: User) -> None:
    from backend.items.gameplay import activate_buff_for_next_game

    key, _ = _key_val(ctx.item.effect)
    activate_buff_for_next_game(
        user.id,
        f"{key}_ready",
        item_id=ctx.item.id,
        label=ctx.item.name,
        polarity=ctx.item.polarity,
        turns=1,
    )
    ctx.note(f"«{ctx.item.name}»: активен на следующий бросок кубика")


def _activate_charge_buff(ctx: EffectContext, user: User) -> None:
    """Использование из инвентаря: заряд уже списан в use.py."""
    from backend.items.gameplay import activate_buff_for_next_game

    key, _ = _key_val(ctx.item.effect)
    polarity = ctx.item.polarity
    activate_buff_for_next_game(
        user.id,
        key or ctx.item.effect.split(":")[0],
        item_id=ctx.item.id,
        label=ctx.item.name,
        polarity=polarity,
        turns=1,
    )
    hint = {
        "ez_glasses": "лёгкая сложность на следующую игру",
        "rambo_band": "макс. сложность на следующую игру",
        "totem_moshnya": "базово 3 очка на следующую игру",
        "reverse_boots": "движение назад на следующий ход",
        "trinity_dice": "3 кубика на следующий ход",
    }.get(key or "", "эффект на следующую игру")
    ctx.note(f"«{ctx.item.name}»: {hint} (заряд списан)")


def _grant_passive(ctx: EffectContext, user: User) -> None:
    inv.grant_inventory_item(user.id, ctx.item.id)
    ctx.note(f"«{ctx.item.name}» → инвентарь (пассивный)")




def _trap_shawarma(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    if inv.has_item(target.id, 12):
        ctx.note("Цель уже имеет тухлую шаурму")
        return
    _add_mod(
        target.id,
        "trap_shawarma",
        "2",
        2,
        item_id=12,
        label="Тухлая шаурма",
        polarity="debuff",
    )
    ctx.note(f"«Тухлая шаурма» → {target.username}")


def _trap_choker(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    _add_mod(
        target.id,
        "trap_choker",
        "1",
        1,
        item_id=14,
        label="Чокер боли",
        polarity="debuff",
    )
    ctx.note(f"«Чокер боли» → {target.username}")


def _trap_fisting(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx) or user
    if not target:
        return
    thrower = User.query.filter_by(username=ctx.actor_username).first()
    if not thrower:
        ctx.note("Не найден игрок, применивший ловушку")
        return
    if inv.has_item(target.id, 19):
        ctx.note("У цели уже есть рука для fisting")
        return
    _add_mod(
        target.id,
        "slave",
        str(thrower.id),
        5,
        item_id=19,
        label="Рука для fisting",
        desc="0",
        polarity="debuff",
    )
    ctx.note(
        f"«Рука для fisting»: {target.username} — каждый 5-й очко уходит вам (до 5 раз)"
    )


def _trap_rust(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    eaten = inv.remove_random_buff(target.id)
    if eaten:
        ctx.note(f"«Мистер Ржавчик»: съел «{eaten}» у {target.username}")
    else:
        ctx.note("«Мистер Ржавчик»: нечего съесть")


def _trap_pig(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    eaten = inv.remove_random_item(target.id)
    if eaten:
        ctx.note(f"«Всепоглощающий свин»: съел «{eaten}»")
    else:
        ctx.note("«Свин»: инвентарь пуст")


def _trap_rake(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    _add_mod(
        target.id,
        "trap_rake",
        "1",
        1,
        item_id=44,
        label="Грабли",
        polarity="debuff",
    )
    ctx.note(f"«Грабли» → {target.username}")


def _trap_slime(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    _add_mod(
        target.id,
        "trap_slime",
        "1",
        1,
        item_id=45,
        label="Липкая жижа",
        polarity="debuff",
    )
    place_slime_trail(target.id, target.position)
    ctx.note(f"«Липкая жижа» → {target.username}")


def _trap_rat(ctx: EffectContext, user: User) -> None:
    target = _resolve_target(ctx)
    if not target:
        return
    if ctx.options.get("refuse"):
        ctx.note("«Крыса»: отказ — реролл колеса (вручную)")
        return
    _add_mod(
        target.id,
        "trap_rat",
        "3",
        1,
        item_id=46,
        label="Крыса",
        polarity="debuff",
    )
    user.points = max(0, user.points - 1)
    ctx.note(f"«Крыса»: {target.username} −3 к броску, вы −1 очко")


def _four_leaf(ctx: EffectContext, user: User) -> None:
    from backend.items.clover import clover_cell_label, is_clover_cell

    mode = ctx.options.get("mode")
    if mode == "block_trap":
        ctx.note("«Клевер»: ловушка отбита")
        return

    if mode == "cell_bonus":
        if not is_clover_cell(user.position):
            ctx.note("«Клевер»: +2 только на Траллалеро / Лотерее / «?»")
            return
        user.points += 2
        db.session.commit()
        cell = BOARD_BY_ID[user.position]
        ctx.note(
            f"«Клевер» на {clover_cell_label(cell.cell_type)}: +2 очка"
        )
        return

    if mode == "cell_easy":
        if not is_clover_cell(user.position):
            ctx.note("«Клевер»: лёгкая сложность только на Траллалеро / Лотерее / «?»")
            return
        cell = BOARD_BY_ID[user.position]
        _add_mod(
            user.id,
            "four_leaf_easy",
            cell.cell_type,
            1,
            item_id=13,
            label="Клевер: лёгкая сложность",
            desc=cell.name,
        )
        ctx.note(
            f"«Клевер» на {clover_cell_label(cell.cell_type)}: лёгкая сложность на эту игру"
        )
        return

    inv.grant_inventory_item(user.id, 13)
    ctx.note("«Четырехлистный клевер» → инвентарь")


def _repair_kit(ctx: EffectContext, user: User) -> None:
    target_id = ctx.options.get("targetItemId")
    if not target_id or int(target_id) == 15:
        ctx.note("Укажите предмет (не Шоколад)")
        return
    r = PlayerInventoryItem.query.filter_by(
        user_id=user.id, item_def_id=int(target_id)
    ).first()
    if not r:
        ctx.note("Предмет не найден")
        return
    defn = get_item(int(target_id))
    r.quantity += 1
    db.session.commit()
    name = defn.name if defn else f"#{target_id}"
    ctx.note(f"«Ремонтный набор»: +1 заряд «{name}»")


def _time_rings(ctx: EffectContext, user: User) -> None:
    from backend.items.resolve_user import resolve_user_id

    partner_id = ctx.options.get("partnerUserId")
    if partner_id is None:
        pid, err = resolve_user_id(username=ctx.options.get("partnerUsername"))
        if err:
            ctx.note(err)
            return
        partner_id = pid
    if not partner_id:
        ctx.note("Укажите имя или id игрока для колец")
        return
    partner = db.session.get(User, int(partner_id))
    if not partner or partner.id == user.id:
        ctx.note("Некорректный партнёр")
        return
    if _has_mod(user.id, "time_ring_partner"):
        ctx.note("У вас уже активны кольца")
        return
    if _has_mod(partner.id, "time_ring_partner"):
        ctx.note(f"У {partner.username} уже есть связь колец")
        return
    _add_mod(
        user.id,
        "time_ring_partner",
        str(partner.id),
        1,
        item_id=11,
        label="Кольца времени",
        polarity="buff",
    )
    _add_mod(
        partner.id,
        "time_ring_partner",
        str(user.id),
        1,
        item_id=11,
        label="Кольца времени",
        polarity="buff",
    )
    ctx.note(f"«Парные кольца времени» с {partner.username}: +1 к броску")


def _resolve_target(ctx: EffectContext) -> User | None:
    from backend.items.resolve_user import resolve_user_id

    uid = ctx.target_user_id
    if uid is None:
        uid, err = resolve_user_id(username=ctx.options.get("targetUsername"))
        if err:
            ctx.note(err)
            return None
    if not uid:
        ctx.note("Укажите имя или id цели")
        return None
    ctx.target_user_id = uid
    t = db.session.get(User, uid)
    if not t:
        ctx.note("Игрок не найден")
    return t


# Дебафф-предметы в инвентаре, которые сразу дают эффект (без списания заряда)
_AUTO_ACTIVATE_DEBUFF_KEYS = frozenset(
    {
        "huubik_dice",
        "rambo_band",
        "reverse_boots",
        "explosives",
        "dice_penalty_next",
    }
)


def _should_auto_activate_debuff(item: ItemDef) -> bool:
    if item.polarity != "debuff" or item.kind != "item":
        return False
    key, _ = _key_val(item.effect)
    return key in _AUTO_ACTIVATE_DEBUFF_KEYS or (
        key.endswith("_dice") and key not in ("cheat_dice",)
    )


def grant_item_to_player(
    user: User,
    item_id: int,
    quantity: int | None = None,
    *,
    is_trap: bool = False,
    auto_activate_debuff: bool = True,
) -> list[str]:
    """Выдать предмет в инвентарь; дебафф-предметы сразу активируют эффект (заряд не тратится)."""
    notes: list[str] = []
    item = get_item(item_id)
    if not item:
        return notes
    if quantity is None:
        quantity = _charges(item)
    if item.kind == "trap":
        is_trap = True
    notes.extend(inv.grant_inventory_item(user.id, item_id, quantity, is_trap=is_trap))
    if item.kind == "trap":
        notes.append(f"Ловушка «{item.name}» → инвентарь")
        return notes
    if item.kind == "item":
        notes.append(f"«{item.name}» → инвентарь ({quantity} зар.)")
        if auto_activate_debuff and _should_auto_activate_debuff(item):
            ctx = EffectContext(
                user_id=user.id,
                item=item,
                actor_username=user.username,
            )
            apply_item_effect(ctx, user, db)
            notes.extend(ctx.factors)
            notes.append(f"«{item.name}»: эффект активирован (заряд в инвентаре)")
    return notes


def apply_on_wheel_land(ctx: EffectContext, user: User, db_sess) -> None:
    item = ctx.item
    if item.instant or item.kind == "none":
        apply_item_effect(ctx, user, db_sess)
        return
    if item.kind == "trap":
        for n in grant_item_to_player(
            user, item.id, is_trap=True, auto_activate_debuff=False
        ):
            ctx.note(n)
        return
    if item.kind == "item":
        for n in grant_item_to_player(user, item.id):
            ctx.note(n)
        return
    ctx.note(f"«{item.name}» (тип {item.kind})")

