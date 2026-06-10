"""Запуск сервера: python run.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.app import create_app, socketio
from backend.comment_scheduler import is_serving_process as is_comment_serving, start as start_commentator
from backend.tenor_refresher import is_serving_process as is_gif_serving, start as start_gif_refresher

app = create_app()

if __name__ == "__main__":
    if is_comment_serving():
        start_commentator(app, socketio)
    if is_gif_serving():
        start_gif_refresher(app, socketio)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
else:
    app = create_app()
