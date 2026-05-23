"""Снимок партии для выбора игрока и подстановки в фразу."""

from __future__ import annotations

import random
from typing import Any

from backend.board import BOARD_BY_ID
from backend.items.inventory import get_inventory_state
from backend.models import PlayerGame, User, db


def _play_time(game: PlayerGame) -> str:
    sec = game.play_seconds or 0
    if game.timer_running and game.timer_started_at:
        from backend.time_utils import ensure_aware, utcnow

        sec += int((utcnow() - ensure_aware(game.timer_started_at)).total_seconds())
    if sec < 60:
        return f"{sec} с"
    h, rem = divmod(sec, 3600)
    m = rem // 60
    return f"{h} ч {m} мин" if h else f"{m} мин"


def _active_game(user_id: int) -> dict | None:
    game = (
        PlayerGame.query.filter_by(user_id=user_id, status="active")
        .order_by(PlayerGame.id.desc())
        .first()
    )
    if not game:
        return None
    return {
        "title": game.title,
        "hltbHours": game.hltb_hours,
        "playTime": _play_time(game),
    }


def _player_row(user: User) -> dict[str, Any]:
    inv = get_inventory_state(user.id)
    cell = BOARD_BY_ID.get(user.position)
    return {
        "username": user.username,
        "userId": user.id,
        "points": user.points,
        "position": user.position,
        "cellName": cell.name if cell else None,
        "laps": user.laps,
        "inDurka": user.in_durka,
        "turnPhase": user.turn_phase,
        "activeGame": _active_game(user.id),
        "inventoryItems": [
            f"{i['name']}×{i['quantity']}"
            for i in inv.get("items", [])
            if i.get("quantity", 0) > 0
        ][:8],
        "buffs": [
            b.get("label") or b.get("effectKey") for b in inv.get("buffs", [])
        ][:6],
        "debuffs": [
            d.get("label") or d.get("effectKey") for d in inv.get("debuffs", [])
        ][:6],
    }


def build_tick_context() -> dict | None:
    users = User.query.filter_by(is_player=True).order_by(User.username).all()
    if not users:
        return None
    players = [_player_row(u) for u in users]
    weights = []
    for p in players:
        w = 1
        if p.get("activeGame"):
            w += 4
        if p.get("turnPhase") not in ("idle",):
            w += 2
        if int(p.get("points") or 0) <= 3:
            w += 2
        weights.append(w)
    focus = random.choices(players, weights=weights, k=1)[0]
    return {
        "focusPlayer": focus["username"],
        "focusUserId": focus["userId"],
        "players": players,
    }


def focus_player(context: dict, username: str) -> dict:
    players = context.get("players") or []
    uid = context.get("focusUserId")
    if uid is not None:
        hit = next((x for x in players if x.get("userId") == uid), None)
        if hit:
            return hit
    return next(
        (x for x in players if x.get("username") == username),
        players[0] if players else {},
    )
