from __future__ import annotations

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


from backend.time_utils import ensure_aware, utcnow  # noqa: F401 — re-export


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(64), default="")
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_url = db.Column(db.String(512), default="")
    is_judge = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_player = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    completed_count = db.Column(db.Integer, default=0)
    dropped_count = db.Column(db.Integer, default=0)
    reroll_count = db.Column(db.Integer, default=0)
    laps = db.Column(db.Integer, default=0)
    in_durka = db.Column(db.Boolean, default=False)
    no_start_bonus_lap = db.Column(db.Boolean, default=False)
    turn_phase = db.Column(db.String(32), default="idle")
    last_position = db.Column(db.Integer, nullable=True)
    pending_reward_spins = db.Column(db.Integer, default=0)
    reward_dice_ready = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    games = db.relationship("PlayerGame", back_populates="player", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def public_name(self) -> str:
        dn = (self.display_name or "").strip()
        return dn or self.username

    def to_public_dict(self) -> dict:
        from backend.items.admin_wheel import public_admin_wheel

        d = {
            "id": self.id,
            "username": self.username,
            "displayName": self.public_name(),
            "avatarUrl": self.avatar_url or "/avatars/default.svg",
            "points": self.points,
            "position": self.position,
            "completedCount": self.completed_count,
            "droppedCount": self.dropped_count,
            "rerollCount": self.reroll_count,
            "laps": self.laps,
            "inDurka": self.in_durka,
            "turnPhase": self.turn_phase,
            "rewardSpinsPending": int(self.pending_reward_spins or 0),
            "rewardDiceReady": bool(self.reward_dice_ready),
            "isJudge": self.is_judge,
            "isAdmin": self.is_admin,
            "isPlayer": self.is_player,
        }
        aw = public_admin_wheel(self.id)
        if aw:
            d["adminWheelEffect"] = aw
        from backend.items.admin_item_grant import public_admin_item_grant

        ag = public_admin_item_grant(self.id)
        if ag:
            d["adminItemGrantPending"] = ag
        from backend.items.wheel_extras import extra_wheel_spins_left

        d["extraWheelSpinsRemaining"] = extra_wheel_spins_left(self.id)
        from backend.services.game_history import public_ongoing_game

        og = public_ongoing_game(self.id)
        if og:
            d["ongoingGame"] = og
        return d


class PlayerGame(db.Model):
    __tablename__ = "player_games"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    cell_id = db.Column(db.Integer, nullable=False)
    cell_name = db.Column(db.String(128))
    genre_label = db.Column(db.String(256))
    dice_roll = db.Column(db.String(16))
    status = db.Column(db.String(32), default="active")
    is_durka = db.Column(db.Boolean, default=False)
    is_question = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, nullable=True)
    hltb_hours = db.Column(db.Float, nullable=True)
    judge_hours = db.Column(db.Float, nullable=True)
    play_seconds = db.Column(db.Integer, default=0)
    timer_running = db.Column(db.Boolean, default=False)
    timer_started_at = db.Column(db.DateTime, nullable=True)
    review = db.Column(db.Text, default="")
    rating = db.Column(db.Integer, nullable=True)
    lottery_url = db.Column(db.String(512), default="")
    gameplay_tags = db.Column(db.Text, default="[]")
    created_at = db.Column(db.DateTime, default=utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    player = db.relationship("User", back_populates="games")

    def _parse_gameplay_tags(self) -> list:
        import json

        try:
            raw = json.loads(self.gameplay_tags or "[]")
            if isinstance(raw, list):
                return raw
        except json.JSONDecodeError:
            pass
        return []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "title": self.title,
            "cellId": self.cell_id,
            "cellName": self.cell_name,
            "genreLabel": self.genre_label,
            "diceRoll": self.dice_roll,
            "status": self.status,
            "isDurka": self.is_durka,
            "isQuestion": self.is_question,
            "pointsEarned": self.points_earned,
            "hltbHours": self.hltb_hours,
            "judgeHours": self.judge_hours,
            "playSeconds": self.play_seconds,
            "timerRunning": self.timer_running,
            "timerStartedAt": (
                ensure_aware(self.timer_started_at).isoformat()
                if self.timer_started_at
                else None
            ),
            "review": self.review,
            "rating": self.rating,
            "lotteryUrl": self.lottery_url,
            "gameplayTags": self._parse_gameplay_tags(),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
        }


class PlayerInventoryItem(db.Model):
    __tablename__ = "player_inventory"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    item_def_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    charges_remaining = db.Column(db.Integer, nullable=True)
    is_trap = db.Column(db.Boolean, default=False)


class PlayerModifier(db.Model):
    """Активные баффы и дебаффы на игроке."""

    __tablename__ = "player_modifiers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    source_item_id = db.Column(db.Integer, nullable=True)
    polarity = db.Column(db.String(16), default="buff")
    label = db.Column(db.String(128), default="")
    description = db.Column(db.Text, default="")
    effect_key = db.Column(db.String(64), default="")
    effect_value = db.Column(db.String(64), default="")
    turns_remaining = db.Column(db.Integer, default=0)


class TurnLog(db.Model):
    """История ходов с факторами (предметы, кубик, клетка)."""

    __tablename__ = "turn_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    summary = db.Column(db.String(256), default="")
    factors_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self) -> dict:
        import json

        try:
            payload = json.loads(self.factors_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        factors = payload.get("factors") if isinstance(payload.get("factors"), list) else []
        points = payload.get("points")
        if points is None:
            for f in factors:
                if isinstance(f, str) and f.startswith("Начислено:"):
                    try:
                        points = int(f.split("+")[1].split()[0])
                    except (IndexError, ValueError):
                        pass
                    break
        return {
            "id": self.id,
            "summary": self.summary,
            "factors": factors,
            "dice": payload.get("dice", ""),
            "cell": payload.get("cell", ""),
            "points": points,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class BoardMark(db.Model):
    """Следы на поле (жижа и т.п.)."""

    __tablename__ = "board_marks"

    id = db.Column(db.Integer, primary_key=True)
    cell_id = db.Column(db.Integer, nullable=False, index=True)
    effect_key = db.Column(db.String(32), nullable=False)
    owner_user_id = db.Column(db.Integer, nullable=True)
    value = db.Column(db.String(32), default="")


class GlobalState(db.Model):
    __tablename__ = "global_state"

    id = db.Column(db.Integer, primary_key=True, default=1)
    event_status = db.Column(db.String(64), default="active")
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
