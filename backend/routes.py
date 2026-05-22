from __future__ import annotations

import os
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import current_user, login_required, login_user, logout_user

from backend.board import get_board_json
from backend.config import UPLOAD_DIR
from backend.models import PlayerGame, User, db
from backend.rules import RULES_HTML
from backend.services.game_lists import wheel_games
from backend.services.scoring import points_for_completion
from backend.services.turn_service import after_drop
from backend.time_utils import ensure_aware, utcnow
from backend.reward_wheels import open_reward_wheel_for_user, roll_reward_dice_for_user
from backend.turn_actions import (
    reveal_trinity_dice_for_user,
    confirm_dice_roll_for_user,
    confirm_wheel_for_user,
    durka_roll_for_user,
    open_wheel_for_user,
    roll_dice_for_user,
    spin_wheel_for_user,
)
from backend.services.hltb_service import hltb_url_for_title
from backend.tenor_service import pick_meme_gif
from backend.turn_logic import require_phase

api = Blueprint("api", __name__)


@api.route("/board")
def board():
    return jsonify(get_board_json())


@api.route("/tenor/meme")
def tenor_meme():
    gif = pick_meme_gif()
    return jsonify(gif)


@api.route("/hltb/links", methods=["POST"])
def hltb_links():
    import urllib.parse
    from concurrent.futures import ThreadPoolExecutor

    data = request.get_json() or {}
    titles = [str(t).strip() for t in (data.get("titles") or []) if str(t).strip()]
    if not titles:
        return jsonify({"links": []})
    if data.get("quick"):
        links = [
            f"https://howlongtobeat.com/?q={urllib.parse.quote(t)}" for t in titles
        ]
        return jsonify({"links": links})
    with ThreadPoolExecutor(max_workers=4) as pool:
        links = list(pool.map(hltb_url_for_title, titles))
    return jsonify({"links": links})


@api.route("/rules")
def rules():
    return jsonify({"html": RULES_HTML})


@api.route("/players")
def players():
    users = (
        User.query.filter_by(is_player=True).order_by(User.points.desc()).all()
    )
    return jsonify([u.to_public_dict() for u in users])


@api.route("/players/<int:user_id>")
def player_detail(user_id: int):
    from backend.items.inventory import get_inventory_state

    user = User.query.get_or_404(user_id)
    games = (
        PlayerGame.query.filter_by(user_id=user_id)
        .order_by(PlayerGame.id.desc())
        .all()
    )
    inv = get_inventory_state(user_id, include_history=False)
    return jsonify(
        {
            "player": user.to_public_dict(),
            "games": [g.to_dict() for g in games],
            "inventory": inv,
        }
    )


@api.route("/players/<int:user_id>/turn-history")
def player_turn_history(user_id: int):
    from backend.items.inventory import get_inventory_state

    User.query.get_or_404(user_id)
    inv = get_inventory_state(user_id, include_history=True)
    return jsonify({"turnHistory": inv.get("turnHistory", [])})


@api.route("/players/<int:user_id>/inventory")
def player_inventory(user_id: int):
    from backend.items.inventory import get_inventory_state

    User.query.get_or_404(user_id)
    return jsonify(get_inventory_state(user_id))


@api.route("/inventory/use", methods=["POST"])
@login_required
def inventory_use():
    from backend.items.use import use_inventory_item

    data = request.get_json() or {}
    item_id = data.get("itemId")
    if not item_id:
        return jsonify({"error": "itemId обязателен"}), 400
    from backend.items.resolve_user import resolve_user_id

    opts = dict(data.get("options") or {})
    for k in ("mode", "targetItemId", "genreId", "coinSide", "refuse"):
        if data.get(k) is not None:
            opts[k] = data[k]
    tid, terr = resolve_user_id(
        user_id=data.get("targetUserId"),
        username=data.get("targetUsername") or opts.get("targetUsername"),
    )
    if terr:
        return jsonify({"error": terr}), 400
    pid, perr = resolve_user_id(
        user_id=data.get("partnerUserId") or opts.get("partnerUserId"),
        username=data.get("partnerUsername") or opts.get("partnerUsername"),
    )
    if perr:
        return jsonify({"error": perr}), 400
    if data.get("partnerUserId") is not None:
        opts["partnerUserId"] = int(data["partnerUserId"])
    elif pid is not None:
        opts["partnerUserId"] = pid

    result = use_inventory_item(
        current_user,
        int(item_id),
        target_user_id=tid,
        options=opts,
    )
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/history")
def history():
    games = PlayerGame.query.order_by(PlayerGame.id.desc()).limit(200).all()
    out = []
    for g in games:
        d = g.to_dict()
        d["username"] = g.player.username if g.player else "?"
        out.append(d)
    return jsonify(out)


