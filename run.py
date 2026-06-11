"""Запуск сервера: python run.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.app import create_app, socketio
from backend.comment_scheduler import is_serving_process as is_comment_serving, start as start_commentator
from backend.tenor_refresher import is_serving_process as is_gif_serving, start as start_gif_refresher

app = create_app()

DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

if __name__ == "__main__":
    if is_comment_serving():
        start_commentator(app, socketio)
    if is_gif_serving():
        start_gif_refresher(app, socketio)
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=DEBUG,
        use_reloader=DEBUG,
    )
