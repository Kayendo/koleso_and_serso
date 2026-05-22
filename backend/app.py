from __future__ import annotations

import os
import sys

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager
from flask_socketio import SocketIO

from backend.config import BASE_DIR, UPLOAD_DIR
from backend.models import User, db
from backend.admin_routes import admin_api
from backend.routes import api
from backend.socket_events import register_socket_handlers

socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "frontend" / "dist"),
        static_url_path="",
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "kolesoblya-dev"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URI", f"sqlite:///{BASE_DIR / 'kolesoblya.db'}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
    )

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5000", "http://localhost:5000"])
    socketio.init_app(app)
    app.extensions["socketio"] = socketio
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(admin_api, url_prefix="/api/admin")
    register_socket_handlers(socketio)

    @app.route("/uploads/avatars/<path:filename>")
    def avatars(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    @app.route("/avatars/<path:filename>")
    def static_avatars(filename):
        public = BASE_DIR / "frontend" / "public" / "avatars"
        return send_from_directory(public, filename)

    with app.app_context():
        db.create_all()
        _migrate_schema()
        from backend.seed import seed_users

        seed_users()
        _ensure_default_avatar()

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path):
        dist = BASE_DIR / "frontend" / "dist"
        if path and (dist / path).is_file():
            return send_from_directory(dist, path)
        index = dist / "index.html"
        if index.exists():
            return send_from_directory(dist, "index.html")
        return (
            "<p>Соберите фронтенд: <code>cd frontend && npm install && npm run build</code></p>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    return app


def _migrate_schema():
    """Добавить новые колонки в существующую SQLite без Alembic."""
    import sqlalchemy as sa

    conn = db.engine.connect()
    cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))}
    if "is_admin" not in cols:
        conn.execute(sa.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
        conn.commit()
    cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))}
    if "is_player" not in cols:
        conn.execute(sa.text("ALTER TABLE users ADD COLUMN is_player BOOLEAN DEFAULT 1"))
        conn.commit()
    cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))}
    if "last_position" not in cols:
        conn.execute(sa.text("ALTER TABLE users ADD COLUMN last_position INTEGER"))
        conn.commit()
    cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(player_games)"))}
    if "gameplay_tags" not in cols:
        conn.execute(
            sa.text("ALTER TABLE player_games ADD COLUMN gameplay_tags TEXT DEFAULT '[]'")
        )
        conn.commit()


def _ensure_default_avatar():
    static_av = BASE_DIR / "frontend" / "public" / "avatars" / "default.png"
    if static_av.exists():
        import shutil

        dest = UPLOAD_DIR / "default.png"
        if not dest.exists():
            shutil.copy(static_av, dest)


if __name__ == "__main__":
    sys.path.insert(0, str(BASE_DIR))
    application = create_app()
    socketio.run(application, host="0.0.0.0", port=5000, debug=True)
