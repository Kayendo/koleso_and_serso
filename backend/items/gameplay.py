"""Пометки прохождения: сложность, баффы и дебаффы на игру."""

from __future__ import annotations

import json

from backend.models import PlayerModifier, User, db

# Короткое имя эффекта (без срока и без повторов)
GAMEPLAY_NAMES: dict[str, str] = {
    "cheat_dice_ready": "Читерский кубик",
    "huubik_dice_ready": "Кубик хуюбика",
    "ez_glasses": "Очки EZ",
    "rambo_band": "Повязка Рэмбо",
    "trap_choker": "Чокер боли",
    "totem_moshnya": "Тотем мошны",
    "base_only_next": "УВЫ",
    "hurry": "Торопыга",
    "hour_growth": "Часовой рост",
    "no_points_next_game": "Дырявый парашют",
    "toilet_paper_ready": "Туалетка",
    "trap_shawarma": "Тухлая шаурма",
    "trap_rake": "Грабли",
    "trap_rat": "Крыса",
    "reverse_boots": "Реверсивные сапоги",
    "trinity_dice": "Бог любит троицу",
    "wheel_crown_pick": "Корона",
    "wheel_crown": "Корона",
    "help_laggard": "Помощь отстающему",
    "dice_penalty_next": "Штраф к броску",
    "dice_bonus_next": "Бонус к броску",
    "points_bonus_next": "Бонус к награде",
    "slave": "Slave",
    "time_ring_partner": "Парные кольца",
    "wheel_extra_spins": "Доп. колёса приколов",
    "shop_chat_buff": "По магазинам с чатом",
    "shop_leprechaun_buff": "По магазинам с Лепреконом",
    "chat_law_buff": "Чат здесь закон",
    "i_am_law_buff": "Я здесь закон",
    "guide_orb": "Шар всезнания",
}

# Пояснение — только суть эффекта, без срока
GAMEPLAY_HINTS: dict[str, str] = {
    "cheat_dice_ready": "Заменить один кубик на броске",
    "huubik_dice_ready": "Больший кубик превращается в 1",
    "ez_glasses": "Лёгкая сложность на игру",
    "rambo_band": "Максимальная сложность на игру",
    "trap_choker": "Только максимальная сложность",
    "totem_moshnya": "3 базовых очка + бонусы HLTB",
    "base_only_next": "Только базовые очки за игру",
    "hurry": "1 базовый + бонусы HLTB (часы вверх)",
    "hour_growth": "2 + 2 за каждые 10 ч HLTB",
    "no_points_next_game": "Следующая игра без очков",
    "toilet_paper_ready": "При дропе — возврат на прошлую клетку",
    "trap_shawarma": "−1 с кубика",
    "trap_rake": "−1 к броску",
    "trap_rat": "−3 к броску",
    "reverse_boots": "Ход назад",
    "trinity_dice": "3 кубика, выбрать 2",
    "wheel_crown_pick": "Выбор соседней игры на колесе",
    "wheel_crown": "Выбор соседней игры на колесе",
    "help_laggard": "Модификатор следующего броска",
    "dice_penalty_next": "Штраф на следующий бросок",
    "dice_bonus_next": "Бонус на следующий бросок",
    "points_bonus_next": "Бонус к награде за игру",
    "slave": "Поинты с игр цели",
    "time_ring_partner": "+1 к каждому вашему броску",
    "wheel_extra_spins": "Докрутите колесо приколов",
    "shop_chat_buff": "Rerolл колеса приколов — чат выбирает",
    "shop_leprechaun_buff": "Rerolл колеса — выберите 2 сектора",
    "chat_law_buff": "Колесо игр — чат выбирает",
    "i_am_law_buff": "Колесо игр — вы выбираете",
    "vote_banner": "Голосование",
    "guide_orb": "Гайд, видео или спидран",
}

# Подпись на карточке активной игры
GAMEPLAY_GAME_LABELS: dict[str, str] = {
    "guide_orb": "Прохождение с гайдами",
    "ez_glasses": "Лёгкая сложность",
    "rambo_band": "Макс. сложность",
    "totem_moshnya": "Тотем мошны",
    "hurry": "Торопыга",
    "hour_growth": "Часовой рост",
    "base_only_next": "Только базовые очки",
    "trap_choker": "Макс. сложность",
    "no_points_next_game": "Без очков",
}

# Обратная совместимость
GAMEPLAY_LABELS = GAMEPLAY_NAMES

