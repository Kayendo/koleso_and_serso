"""Фоновое обновление пула GIF раз в N секунд."""

from __future__ import annotations

import logging
import os
import threading
import time

from flask import Flask

log = logging.getLogger(__name__)

_started = False


def is_serving_process() -> bool:
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True
    if "WERKZEUG_SERVER_FD" not in os.environ:
        return True
    return False


def enabled() -> bool:
    return os.environ.get("TENOR_POOL_REFRESH_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _first_delay_sec() -> float:
    return float(os.environ.get("TENOR_POOL_FIRST_DELAY", "15"))


def _tick(app: Flask, socketio) -> None:
    from backend.tenor_service import pool_status, refresh_gif_pool

    with app.app_context():
        try:
            size = refresh_gif_pool()
        except Exception as exc:
            log.warning("GIF pool refresh failed: %s", exc, exc_info=True)
            return
    payload = pool_status()
    payload["poolSize"] = size
    socketio.emit("gif_pool_refresh", payload, room="lobby", namespace="/")
    log.info("GIF pool broadcast: %s items", size)


def _loop(app: Flask, socketio) -> None:
    from backend.tenor_service import pool_refresh_interval_sec

    log.info("GIF pool refresher started")
    time.sleep(_first_delay_sec())
    while True:
        try:
            threading.Thread(
                target=_tick,
                args=(app, socketio),
                name="gif-pool-refresh",
                daemon=True,
            ).start()
        except Exception as exc:
            log.warning("GIF pool schedule failed: %s", exc)
        time.sleep(pool_refresh_interval_sec())


def start(app: Flask, socketio) -> None:
    global _started  # noqa: PLW0603
    if _started or not enabled() or not is_serving_process():
        return
    _started = True
    app_obj = app._get_current_object() if hasattr(app, "_get_current_object") else app
    threading.Thread(
        target=_loop,
        args=(app_obj, socketio),
        name="gif-pool-loop",
        daemon=True,
    ).start()
    from backend.tenor_service import pool_refresh_interval_sec

    log.info(
        "GIF pool refresh on (first %.0fs, then every %ss)",
        _first_delay_sec(),
        pool_refresh_interval_sec(),
    )
