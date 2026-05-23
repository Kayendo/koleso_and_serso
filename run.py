"""Запуск сервера: python run.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.app import create_app, socketio
from backend.comment_scheduler import is_serving_process, start as start_commentator

if __name__ == "__main__":
    app = create_app()
    if is_serving_process():
        start_commentator(app, socketio)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
else:
    app = create_app()
