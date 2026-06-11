from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from backend.board import BOARD, BOARD_BY_ID, get_board_json
from backend.items.catalog import all_items
from backend.items.effects import grant_item_to_player
from backend.items.inventory import add_user_modifier, remove_all
from backend.models import PlayerGame, PlayerModifier, User, db
from backend.time_utils import utcnow

admin_api = Blueprint("admin_api", __name__)


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({"error": "Только админ"}), 403
        return fn(*args, **kwargs)

    return wrapper


def _emit_board() -> None:
    socketio = current_app.extensions.get("socketio")
    if not socketio:
        return
    users = User.query.filter_by(is_player=True).all()
    socketio.emit(
        "board_state",
        {"players": [u.to_public_dict() for u in users], "boardSize": len(BOARD)},
        room="lobby",
        namespace="/",
    )


@admin_api.route("/players")
@admin_required
def admin_players():
    users = User.query.filter_by(is_player=True).order_by(User.username).all()
    return jsonify([u.to_public_dict() for u in users])


@admin_api.route("/items")
@admin_required
def admin_items():
    return jsonify([i.to_dict() for i in all_items()])


@admin_api.route("/board")
@admin_required
def admin_board():
    return jsonify(get_board_json())


@admin_api.route("/users/<int:user_id>", methods=["PATCH"])
@admin_required
def admin_patch_user(user_id: int):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    for key in (
        "position",
        "completed_count",
        "dropped_count",
        "reroll_count",
        "laps",
        "in_durka",
        "turn_phase",
    ):
        if key in data:
            setattr(user, key, data[key])
    if "username" in data and data["username"]:
        user.username = str(data["username"]).strip()
    if "turnPhase" in data:
        user.turn_phase = str(data["turnPhase"])
    if "inDurka" in data:
        user.in_durka = bool(data["inDurka"])
    for camel, snake in (
        ("completedCount", "completed_count"),
        ("droppedCount", "dropped_count"),
        ("rerollCount", "reroll_count"),
    ):
        if camel in data:
            setattr(user, snake, int(data[camel]))

    factors: list[str] = []
    if "points" in data:
        from backend.items.inventory import log_turn
        from backend.items.points import grant_points

        old_pts = int(user.points)
        new_pts = int(data["points"])
        delta = new_pts - old_pts
        if delta > 0:
            gained = grant_points(user, delta, factors)
            factors.insert(
                0,
                f"Админ {current_user.username}: +{delta} запрошено, игроку +{gained}",
            )
        elif delta < 0:
            user.points = max(0, new_pts)
            factors.append(
                f"Админ {current_user.username}: очки {old_pts} → {user.points}"
            )
        log_turn(
            user.id,
            summary=f"Админ: очки {old_pts} → {user.points}",
            factors=factors,
            extra={
                "admin": True,
                "adminUser": current_user.username,
                "pointsBefore": old_pts,
                "pointsAfter": user.points,
                "delta": delta,
            },
        )

    db.session.commit()
    _emit_board()
    return jsonify(user.to_public_dict())


@admin_api.route("/users/<int:user_id>/move", methods=["POST"])
@admin_required
def admin_move_user(user_id: int):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    pos = data.get("position")
    if pos is None and data.get("cellId") is not None:
        pos = data["cellId"]
    if pos is None:
        return jsonify({"error": "Укажите position или cellId"}), 400
    pos = int(pos)
    if pos not in BOARD_BY_ID:
        return jsonify({"error": "Нет такой клетки"}), 400
    user.position = pos
    user.last_position = pos
    db.session.commit()
    from backend.items.inventory import log_turn

    log_turn(
        user.id,
        summary=f"Админ: перемещение на {BOARD_BY_ID[pos].name}",
        factors=[f"Админ {current_user.username}: клетка {pos}"],
        cell_name=BOARD_BY_ID[pos].name,
        extra={"admin": True, "position": pos},
    )
    _emit_board()
    cell = BOARD_BY_ID[pos]
    return jsonify(
        {
            "user": user.to_public_dict(),
            "cell": {"id": cell.id, "name": cell.name, "type": cell.cell_type},
        }
    )


@admin_api.route("/users/<int:user_id>/grant-item", methods=["POST"])
@admin_required
def admin_grant_item(user_id: int):
    from backend.items.catalog import get_item

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    item_id = data.get("itemId")
    if not item_id:
        return jsonify({"error": "itemId обязателен"}), 400
    item = get_item(int(item_id))
    if not item:
        return jsonify({"error": "Неизвестный предмет"}), 400
    qty = int(data.get("quantity") or 1)
    notes = grant_item_to_player(
        user,
        item.id,
        qty,
        is_trap=item.kind == "trap",
        auto_activate_debuff=bool(data.get("autoActivate", True)),
        source="админ",
    )
    return jsonify(
        {
            "ok": True,
            "notes": notes,
            "inventory": __import__(
                "backend.items.inventory", fromlist=["get_inventory_state"]
            ).get_inventory_state(user.id),
        }
    )


