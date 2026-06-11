"""Заготовленные фразы: ленивая загрузка + индекс по тегам."""

from __future__ import annotations

import json
import random
from collections import deque
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR

_PHRASES_FILE = DATA_DIR / "ai_comment_phrases.jsonl"
_EXTRA_FILE = DATA_DIR / "ai_comment_phrases_extra.jsonl"

_TAG_PRIORITY = (
    "durka",
    "debuff",
    "buff",
    "inventory",
    "game",
    "low_points",
    "high_points",
    "no_game",
    "cell",
    "fact",
    "general",
)

_HARDCODED_GAMES = (
    "Metro",
    "Dark Souls",
    "Witcher",
    "Cyberpunk",
    "Skyrim",
    "Minecraft",
    "Dota",
    "Valorant",
    "Elden Ring",
    "GTA",
    "CS2",
)

_rows: list[dict[str, Any]] | None = None
_by_tag: dict[str, list[int]] | None = None
_recent: deque[str] = deque(maxlen=40)


def _valid(text: str, tags: set[str]) -> bool:
    if "{name}" not in text:
        return False
    if "game" in tags and "{game}" not in text:
        if any(g in text for g in _HARDCODED_GAMES):
            return False
    return True


def _ensure_loaded() -> None:
    global _rows, _by_tag
    if _rows is not None:
        return
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for path in (_PHRASES_FILE, _EXTRA_FILE):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = (row.get("text") or "").strip()
            tags = set(row.get("tags") or ["general"])
            if not text or text in seen or not _valid(text, tags):
                continue
            seen.add(text)
            rows.append(row)
    _rows = rows
    index: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        for tag in row.get("tags") or ["general"]:
            index.setdefault(tag, []).append(i)
    _by_tag = index


def phrase_count() -> int:
    _ensure_loaded()
    return len(_rows or [])


def situation_tags(p: dict) -> set[str]:
    tags: set[str] = set()
    g = p.get("activeGame") or {}
    if g.get("title"):
        tags.add("game")
    pts = int(p.get("points") or 0)
    if pts <= 5:
        tags.add("low_points")
    elif pts >= 15:
        tags.add("high_points")
    if p.get("inDurka"):
        tags.add("durka")
    if p.get("debuffs"):
        tags.add("debuff")
    if p.get("buffs"):
        tags.add("buff")
    if p.get("inventoryItems"):
        tags.add("inventory")
    if not g.get("title"):
        tags.add("no_game")
    if p.get("cellName"):
        tags.add("cell")
    return tags


def _primary_tag(active: set[str]) -> str:
    for tag in _TAG_PRIORITY:
        if tag in active:
            return tag
    return "general"


def _pool_indices(active: set[str]) -> list[int]:
    _ensure_loaded()
    assert _by_tag is not None
    primary = _primary_tag(active)
    pool = list(_by_tag.get(primary, []))
    if len(pool) < 12:
        seen_idx: set[int] = set()
        for tag in active:
            for i in _by_tag.get(tag, []):
                seen_idx.add(i)
        pool = list(seen_idx)
    if not pool:
        pool = list(_by_tag.get("general", []))
    if not pool:
        pool = list(range(len(_rows or [])))
    return pool


def _fmt(template: str, target: str, p: dict) -> str:
    g = p.get("activeGame") or {}
    title = (g.get("title") or "эта игра").strip()
    inv = p.get("inventoryItems") or []
    debuffs = p.get("debuffs") or []
    buffs = p.get("buffs") or []
    try:
        return template.format(
            name=target,
            game=title,
            points=p.get("points", 0),
            cell=p.get("cellName") or "клетка",
            hltb=g.get("hltbHours") or "?",
            played=g.get("playTime") or "0",
            laps=p.get("laps", 0),
            items=", ".join(inv[:3]) if inv else "хлам",
            debuffs=", ".join(debuffs[:2]) if debuffs else "грех",
            buffs=", ".join(buffs[:2]) if buffs else "понты",
            ins="лошара",
        )
    except (KeyError, ValueError):
        return template.replace("{name}", target).replace("{game}", title)


def pick_line(target: str, player: dict) -> str:
    """Случайная фраза из пула под ситуацию игрока."""
    _ensure_loaded()
    assert _rows is not None
    pool = _pool_indices(situation_tags(player))
    recent = set(_recent)
    candidates = [i for i in pool if _rows[i].get("text") not in recent]
    if not candidates:
        candidates = pool

    for _ in range(8):
        row = _rows[random.choice(candidates)]
        line = _fmt(row["text"], target, player).strip()
        if line and "{" not in line and line not in recent:
            _recent.append(line)
            return line[:280]

    row = _rows[random.choice(pool)]
    line = _fmt(row["text"], target, player).strip()[:280]
    if line:
        _recent.append(line)
    return line or f"{target}, крути колесо дальше."


def reload_phrases() -> None:
    """Сброс кэша фраз (после правки ai_comment_phrases*.jsonl)."""
    global _rows, _by_tag
    _rows = None
    _by_tag = None
