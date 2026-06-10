"""Модификаторы кубика, очков и хода."""

from __future__ import annotations

import math

from backend.board import START_CELL_ID
from backend.items import inventory as inv
from backend.items.catalog import get_item
from backend.models import BoardMark, PlayerGame, PlayerInventoryItem, PlayerModifier, User, db
from backend.random_utils import randint


def _mods(user_id: int) -> list[PlayerModifier]:
    return PlayerModifier.query.filter_by(user_id=user_id).all()


def _has_mod(user_id: int, key: str) -> PlayerModifier | None:
    for m in _mods(user_id):
        if m.effect_key == key and m.turns_remaining != 0:
            return m
    return None


def _add_mod(
    user_id: int,
    key: str,
    value: str,
    turns: int,
    *,
    item_id: int | None = None,
    label: str = "",
    desc: str = "",
    polarity: str = "buff",
) -> None:
    from backend.items.inventory import add_user_modifier

    add_user_modifier(
        user_id,
        key,
        value,
        turns,
        source_item_id=item_id,
        label=label,
        description=desc,
        polarity=polarity,
    )


def _consume_mod(mod: PlayerModifier) -> None:
    if mod.turns_remaining > 0:
        mod.turns_remaining -= 1
    if mod.turns_remaining <= 0:
        db.session.delete(mod)
    db.session.commit()


def count_inventory_debuffs(user_id: int) -> int:
    from backend.items.inventory import _ensure_charges

    n = 0
    for row in PlayerInventoryItem.query.filter_by(user_id=user_id).all():
        defn = get_item(row.item_def_id)
        _ensure_charges(row)
        if defn and defn.polarity == "debuff" and row.charges_remaining > 0:
            n += row.quantity
    return n


def dice_choice_needed(
    user: User,
    d1: int,
    d2: int,
    options: dict | None = None,
) -> dict | None:
    """Выбор двух из трёх кубиков (троица) — до движения."""
    options = options or {}
    tri = _has_mod(user.id, "trinity_dice")
    if tri and not options.get("trinityPick"):
        return {"type": "trinity"}
    return None


def cheat_replacement_pending(user: User, options: dict | None = None) -> bool:
    """Читерский кубик: после броска можно заменить один кубик."""
    options = options or {}
    if not _has_mod(user.id, "cheat_dice_ready"):
        return False
    return not (
        options.get("cheatDie") in (1, 2) and options.get("cheatValue")
    )


def apply_dice_roll(
    user: User,
    d1: int,
    d2: int,
    *,
    use_cheat: dict | None = None,
) -> tuple[int, int, int, str, dict, list[str]]:
    factors: list[str] = []
    raw_d1, raw_d2 = d1, d2
    meta: dict = {
        "backward": False,
        "one_die": False,
        "rawDice": [raw_d1, raw_d2],
    }
    use_cheat = use_cheat or {}

    rev = _has_mod(user.id, "reverse_boots")
    if rev:
        die = randint(1, 6)
        _consume_mod(rev)
        if rev.effect_value == "pending_charge" and rev.source_item_id:
            from backend.items.inventory import consume_inventory_item

            consume_inventory_item(user.id, rev.source_item_id)
        factors.append(f"«Реверсивные сапоги»: 1 кубик={die}, назад")
        return die, 0, die, str(die), {"backward": True, "one_die": True, "rawDice": [die, 0]}, factors

    tri = _has_mod(user.id, "trinity_dice")
    if tri:
        pick = use_cheat.get("trinityPick")
        d3 = use_cheat.get("trinityThird")
        if pick and len(pick) == 2:
            d1, d2 = int(pick[0]), int(pick[1])
            _consume_mod(tri)
            third = f", третий {d3}" if d3 is not None else ""
            factors.append(f"«Бог любит троицу»: выбраны {d1}+{d2}{third}")

    cheat_ready = _has_mod(user.id, "cheat_dice_ready")
    if cheat_ready and use_cheat.get("cheatDie") in (1, 2) and use_cheat.get("cheatValue"):
        idx = int(use_cheat["cheatDie"]) - 1
        val = max(1, min(6, int(use_cheat["cheatValue"])))
        if idx == 0:
            d1 = val
        else:
            d2 = val
        _consume_mod(cheat_ready)
        factors.append(f"«Читерский кубик»: кубик {idx + 1} → {val}")

    steps = d1 + d2
    label = f"{d1}+{d2}"

    sh = _has_mod(user.id, "trap_shawarma")
    if sh:
        d1, d2 = max(1, d1 - 1), max(1, d2 - 1)
        steps = d1 + d2
        label = f"{d1}+{d2}"
        _consume_mod(sh)
        factors.append("«Тухлая шаурма»: −1 с каждого кубика")

    hu_ready = _has_mod(user.id, "huubik_dice_ready")
    if hu_ready and not tri:
        if d1 >= d2:
            d1 = 1
        else:
            d2 = 1
        _consume_mod(hu_ready)
        steps = d1 + d2
        label = f"{d1}+{d2}"
        factors.append("«Кубик хуюбика»: больший → 1")
        from backend.items.inventory import consume_inventory_item

        consume_inventory_item(user.id, 2)

    for key, delta, lbl in (
        ("trap_rake", -1, "Грабли"),
        ("trap_rat", -3, "Крыса"),
        ("dice_penalty_next", -1, "Штраф к броску"),
        ("help_laggard", None, "Помощь отстающему"),
        ("dice_bonus_next", None, "Бонус к броску"),
    ):
        m = _has_mod(user.id, key)
        if not m:
            continue
        if key == "help_laggard":
            d = int(m.effect_value or "0")
        elif key == "dice_bonus_next":
            d = abs(int(m.effect_value or "1"))
        else:
            d = delta if delta is not None else int(m.effect_value or "0")
        steps = max(2, steps + d)
        _consume_mod(m)
        factors.append(f"«{lbl}»: {d:+d} к ходу")
        label = f"{d1}+{d2}→{steps}"

    mark = BoardMark.query.filter_by(
        cell_id=user.position, effect_key="slime_trail"
    ).first()
    if mark:
        steps = max(2, steps - 2)
        db.session.delete(mark)
        factors.append("След жижи: −2 к броску")

    ring = _has_mod(user.id, "time_ring_partner")
    if ring:
        steps += 1
        label = f"{d1}+{d2}→{steps}"
        factors.append("«Парные кольца времени»: +1 к ходу")
        ring.turns_remaining -= 1
        if ring.turns_remaining <= 0:
            db.session.delete(ring)
            factors.append("«Парные кольца времени»: связь закончилась")
        db.session.commit()

    db.session.commit()
    return d1, d2, steps, label, meta, factors