@api.route("/statistics")
def statistics():
    users = User.query.filter_by(is_player=True).all()
    rows = []
    for u in users:
        completed = PlayerGame.query.filter_by(
            user_id=u.id, status="completed"
        ).all()
        dropped = PlayerGame.query.filter_by(user_id=u.id, status="dropped").count()
        pts_games = sum(g.points_earned or 0 for g in completed)
        rows.append(
            {
                "username": u.username,
                "points": u.points,
                "gamesCompleted": len(completed),
                "gamesDropped": dropped,
                "pointsFromGames": pts_games,
                "laps": u.laps,
                "rerolls": u.reroll_count,
            }
        )
    rows.sort(key=lambda r: r["points"], reverse=True)
    return jsonify(rows)


@api.route("/auth/accounts")
def list_accounts():
    players = User.query.filter_by(is_player=True).order_by(User.username).all()
    return jsonify(
        {
            "players": [{"username": u.username} for u in players],
            "adminUsername": "admin",
        }
    )


@api.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(username=(data.get("username") or "").strip()).first()
    if not user or not user.check_password(data.get("password") or ""):
        return jsonify({"error": "Неверный логин или пароль"}), 401
    login_user(user)
    return jsonify({"user": user.to_public_dict()})


@api.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@api.route("/auth/me")
def me():
    if current_user.is_authenticated:
        return jsonify({"user": current_user.to_public_dict()})
    return jsonify({"user": None})