# Списываются только после завершения/дропа игры, не при ходе без игры
TICK_ON_GAME_END: frozenset[str] = frozenset(
    {
        "ez_glasses",
        "rambo_band",
        "trap_choker",
        "totem_moshnya",
        "base_only_next",
        "hurry",
        "hour_growth",
        "guide_orb",
    }
)

# Снимается только при начислении очков за игру (apply_completion_points)
NEXT_GAME_POINT_DEBUFFS: frozenset[str] = frozenset({"no_points_next_game"})

# Остаётся на игроке до срабатывания; в теги игры только копируется
PERSIST_ON_PLAYER_UNTIL_USED: frozenset[str] = frozenset(
    {"no_points_next_game", "wheel_crown_pick", "wheel_crown"}
)

# Нельзя снять случайным эффектом колеса (аптечка, грязнулькин и т.д.)
PROTECTED_DEBUFF_KEYS: frozenset[str] = frozenset({"no_points_next_game"})

# Эффекты с зарядами в инвентаре: 1 использование = −1 заряд + бафф на 1 игру
CHARGE_BUFF_ACTIVATE: frozenset[str] = frozenset(
    {"ez_glasses", "rambo_band", "totem_moshnya", "reverse_boots", "trinity_dice"}
)

# Не списываются по ходам — только при срабатывании (кубик/колесо)
NO_TICK_ON_TURN: frozenset[str] = frozenset(
    {
        "wheel_crown_pick",
        "wheel_crown",
        "cheat_dice_ready",
        "huubik_dice_ready",
        "trinity_dice",
        "wheel_extra_spins",
        "shop_chat_buff",
        "shop_leprechaun_buff",
        "chat_law_buff",
        "i_am_law_buff",
        "vote_banner",
        "time_ring_partner",
    }
)


def label_for_modifier(mod: PlayerModifier) -> str:
    return display_name_for_modifier(mod)


def display_name_for_modifier(mod: PlayerModifier) -> str:
    key = mod.effect_key or ""
    if mod.label and mod.label not in (key, ""):
        return mod.label
    return GAMEPLAY_NAMES.get(key, mod.label or "Эффект")


def collect_gameplay_tags(user_id: int) -> list[dict]:
    tags: list[dict] = []
    for mod in PlayerModifier.query.filter_by(user_id=user_id).all():
        if mod.turns_remaining <= 0:
            continue
        if mod.effect_key.endswith("_wait"):
            continue
        if mod.effect_key not in GAMEPLAY_NAMES:
            continue
        tags.append(
            {
                "key": mod.effect_key,
                "label": GAMEPLAY_GAME_LABELS.get(
                    mod.effect_key, label_for_modifier(mod)
                ),
                "turnsRemaining": mod.turns_remaining,
                "polarity": mod.polarity,
            }
        )
    return tags


def gameplay_tags_to_strings(tags: list[dict]) -> list[str]:
    return [t["label"] for t in tags]


def activate_buff_for_next_game(
    user_id: int,
    effect_key: str,
    *,
    item_id: int | None = None,
    label: str = "",
    polarity: str = "buff",
    turns: int = 1,
    pending_inventory_charge: bool = False,
) -> None:
    """Один заряд использования → бафф на следующую игру."""
    from backend.items.modifiers import _add_mod

    PlayerModifier.query.filter_by(
        user_id=user_id, effect_key=effect_key
    ).delete()
    effect_val = "pending_charge" if pending_inventory_charge else str(turns)
    _add_mod(
        user_id,
        effect_key,
        effect_val,
        turns,
        item_id=item_id,
        label=label or GAMEPLAY_NAMES.get(effect_key, effect_key),
        desc=GAMEPLAY_HINTS.get(effect_key, ""),
        polarity=polarity,
    )


