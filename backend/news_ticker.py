"""Бегущая строка новостей — data/casino_news.txt."""

from __future__ import annotations

from backend.config import BASE_DIR

NEWS_FILE = BASE_DIR / "data" / "casino_news.txt"


def load_news_items() -> list[str]:
    if not NEWS_FILE.is_file():
        return []
    lines: list[str] = []
    for raw in NEWS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines
