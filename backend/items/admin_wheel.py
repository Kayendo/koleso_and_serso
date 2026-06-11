"""Эффекты колеса приколов: жанр → ролл игры → заглушка для админа."""

from __future__ import annotations

from backend.board import BOARD_BY_ID, GENRE_LABELS, GENRE_SHORT_LABELS
from backend.items.effects import EffectContext
from backend.models import PlayerGame, User, db
from backend.services import game_lists
from backend.services.turn_service import cell_game_source

ADMIN_WHEEL_ITEM_IDS = frozenset({40, 41})

ADMIN_WHEEL_BANNERS: dict[int, str] = {
    40: "После ролла: чат выбирает игру из 5 вариантов",
    41: "После ролла: игрок выбирает категорию и игру",
}

def is_admin_wheel_item(item_id: int) -> bool:
    return int(item_id) in ADMIN_WHEEL_ITEM_IDS


def activate_law_buff_pending(ctx: EffectContext, user: User) -> None:
    """Закон из инвентаря: бафф → категория и ролл слева в панели хода."""
    from backend.items.modifiers import _add_mod
    from backend.pending_wheels import set_admin_wheel

    item = ctx.item
    banner = ADMIN_WHEEL_BANNERS.get(item.id, item.name)
    key = "chat_law_buff" if item.id == 40 else "i_am_law_buff"
    _add_mod(
        user.id,
        key,
        "1",
        1,
        item_id=item.id,
        label=item.name,
        desc=banner,
    )
    set_admin_wheel(
        user.id,
        {
            "itemId": item.id,
            "name": item.name,
            "banner": banner,
        },
    )
    ctx.note(f"«{item.name}»: активно — выберите категорию слева и роллите игру")
    db.session.commit()


def get_active_admin_wheel(user_id: int) -> dict | None:
    from backend.pending_wheels import get_admin_wheel

    return get_admin_wheel(user_id)


def public_admin_wheel(user_id: int) -> dict | None:
    return get_active_admin_wheel(user_id)


def consume_admin_wheel(user_id: int) -> dict | None:
    from backend.pending_wheels import pop_admin_wheel, pop_wheel_banner

    pop_wheel_banner(user_id)
    return pop_admin_wheel(user_id)


def admin_wheel_genre_payload(user: User) -> dict:
    active = get_active_admin_wheel(user.id)
    if active and active.get("genreId"):
        return {
            "username": user.username,
            "displayName": user.public_name(),
            "userId": user.id,
            "needsGenrePick": False,
            "adminWheelEffect": active,
            "user": user.to_public_dict(),
        }
    return {
        "username": user.username,
        "displayName": user.public_name(),
        "userId": user.id,
        "needsGenrePick": True,
        "adminWheelEffect": active,
        "genres": [
            {
                "id": gid,
                "label": GENRE_LABELS[gid],
                "shortLabel": GENRE_SHORT_LABELS.get(gid, GENRE_LABELS[gid]),
                "buttonLabel": GENRE_SHORT_LABELS.get(gid, GENRE_LABELS[gid]),
            }
            for gid in sorted(GENRE_LABELS)
        ],
        "user": user.to_public_dict(),
    }


def admin_wheel_open(user: User, genre_id: int) -> tuple[list[str], dict]:
    wheel = game_lists.wheel_games(int(genre_id), 12)
    src = {
        **cell_game_source(user.position),
        "genreId": int(genre_id),
        "adminWheel": True,
        "blazerdGenreLabel": GENRE_LABELS.get(int(genre_id), f"Жанр {genre_id}"),
    }
    return wheel, src


def admin_wheel_vote_labels(user_id: int) -> list[str]:
    return []


def create_admin_stub_from_wheel(
    user: User,
    rolled_title: str,
    *,
    genre_id: int | None,
    dice_label: str,
    cell_id: int,
) -> dict:
    from backend.items.inventory import log_turn

    effect = consume_admin_wheel(user.id) or {}
    from backend.items.modifiers import _consume_mod, _has_mod

    for key in ("chat_law_buff", "i_am_law_buff"):
        mod = _has_mod(user.id, key)
        if mod:
            _consume_mod(mod)
    genre_label = GENRE_LABELS.get(int(genre_id), "") if genre_id else ""
    cell = BOARD_BY_ID[cell_id]
    meta = {
        "rolledTitle": rolled_title,
        "adminEffectItemId": effect.get("itemId"),
        "adminEffectName": effect.get("name"),
        "adminEffectBanner": effect.get("banner"),
        "genreId": genre_id,
    }
    game = PlayerGame(
        user_id=user.id,
        title=rolled_title,
        cell_id=cell_id,
        cell_name=cell.name,
        genre_label=genre_label or None,
        dice_roll=dice_label,
        status="pending_admin",
        review="",
        rating=None,
    )
    db.session.add(game)
    user.turn_phase = "playing"
    db.session.commit()

    factors = [
        f"Ролл с эффектом «{effect.get('name', 'колесо')}»",
        effect.get("banner") or "",
        f"Выпало на колесе: {rolled_title}",
        "Игра назначается админом",
    ]
    factors = [f for f in factors if f]
    log_turn(
        user.id,
        summary=f"Ролл: {effect.get('name', 'эффект колеса')}",
        factors=factors,
        dice_label=dice_label,
        cell_name=cell.name,
        extra={"gameId": game.id, "adminWheel": meta},
    )
    return {
        "game": game.to_dict(),
        "adminWheelResolved": True,
        "rolledTitle": rolled_title,
        "factors": factors,
        "user": user.to_public_dict(),
    }
