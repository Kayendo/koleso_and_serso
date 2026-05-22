"""Пометки прохождения: сложность, баффы и дебаффы на игру."""

from __future__ import annotations

import json

from backend.models import PlayerModifier, User, db

GAMEPLAY_LABELS: dict[str, str] = {
    "cheat_dice_ready": "Читерский кубик: замена одного кубика",
    "huubik_dice_ready": "Кубик хуюбика: больший кубик → 1",
    "ez_glasses": "Очки EZ: лёгкая сложность на игру",
    "rambo_band": "Повязка Рэмбо: макс. сложность на игру",
    "trap_choker": "Чокер боли: только макс. сложность",
    "four_leaf_easy": "Клевер: лёгкая сложность на игру",
    "totem_moshnya": "Тотем мошны: 3 базовых очка за игру",
    "base_only_next": "УВЫ: только базовые очки",
    "hurry": "Торопыга: 1 базовый поинт за игру",
    "hour_growth": "Часовой рост: ×2 за 10 ч HLTB",
    "no_points_next_game": "Дырявый парашют: игра без очков",
    "trap_shawarma": "Тухлая шаурма: −1 с кубика",
    "trap_rake": "Грабли: −1 к броску",
    "trap_slime": "Липкая жижа: −1 к броску",
    "trap_rat": "Крыса: −3 к броску",
    "reverse_boots": "Реверсивные сапоги: ход назад",
    "trinity_dice": "Бог любит троицу: 3 кубика, выбор 2",
    "wheel_crown_pick": "Корона: выбор соседней игры на колесе",
    "wheel_crown": "Корона: выбор соседней игры на колесе",
    "help_laggard": "Помощь отстающему: модификатор броска",
    "lucky_loser": "Удачный неудачник: бонус за дебаффы",
    "coin_dice": "Орёл/решка: ±2 к броску",
    "dice_penalty_next": "Штраф к броску",
    "dice_bonus_next": "Бонус к броску",
    "points_bonus_next": "Бонус к награде",
    "slave": "Slave: поинты с игр цели",
    "time_ring_partner": "Парные кольца: +1 к броску",
    "wheel_extra_spins": "Доп. прокруты колеса приколов",
}

# Списываются только после завершения/дропа игры, не при ходе без игры
TICK_ON_GAME_END: frozenset[str] = frozenset(
    {
        "ez_glasses",
        "rambo_band",
        "trap_choker",
        "four_leaf_easy",
        "totem_moshnya",
        "base_only_next",
        "hurry",
        "hour_growth",
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
    }
)


def label_for_modifier(mod: PlayerModifier) -> str:
    if mod.effect_key in GAMEPLAY_LABELS:
        return GAMEPLAY_LABELS[mod.effect_key]
    if mod.label and mod.label != mod.effect_key:
        return mod.label
    return "Активный эффект"


def collect_gameplay_tags(user_id: int) -> list[dict]:
    tags: list[dict] = []
    for mod in PlayerModifier.query.filter_by(user_id=user_id).all():
        if mod.turns_remaining <= 0:
            continue
        if mod.effect_key.endswith("_wait"):
            continue
        if mod.effect_key not in GAMEPLAY_LABELS:
            continue
        tags.append(
            {
                "key": mod.effect_key,
                "label": label_for_modifier(mod),
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
) -> None:
    """Один заряд использования → бафф на следующую игру."""
    from backend.items.modifiers import _add_mod

    PlayerModifier.query.filter_by(
        user_id=user_id, effect_key=effect_key
    ).delete()
    _add_mod(
        user_id,
        effect_key,
        str(turns),
        turns,
        item_id=item_id,
        label=label or GAMEPLAY_LABELS.get(effect_key, effect_key),
        desc=GAMEPLAY_LABELS.get(effect_key, ""),
        polarity=polarity,
    )


def tick_buffs_after_game(user_id: int) -> list[str]:
    """Снять игровые баффы после прохождения/дропа игры."""
    notes: list[str] = []
    for mod in list(PlayerModifier.query.filter_by(user_id=user_id).all()):
        if mod.effect_key not in TICK_ON_GAME_END:
            continue
        if mod.turns_remaining <= 0:
            continue
        mod.turns_remaining -= 1
        if mod.turns_remaining <= 0:
            notes.append(f"Снят эффект «{mod.label}»")
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
        return "∞"
    if key in TICK_ON_GAME_END:
        n = max(1, tr)
        return "1 игра" if n == 1 else f"{n} игр"
    if key in ("cheat_dice_ready", "huubik_dice_ready"):
        return "1 бросок кубика"
    if key == "time_ring_partner":
        return f"{tr} ход." if tr < 99 else "пока есть заряд колец"
    return f"{tr} ход."


def enrich_modifier_entry(mod: PlayerModifier) -> dict:
    key = mod.effect_key or ""
    hint = GAMEPLAY_LABELS.get(key, "")
    if key.endswith("_wait"):
        hint = f"Ожидает активации · {mod.description or ''}"
    elif key in TICK_ON_GAME_END:
        hint = f"{hint} · действует на следующую игру"
    elif key in ("cheat_dice_ready", "huubik_dice_ready"):
        hint = f"{hint} · на следующий бросок кубика"
    elif key == "wheel_crown_pick":
        hint = f"{hint} · после вращения колеса игр"
    elif key == "time_ring_partner":
        hint = f"{hint} · +1 к броску"
    elif hint:
        hint = f"{hint}"
        if mod.turns_remaining > 0 and mod.turns_remaining < 99:
            hint += f" ({mod.turns_remaining} ход.)"
    return {
        "id": mod.id,
        "itemId": mod.source_item_id,
        "name": label_for_modifier(mod),
        "description": mod.description,
        "turnsRemaining": mod.turns_remaining,
        "durationLabel": _duration_label(mod),
        "effectKey": mod.effect_key,
        "gameplayHint": hint or mod.description,
    }