@api.route("/avatar", methods=["POST"])
@login_required
def upload_avatar():
    f = request.files.get("avatar")
    if not f:
        return jsonify({"error": "Нет файла"}), 400
    ext = os.path.splitext(f.filename or "")[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return jsonify({"error": "Недопустимый формат"}), 400
    name = f"user_{current_user.id}{ext}"
    path = UPLOAD_DIR / name
    f.save(path)
    current_user.avatar_url = f"/uploads/avatars/{name}"
    db.session.commit()
    return jsonify({"avatarUrl": current_user.avatar_url})


@api.route("/games/<int:game_id>/timer", methods=["POST"])
@login_required
def timer_toggle(game_id: int):
    game = PlayerGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    if game.status != "active":
        return jsonify({"error": "Игра не активна"}), 400
    now = utcnow()
    if game.timer_running and game.timer_started_at:
        started = ensure_aware(game.timer_started_at)
        delta = (now - started).total_seconds()
        game.play_seconds += int(delta)
        game.timer_running = False
        game.timer_started_at = None
    else:
        game.timer_running = True
        game.timer_started_at = now
    db.session.commit()
    return jsonify(game.to_dict())


@api.route("/games/<int:game_id>/review", methods=["POST"])
@login_required
def save_review(game_id: int):
    game = PlayerGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    game.review = (data.get("review") or "").strip()
    rating = data.get("rating")
    if rating is not None:
        r = int(rating)
        if 1 <= r <= 10:
            game.rating = r
    db.session.commit()
    return jsonify(game.to_dict())


@api.route("/games/<int:game_id>/complete", methods=["POST"])
@login_required
def complete_game(game_id: int):
    game = PlayerGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    err = require_phase(current_user, "playing")
    if err:
        return jsonify({"error": err}), 400
    if game.status != "active":
        return jsonify({"error": "Уже завершена"}), 400

    data = request.get_json() or {}
    if data.get("review") is not None:
        game.review = str(data.get("review") or "").strip()
    if data.get("rating") is not None:
        r = int(data["rating"])
        if 1 <= r <= 10:
            game.rating = r

    if not (game.review and game.review.strip()) or not game.rating:
        return jsonify({"error": "Нужны отзыв и оценка 1–10"}), 400

    now = utcnow()
    if game.timer_running and game.timer_started_at:
        started = ensure_aware(game.timer_started_at)
        game.play_seconds += int((now - started).total_seconds())
        game.timer_running = False
        game.timer_started_at = None

    from backend.items.modifiers import apply_completion_points

    from backend.items.gameplay import gameplay_tags_to_strings

    factors: list[str] = []
    gp = gameplay_tags_to_strings(game._parse_gameplay_tags())
    if gp:
        factors.extend([f"Прохождение: {t}" for t in gp])
    base = 0 if game.is_durka else points_for_completion(
        game.hltb_hours, game.judge_hours, game.is_question
    )
    earn = apply_completion_points(current_user, game, base, factors)
    from backend.items.gameplay import tick_buffs_after_game

    factors.extend(tick_buffs_after_game(current_user.id))
    game.points_earned = earn
    game.status = "completed"
    game.finished_at = now
    current_user.points += earn
    current_user.completed_count += 1
    if current_user.in_durka:
        current_user.in_durka = False
        current_user.position = game.cell_id
    db.session.commit()

    from backend.items.inventory import log_turn

    if earn > 0:
        factors.append(f"Начислено: +{earn} очк.")
    log_turn(
        current_user.id,
        summary=f"Завершена: {game.title}"
        + (f" (+{earn} очк.)" if earn else ""),
        factors=factors,
        cell_name=game.cell_name or "",
        extra={"gameId": game.id, "points": earn},
    )

    from backend.reward_wheels import start_reward_item_wheels

    socketio = current_app.extensions["socketio"]

    def _emit(event, payload):
        socketio.emit(event, payload, room="lobby", namespace="/")

    reward_payload = start_reward_item_wheels(current_user, emit=_emit)

    return jsonify({
        "game": game.to_dict(),
        "user": current_user.to_public_dict(),
        "factors": factors,
        **reward_payload,
    })


@api.route("/games/<int:game_id>/drop", methods=["POST"])
@login_required
def drop_game(game_id: int):
    game = PlayerGame.query.get_or_404(game_id)
    if game.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    err = require_phase(current_user, "playing")
    if err:
        return jsonify({"error": err}), 400
    from backend.items.drop import handle_drop

    data = request.get_json() or {}
    on_durka = game.is_durka or current_user.in_durka
    factors = handle_drop(
        current_user,
        game,
        on_durka_cell=on_durka,
        use_toilet=bool(data.get("useToiletPaper")),
    )
    return jsonify({"user": current_user.to_public_dict(), "factors": factors})


@api.route("/games/<int:game_id>/judge-hours", methods=["POST"])
@login_required
def judge_hours(game_id: int):
    if not current_user.is_admin:
        return jsonify({"error": "Только админ"}), 403
    game = PlayerGame.query.get_or_404(game_id)
    data = request.get_json() or {}
    hours = float(data.get("hours", 0))
    game.judge_hours = round(hours, 1)
    if game.hltb_hours is None:
        game.hltb_hours = game.judge_hours
    db.session.commit()
    return jsonify(game.to_dict())


@api.route("/wheel-preview")
def wheel_preview():
    genre_id = int(request.args.get("genreId", 1))
    return jsonify({"games": wheel_games(genre_id, 12)})


@api.route("/turn/roll-dice", methods=["POST"])
@login_required
def http_roll_dice():
    data = request.get_json() or {}
    result = roll_dice_for_user(current_user, data)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/confirm-dice", methods=["POST"])
@login_required
def http_confirm_dice():
    data = request.get_json() or {}
    result = confirm_dice_roll_for_user(current_user, data)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/reveal-trinity-dice", methods=["POST"])
@login_required
def http_reveal_trinity_dice():
    result = reveal_trinity_dice_for_user(current_user)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/roll-reward-dice", methods=["POST"])
@login_required
def http_roll_reward_dice():
    result = roll_reward_dice_for_user(current_user)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/durka-roll", methods=["POST"])
@login_required
def http_durka_roll():
    result = durka_roll_for_user(current_user)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/open-wheel", methods=["POST"])
@login_required
def http_open_wheel():
    data = request.get_json() or {}
    genre_id = data.get("genreId")
    result = open_wheel_for_user(
        current_user, int(genre_id) if genre_id else None
    )
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/spin-wheel", methods=["POST"])
@login_required
def http_spin_wheel():
    result = spin_wheel_for_user(current_user)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/confirm-wheel", methods=["POST"])
@login_required
def http_confirm_wheel():
    data = request.get_json() or {}
    result = confirm_wheel_for_user(current_user, data)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@api.route("/turn/open-reward-wheel", methods=["POST"])
@login_required
def http_open_reward_wheel():
    socketio = current_app.extensions["socketio"]

    def _emit(event, payload):
        socketio.emit(event, payload, room="lobby", namespace="/")

    result = open_reward_wheel_for_user(current_user, emit=_emit)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)
