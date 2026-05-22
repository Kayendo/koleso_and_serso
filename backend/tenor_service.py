"""Случайный GIF с Tenor по тегу meme — без повторов из маленького кэша."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from backend.random_utils import choice, randbelow, shuffle

TENOR_API_KEY = os.environ.get("TENOR_API_KEY", "LIVDSRZULELA")
TENOR_CLIENT_KEY = os.environ.get("TENOR_CLIENT_KEY", "kolesoblya")
SEARCH_TAG = "meme"
_RECENT_URLS: list[str] = []
_RECENT_MAX = 24


def _http_get(url: str, timeout: float = 8.0) -> dict | list | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Kolesoblya/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _urls_from_v2(data: dict) -> list[dict]:
    out: list[dict] = []
    for item in data.get("results") or []:
        media = item.get("media_formats") or {}
        gif = media.get("gif") or media.get("mediumgif") or media.get("tinygif")
        if not gif or not gif.get("url"):
            continue
        out.append(
            {
                "url": gif["url"],
                "title": item.get("content_description") or item.get("title") or "meme",
            }
        )
    return out


def _urls_from_v1(data: dict) -> list[dict]:
    out: list[dict] = []
    for item in data.get("results") or []:
        media = item.get("media") or []
        if not media:
            continue
        gif = media[0].get("gif") or media[0].get("mediumgif") or media[0].get("tinygif")
        if not gif or not gif.get("url"):
            continue
        out.append(
            {
                "url": gif["url"],
                "title": item.get("title") or "meme",
            }
        )
    return out


def _fetch_batch() -> list[dict]:
    q = urllib.parse.quote(SEARCH_TAG)
    pos = randbelow(80)
    limit = 30
    v2_url = (
        "https://tenor.googleapis.com/v2/search?"
        f"q={q}&key={TENOR_API_KEY}&client_key={TENOR_CLIENT_KEY}"
        f"&limit={limit}&pos={pos}&media_filter=gif&random=true"
    )
    data = _http_get(v2_url)
    if isinstance(data, dict):
        pool = _urls_from_v2(data)
        if pool:
            return pool

    v1_url = (
        f"https://g.tenor.com/v1/search?q={q}&key={TENOR_API_KEY}"
        f"&limit={limit}&pos={pos}&media_filter=minimal"
    )
    data = _http_get(v1_url)
    if isinstance(data, dict):
        return _urls_from_v1(data)
    return []


def pick_meme_gif() -> dict:
    global _RECENT_URLS  # noqa: PLW0603
    pool = shuffle(_fetch_batch())
    fresh = [g for g in pool if g["url"] not in _RECENT_URLS]
    pick_from = fresh if fresh else pool
    if not pick_from:
        return {
            "url": "https://media.tenor.com/wi8f6OqgfK8AAAAC/meme-laughing.gif",
            "title": "meme",
        }
    picked = choice(pick_from)
    _RECENT_URLS.append(picked["url"])
    if len(_RECENT_URLS) > _RECENT_MAX:
        _RECENT_URLS = _RECENT_URLS[-_RECENT_MAX:]
    return picked
