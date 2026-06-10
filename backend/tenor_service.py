"""Случайный GIF с Tenor — ротация тегов, пул в памяти и без повторов."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from backend.config import BASE_DIR, DATA_DIR
from backend.random_utils import choice, randbelow, sample, shuffle

log = logging.getLogger(__name__)

TENOR_API_KEY = os.environ.get("TENOR_API_KEY", "LIVDSRZULELA")
TENOR_CLIENT_KEY = os.environ.get("TENOR_CLIENT_KEY", "kolesoblya")
_TAGS_FILE = DATA_DIR / "tenor_tags.txt"
_FALLBACK_FILE = DATA_DIR / "gif_fallback.json"
_DEFAULT_TAGS = (
    "meme",
    "funny meme",
    "reaction meme",
    "gaming meme",
    "absurd meme",
    "viral meme",
    "lol meme",
    "dank meme",
)
_RECENT_URLS: list[str] = []
_RECENT_MAX = 96
_tag_cursor = 0
_POOL: list[dict] = []
_POOL_LOCK = threading.Lock()
_LAST_REFRESH_TS = 0.0
_POOL_MAX = 200
_REFRESH_BUSY = False


def _load_search_tags() -> list[str]:
    env = os.environ.get("TENOR_SEARCH_TAGS", "").strip()
    if env:
        tags = [t.strip() for t in env.split(",") if t.strip()]
        if tags:
            return tags
    if _TAGS_FILE.is_file():
        tags = [
            line.strip()
            for line in _TAGS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if tags:
            return tags
    return list(_DEFAULT_TAGS)


def _next_tag() -> str:
    global _tag_cursor  # noqa: PLW0603
    tags = _load_search_tags()
    tag = tags[_tag_cursor % len(tags)]
    _tag_cursor += 1
    return tag


def _load_fallback_pool() -> list[dict]:
    if _FALLBACK_FILE.is_file():
        try:
            raw = json.loads(_FALLBACK_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                out = []
                for item in raw:
                    if isinstance(item, str) and item.strip():
                        out.append({"url": item.strip(), "title": "meme"})
                    elif isinstance(item, dict) and item.get("url"):
                        out.append(
                            {
                                "url": str(item["url"]),
                                "title": str(item.get("title") or "meme"),
                            }
                        )
                if out:
                    return out
        except (OSError, json.JSONDecodeError):
            pass
    return [
        {
            "url": "https://media.tenor.com/wi8f6OqgfK8AAAAC/meme-laughing.gif",
            "title": "meme",
        }
    ]


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


def _fetch_search(tag: str) -> list[dict]:
    q = urllib.parse.quote(tag)
    pos = randbelow(500)
    limit = 50
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
        f"&limit={limit}&pos={pos % 200}&media_filter=minimal"
    )
    data = _http_get(v1_url)
    if isinstance(data, dict):
        return _urls_from_v1(data)
    return []


def _fetch_trending() -> list[dict]:
    v2_url = (
        "https://tenor.googleapis.com/v2/featured?"
        f"key={TENOR_API_KEY}&client_key={TENOR_CLIENT_KEY}"
        f"&limit=50&media_filter=gif&random=true"
    )
    data = _http_get(v2_url)
    if isinstance(data, dict):
        pool = _urls_from_v2(data)
        if pool:
            return pool
    return []


def _fetch_batch() -> list[dict]:
    tag = _next_tag()
    pool = _fetch_search(tag)
    if len(pool) < 8:
        pool.extend(_fetch_trending())
    if len(pool) < 8 and tag != "meme":
        pool.extend(_fetch_search("meme"))
    return pool


def _merge_unique(target: list[dict], seen: set[str], items: list[dict]) -> None:
    for g in items:
        url = g.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        target.append(g)


def refresh_gif_pool() -> int:
    """Подгрузить пул с Tenor (несколько тегов + trending)."""
    global _LAST_REFRESH_TS  # noqa: PLW0603
    seen: set[str] = set()
    merged: list[dict] = []
    tags = shuffle(_load_search_tags())
    for tag in sample(tags, min(5, len(tags))):
        _merge_unique(merged, seen, _fetch_search(tag))
        if len(merged) >= _POOL_MAX:
            break
    if len(merged) < 24:
        _merge_unique(merged, seen, _fetch_trending())
    if len(merged) < 12:
        _merge_unique(merged, seen, _fetch_batch())
    if not merged:
        merged = shuffle(_load_fallback_pool())

    with _POOL_LOCK:
        _POOL[:] = shuffle(merged)[:_POOL_MAX]
        _LAST_REFRESH_TS = time.time()
        size = len(_POOL)
    log.info("GIF pool refreshed: %s items", size)
    return size


def pool_status() -> dict:
    with _POOL_LOCK:
        size = len(_POOL)
    return {
        "poolSize": size,
        "lastRefresh": int(_LAST_REFRESH_TS * 1000) if _LAST_REFRESH_TS else None,
        "refreshIntervalSec": pool_refresh_interval_sec(),
    }


def pool_refresh_interval_sec() -> int:
    return max(60, int(os.environ.get("TENOR_POOL_REFRESH_SEC", "3600")))


def pool_low_threshold() -> int:
    return max(8, int(os.environ.get("TENOR_POOL_LOW", "20")))


def _pick_from_pool() -> dict | None:
    with _POOL_LOCK:
        pool = list(_POOL)
    if not pool:
        return None
    fresh = [g for g in pool if g["url"] not in _RECENT_URLS]
    pick_from = fresh or pool
    return choice(pick_from)


def _remember_pick(picked: dict) -> None:
    global _RECENT_URLS  # noqa: PLW0603
    _RECENT_URLS.append(picked["url"])
    if len(_RECENT_URLS) > _RECENT_MAX:
        _RECENT_URLS = _RECENT_URLS[-_RECENT_MAX:]


def schedule_pool_refresh_if_low() -> None:
    global _REFRESH_BUSY  # noqa: PLW0603
    with _POOL_LOCK:
        low = len(_POOL) < pool_low_threshold()
    if not low or _REFRESH_BUSY:
        return
    _REFRESH_BUSY = True

    def _worker() -> None:
        global _REFRESH_BUSY  # noqa: PLW0603
        try:
            refresh_gif_pool()
        except Exception as exc:
            log.warning("GIF pool low refresh failed: %s", exc)
        finally:
            _REFRESH_BUSY = False

    threading.Thread(target=_worker, name="gif-pool-low", daemon=True).start()


def pick_meme_gif() -> dict:
    picked = _pick_from_pool()
    if not picked:
        pool = shuffle(_fetch_batch())
        fresh = [g for g in pool if g["url"] not in _RECENT_URLS]
        pick_from = fresh if fresh else pool
        if not pick_from:
            pick_from = shuffle(_load_fallback_pool())
            pick_from = [g for g in pick_from if g["url"] not in _RECENT_URLS] or pick_from
        picked = choice(pick_from)
    _remember_pick(picked)
    schedule_pool_refresh_if_low()
    return picked


def tags_for_api() -> dict:
    st = pool_status()
    return {
        "tags": _load_search_tags(),
        "tagsFile": str(_TAGS_FILE.relative_to(BASE_DIR)).replace("\\", "/"),
        "fallbackFile": str(_FALLBACK_FILE.relative_to(BASE_DIR)).replace("\\", "/"),
        **st,
    }