@admin_api.route("/users/<int:user_id>/remove-item", methods=["POST"])
@admin_required
def admin_remove_item(user_id: int):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    item_id = data.get("itemId")
    if not item_id:
        return jsonify({"error": "itemId обязателен"}), 400
    remove_all(user.id, int(item_id))
    from backend.items.inventory import get_inventory_state

    return jsonify({"ok": True, "inventory": get_inventory_state(user.id)})


@admin_api.route("/users/<int:user_id>/apply-status", methods=["POST"])
@admin_required
def admin_apply_status(user_id: int):
    """Навесить бафф/дебафф: из каталога (itemId) или вручную."""
    from backend.items.catalog import get_item

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if data.get("itemId"):
        item = get_item(int(data["itemId"]))
        if not item:
            return jsonify({"error": "Неизвестный предмет"}), 400
        if False:
            pass
        else:
            from backend.items.gameplay import CHARGE_BUFF_ACTIVATE, TICK_ON_GAME_END

            key, val = (item.effect.split(":", 1) + [""])[:2]
            mod_key_map = {
                "wheel_crown": "wheel_crown_pick",
                "cheat_dice": "cheat_dice_ready",
                "huubik_dice": "huubik_dice_ready",
            }
            key = mod_key_map.get(key, key)
            if data.get("turns") is not None:
                turns = int(data["turns"])
            elif key in TICK_ON_GAME_END or key in CHARGE_BUFF_ACTIVATE:
                turns = 1
            elif item.duration_turns > 0:
                turns = item.duration_turns
            else:
                turns = 1
            add_user_modifier(
                user.id,
                key or f"item_{item.id}",
                val,
                turns,
                source_item_id=item.id,
                label=item.name,
                description=item.description,
                polarity=item.polarity,
            )
    else:
        polarity = str(data.get("polarity") or "buff")
        label = str(data.get("label") or "Админ-эффект")
        key = str(data.get("effectKey") or "admin_custom")
        val = str(data.get("effectValue") or "")
        turns = int(data.get("turns") or 1)
        add_user_modifier(
            user.id,
            key,
            val,
            turns,
            label=label,
            description=str(data.get("description") or ""),
            polarity=polarity,
        )

    from backend.items.inventory import get_inventory_state

    return jsonify({"ok": True, "inventory": get_inventory_state(user.id)})


@admin_api.route("/users/<int:user_id>/clear-status", methods=["POST"])
@admin_required
def admin_clear_status(user_id: int):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    mod_id = data.get("modifierId")
    if mod_id:
        mod = PlayerModifier.query.filter_by(
            id=int(mod_id), user_id=user.id
        ).first_or_404()
        db.session.delete(mod)
    else:
        polarity = data.get("polarity")
        q = PlayerModifier.query.filter_by(user_id=user.id)
        if polarity in ("buff", "debuff"):
            q = q.filter_by(polarity=polarity)
        for m in q.all():
            db.session.delete(m)
    db.session.commit()
    from backend.items.inventory import get_inventory_state

    return jsonify({"ok": True, "inventory": get_inventory_state(user.id)})


@admin_api.route("/games/<int:game_id>", methods=["PATCH"])
@admin_required
def admin_patch_game(game_id: int):
    game = PlayerGame.query.get_or_404(game_id)
    data = request.get_json() or {}
    fields = {
        "title": str,
        "cell_id": int,
        "cell_name": str,
        "genre_label": str,
        "dice_roll": str,
        "status": str,
        "review": str,
        "rating": int,
        "points_earned": int,
        "hltb_hours": float,
        "judge_hours": float,
        "play_seconds": int,
        "is_durka": bool,
        "is_question": bool,
        "timer_running": bool,
        "lottery_url": str,
    }
    for key, typ in fields.items():
        if key in data:
            val = data[key]
            if val is None and key in ("rating", "points_earned", "hltb_hours", "judge_hours"):
                setattr(game, key, None)
            else:
                setattr(game, key, typ(val) if typ is not bool else bool(val))
    if data.get("status") in ("completed", "dropped") and not game.finished_at:
        game.finished_at = utcnow()
    user = game.player
    if data.get("status") == "active" and user:
        from backend.items.gameplay import attach_gameplay_to_game
        from backend.services.game_history import ensure_turn_phase_matches_ongoing_game
        from backend.services.turn_service import _schedule_hltb_lookup

        if not game._parse_gameplay_tags():
            attach_gameplay_to_game(game, user)
        if game.hltb_hours is None and game.title:
            _schedule_hltb_lookup(game.id, game.title)
        ensure_turn_phase_matches_ongoing_game(user)
    db.session.commit()
    payload = game.to_dict()
    if user:
        payload["user"] = user.to_public_dict()
    return jsonify(payload)


@admin_api.route("/reload-data", methods=["POST"])
@admin_required
def admin_reload_data():
    from backend.data_reload import reload_all_data

    return jsonify(reload_all_data())