def tick_buffs_after_game(user_id: int) -> list[str]:
    """Снять игровые баффы после прохождения/дропа игры."""
    from backend.items import inventory as inv

    notes: list[str] = []
    for mod in list(PlayerModifier.query.filter_by(user_id=user_id).all()):
        if mod.effect_key not in TICK_ON_GAME_END:
            continue
        if mod.turns_remaining <= 0:
            continue
        mod.turns_remaining -= 1
        if mod.turns_remaining <= 0:
            label = mod.label or mod.effect_key
            item_id = mod.source_item_id
            effect_key = mod.effect_key
            polarity = mod.polarity or "buff"
            pending = mod.effect_value == "pending_charge"
            if pending and item_id and effect_key in CHARGE_BUFF_ACTIVATE:
                inv.consume_inventory_item(user_id, item_id)
            notes.append(f"Снят эффект «{label}»")
            db.session.delete(mod)
            db.session.flush()
            if (
                item_id
                and effect_key in CHARGE_BUFF_ACTIVATE
                and inv.has_item(user_id, item_id)
            ):
                activate_buff_for_next_game(
                    user_id,
                    effect_key,
                    item_id=item_id,
                    label=label,
                    polarity=polarity,
                    turns=1,
                    pending_inventory_charge=True,
                )
                notes.append(f"«{label}»: автоматически на следующую игру")
    db.session.commit()
    return notes


def collect_vote_banners(user_id: int) -> list[str]:
    """Подписи голосования на колесе (магазины с чатом и т.п.)."""
    labels: list[str] = []
    for mod in PlayerModifier.query.filter_by(user_id=user_id).all():
        if mod.effect_key != "vote_banner" or mod.turns_remaining <= 0:
            continue
        if mod.label:
            labels.append(mod.label)
    return labels


def add_vote_banner(user_id: int, *, item_id: int, label: str) -> None:
    from backend.items.modifiers import _add_mod

    _add_mod(
        user_id,
        "vote_banner",
        str(item_id),
        1,
        item_id=item_id,
        label=label,
        desc="Голосование — решите в чате",
        polarity="buff",
    )


def clear_gameplay_modifiers_for_reroll(user_id: int) -> list[str]:
    """Свиток реролла: сбросить эффекты, влияющие на прохождение игры."""
    clear_keys = TICK_ON_GAME_END | NEXT_GAME_POINT_DEBUFFS
    notes: list[str] = []
    for mod in list(PlayerModifier.query.filter_by(user_id=user_id).all()):
        if mod.effect_key not in clear_keys:
            continue
        notes.append(f"Снят эффект «{mod.label}» (реролл)")
        db.session.delete(mod)
    db.session.commit()
    return notes


def attach_gameplay_to_game(game, user: User) -> list[str]:
    """Скопировать активные игровые эффекты на карточку игры (заряды — при завершении/дропе)."""
    tags = collect_gameplay_tags(user.id)
    game.gameplay_tags = json.dumps(tags, ensure_ascii=False)
    db.session.commit()
    return gameplay_tags_to_strings(tags)


def _duration_label(mod: PlayerModifier) -> str:
    key = mod.effect_key or ""
    tr = mod.turns_remaining
    if tr <= 0:
        return ""
    if key in TICK_ON_GAME_END:
        n = max(1, tr)
        return "1 игра" if n == 1 else f"{n} игр"
    if key in NEXT_GAME_POINT_DEBUFFS:
        return "1 игра"
    if key in ("cheat_dice_ready", "huubik_dice_ready"):
        return "1 бросок"
    if key == "wheel_extra_spins":
        n = max(1, tr)
        return f"{n} колёс" if n != 1 else "1 колесо"
    if key == "time_ring_partner":
        n = max(0, tr)
        if n == 1:
            return "остался 1 бросок"
        if 2 <= n <= 4:
            return f"осталось {n} броска"
        return f"осталось {n} бросков"
    if key in ("wheel_crown_pick", "wheel_crown"):
        return "1 колесо"
    return f"{tr} ход."


def _format_display_line(name: str, duration: str) -> str:
    if duration:
        return f"{name} · {duration}"
    return name


def enrich_modifier_entry(mod: PlayerModifier) -> dict:
    from backend.items.catalog import get_item

    key = mod.effect_key or ""
    name = display_name_for_modifier(mod)
    duration = _duration_label(mod)
    hint = GAMEPLAY_HINTS.get(key, "")
    if key.endswith("_wait"):
        hint = mod.description or "Ожидает срабатывания"
    elif not hint and mod.description and mod.description not in (name, key):
        hint = mod.description
    flavor = ""
    if mod.source_item_id:
        item = get_item(mod.source_item_id)
        if item:
            flavor = item.flavor
    return {
        "id": mod.id,
        "itemId": mod.source_item_id,
        "name": name,
        "flavor": flavor,
        "description": mod.description,
        "turnsRemaining": mod.turns_remaining,
        "durationLabel": duration,
        "effectKey": mod.effect_key,
        "gameplayHint": hint,
        "displayLine": _format_display_line(name, duration),
    }
