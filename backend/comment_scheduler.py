"""Периодический комментатор: фраза + озвучка в lobby."""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from typing import Any

from flask import Flask

log = logging.getLogger(__name__)

_busy = False
_started = False
_last_payload: dict[str, Any] | None = None
_last_error: str | None = None


def enabled() -> bool:
    return os.environ.get("COMMENTATOR_ENABLED", os.environ.get("AI_COMMENTATOR_ENABLED", "1")).strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def is_serving_process() -> bool:
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True
    if "WERKZEUG_SERVER_FD" not in os.environ:
        return True
    return False


def _interval_sec() -> float:
    lo = float(os.environ.get("COMMENTATOR_INTERVAL_MIN", os.environ.get("AI_COMMENTATOR_INTERVAL_MIN", "30")))
    hi = float(os.environ.get("COMMENTATOR_INTERVAL_MAX", os.environ.get("AI_COMMENTATOR_INTERVAL_MAX", "40")))
    if hi < lo:
        hi = lo
    return random.uniform(lo, hi)


def _first_delay_sec() -> float:
    return float(
        os.environ.get("COMMENTATOR_FIRST_DELAY", os.environ.get("AI_COMMENTATOR_FIRST_DELAY", "12"))
    )


def get_last() -> dict[str, Any] | None:
    return _last_payload


def get_last_error() -> str | None:
    return _last_error


def is_started() -> bool:
    return _started


def _tick(app: Flask, socketio) -> None:
    global _last_payload, _last_error
    with app.app_context():
        from backend.commentator import make_comment, status

        st = status()
        if not st.get("ok"):
            _last_error = st.get("error") or "нет фраз"
            return

        try:
            out = make_comment()
        except Exception as exc:
            _last_error = str(exc)
            log.warning("Commentator tick: %s", exc, exc_info=True)
            return

        emitted_at = int(time.time() * 1000)
        payload = {
            "id": emitted_at,
            "emittedAt": emitted_at,
            "text": out["text"],
            "targetPlayer": out["targetPlayer"],
            "voice": out.get("voice"),
            "voiceLabel": out.get("voiceLabel"),
            "audioMime": out.get("audioMime", "audio/mpeg"),
            "audioBase64": out.get("audioBase64", ""),
        }
        _last_payload = payload
        _last_error = None
        socketio.emit("game_comment", payload, room="lobby", namespace="/")
        log.info("Comment -> %s: %s", out["targetPlayer"], (out["text"] or "")[:72])


def _worker(app: Flask, socketio) -> None:
    global _busy
    if _busy:
        return
    _busy = True
    try:
        _tick(app, socketio)
    finally:
        _busy = False


def _loop(app: Flask, socketio) -> None:
    log.info("Commentator loop started")
    time.sleep(_first_delay_sec())
    while True:
        try:
            threading.Thread(
                target=_worker,
                args=(app, socketio),
                name="comment-tick",
                daemon=True,
            ).start()
        except Exception as exc:
            log.warning("Commentator schedule failed: %s", exc)
        time.sleep(_interval_sec())


def start(app: Flask, socketio) -> None:
    global _started
    if _started or not enabled():
        return
    if not is_serving_process():
        return
    _started = True
    app_obj = app._get_current_object() if hasattr(app, "_get_current_object") else app
    threading.Thread(
        target=_loop,
        args=(app_obj, socketio),
        name="commentator-loop",
        daemon=True,
    ).start()
    log.info(
        "Commentator on (first %.0fs, then %.0f–%.0fs)",
        _first_delay_sec(),
        float(os.environ.get("COMMENTATOR_INTERVAL_MIN", "30")),
        float(os.environ.get("COMMENTATOR_INTERVAL_MAX", "40")),
    )
