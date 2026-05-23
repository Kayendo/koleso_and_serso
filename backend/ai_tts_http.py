"""Озвучка через свой HTTP-сервер (RVC, XTTS, Piper API и т.п.)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def synthesize_http(
    text: str,
    url: str | None = None,
    *,
    voice_id: str = "",
    timeout: float = 60.0,
) -> bytes:
    endpoint = (url or os.environ.get("AI_TTS_HTTP_URL") or "").strip()
    if not endpoint:
        raise ValueError("AI_TTS_HTTP_URL не задан для provider=http")

    payload = {"text": text.strip(), "input": text.strip()}
    if voice_id:
        payload["voice"] = voice_id
        payload["speaker"] = voice_id

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"TTS HTTP {e.code}: {err}") from e

    if "json" in ctype:
        data = json.loads(body.decode("utf-8"))
        if data.get("audioBase64"):
            import base64

            return base64.b64decode(data["audioBase64"])
        if data.get("url"):
            with urllib.request.urlopen(data["url"], timeout=timeout) as r2:
                return r2.read()
        raise ValueError("HTTP TTS JSON без audioBase64/url")
    return body