def build_move_path(
    start: int, steps: int, *, backward: bool
) -> tuple[list[int], int, bool]:
    from backend.board import BOARD_SIZE

    passed_start = False
    path: list[int] = []
    pos = start
    if backward:
        for _ in range(steps):
            pos = (pos - 1) % BOARD_SIZE
            path.append(pos)
        return path, pos, False

    for _ in range(steps):
        nxt = (pos + 1) % BOARD_SIZE
        if nxt == START_CELL_ID and pos != START_CELL_ID:
            passed_start = True
        pos = nxt
        path.append(pos)
    return path, pos, passed_start


def _game_has_tag(game: PlayerGame, key: str) -> bool:
    try:
        tags = game._parse_gameplay_tags()
    except Exception:
        return False
    return any(t.get("key") == key for t in tags)


def apply_completion_points(
    user: User,
    game: PlayerGame,
    base: int,
    factors: list[str] | None = None,
) -> int:
    from backend.services.scoring import points_for_completion, points_for_hurry, points_for_totem

    factors = factors or []
    pts = base
    base_only = _has_mod(user.id, "base_only_next") or _game_has_tag(
        game, "base_only_next"
    )

    if base_only:
        pts = points_for_completion(None, None, bool(game.is_question))
        factors.append("«УВЫ»: только базовые очки (без HLTB)")
    elif _has_mod(user.id, "totem_moshnya") or _game_has_tag(game, "totem_moshnya"):
        from backend.services.scoring import _hours_ceiled

        pts = points_for_totem(
            game.hltb_hours,
            game.judge_hours,
            bool(game.is_question),
        )
        h = _hours_ceiled(game.hltb_hours, game.judge_hours)
        if h is None:
            factors.append("«Тотем мошны»: 3 очка")
        else:
            bonus = pts - 3
            factors.append(f"«Тотем мошны»: 3 + {bonus} за HLTB")
    elif _has_mod(user.id, "hurry") or _game_has_tag(game, "hurry"):
        pts = points_for_hurry(
            game.hltb_hours,
            game.judge_hours,
            bool(game.is_question),
        )
        factors.append("«Торопыга»")
    elif _has_mod(user.id, "hour_growth") or _game_has_tag(game, "hour_growth"):
        from backend.services.scoring import _hours_ceiled

        h = _hours_ceiled(game.hltb_hours, game.judge_hours)
        if h is not None:
            blocks = math.ceil(h / 10)
            pts = 2 + 2 * blocks
        else:
            pts = 2
        factors.append(f"«Часовой рост»: {pts} очк.")

    m = _has_mod(user.id, "no_points_next_game")
    if m or _game_has_tag(game, "no_points_next_game"):
        pts = 0
        if m:
            _consume_mod(m)
        factors.append("«Дырявый парашют»: без очков за эту игру")

    bonus = _has_mod(user.id, "points_bonus_next")
    if bonus:
        pts += int(bonus.effect_value or "0")
        _consume_mod(bonus)
        factors.append(f"Бонус к награде: +{bonus.effect_value}")

    if pts > 0:
        from backend.items.points import grant_points

        pts = grant_points(user, pts, factors)

    db.session.commit()
    return max(0, pts)


def tick_turn_modifiers(user_id: int) -> list[str]:
    """Только эффекты движения/кубика. Игровые баффы — после игры (tick_buffs_after_game)."""
    from backend.items.inventory import tick_modifiers_after_turn

    return tick_modifiers_after_turn(user_id)


def place_slime_trail(user_id: int, cell_id: int) -> None:
    BoardMark.query.filter_by(cell_id=cell_id, effect_key="slime_trail").delete()
    db.session.add(
        BoardMark(
            cell_id=cell_id,
            effect_key="slime_trail",
            owner_user_id=user_id,
            value="-2",
        )
    )
    db.session.commit()
