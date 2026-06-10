from __future__ import annotations

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room

from backend.models import User, db
from backend.turn_actions import (
    confirm_wheel_for_user,
    durka_roll_for_user,
    durka_step_for_user,
    open_wheel_for_user,
    roll_dice_for_user,
    spin_wheel_for_user,
)
def register_socket_handlers(socketio):
    @socketio.on("connect")
    def on_connect():
        join_room("lobby")
        emit("board_state", _full_state())

    @socketio.on("join")
    def on_join():
        join_room("lobby")

    @socketio.on("request_state")
    def on_request_state():
        emit("board_state", _full_state())

    @socketio.on("durka_roll_game")
    def durka_roll_game():
        if not current_user.is_authenticated:
            return emit("error", {"message": "Войдите в аккаунт"})
        user = db.session.get(User, current_user.id)
        result = durka_roll_for_user(user)
        if isinstance(result, tuple):
            emit("error", result[0])

    @socketio.on("durka_step")
    def durka_step(data):
        if not current_user.is_authenticated:
            return emit("error", {"message": "Войдите в аккаунт"})
        user = db.session.get(User, current_user.id)
        data = data or {}
        result = durka_step_for_user(user, data.get("direction"))
        if isinstance(result, tuple):
            emit("error", result[0])

    @socketio.on("turn_roll_dice")
    def turn_roll_dice():
        if not current_user.is_authenticated:
            return emit("error", {"message": "Войдите в аккаунт"})
        user = db.session.get(User, current_user.id)
        data = request.get_json(silent=True) or {}
        result = roll_dice_for_user(user, data)
        if isinstance(result, tuple):
            emit("error", result[0])

    @socketio.on("turn_confirm_wheel")
    def turn_confirm_wheel(data):
        if not current_user.is_authenticated:
            return emit("error", {"message": "Войдите в аккаунт"})
        user = db.session.get(User, current_user.id)
        result = confirm_wheel_for_user(user, data)
        if isinstance(result, tuple):
            emit("error", result[0])


def _full_state() -> dict:
    users = User.query.filter_by(is_player=True).all()
    return {
        "players": [u.to_public_dict() for u in users],
        "boardSize": 40,
    }
