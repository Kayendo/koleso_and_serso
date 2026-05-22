from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

try:
    from howlongtobeatpy import HowLongToBeat
except ImportError:
    HowLongToBeat = None  # type: ignore

_URL_CACHE: dict[str, str] = {}


def _main_story_hours(entry: Any) -> float | None:
    for attr in ("main_story", "gameplay_main", "main"):
        val = getattr(entry, attr, None)
        if val and val > 0:
            return round(float(val) / 3600, 1) if val > 100 else round(float(val), 1)
    comp = getattr(entry, "comp_main", None)
    if comp:
        return round(float(comp), 1)
    return None


def _search_best(title: str) -> Any | None:
    if not title or HowLongToBeat is None:
        return None
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(HowLongToBeat().async_search(title))
    finally:
        loop.close()
    if not results:
        return None
    return max(results, key=lambda e: getattr(e, "similarity", 0) or 0)


def hltb_url_for_title(title: str) -> str:
    key = (title or "").strip()
    if not key:
        return "https://howlongtobeat.com/"
    if key in _URL_CACHE:
        return _URL_CACHE[key]
    fallback = f"https://howlongtobeat.com/?q={urllib.parse.quote(key)}"
    try:
        best = _search_best(key)
        if best:
            link = getattr(best, "game_web_link", None)
            if link:
                _URL_CACHE[key] = str(link)
                return _URL_CACHE[key]
            gid = getattr(best, "game_id", None)
            if gid:
                url = f"https://howlongtobeat.com/game/{gid}"
                _URL_CACHE[key] = url
                return url
    except Exception:
        pass
    _URL_CACHE[key] = fallback
    return fallback


def fetch_hltb_hours(title: str) -> float | None:
    try:
        best = _search_best(title)
        if not best:
            return None
        return _main_story_hours(best)
    except Exception:
        return None
