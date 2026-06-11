"""Горячая перезагрузка файлов из data/ (без рестарта сервера)."""

from __future__ import annotations


def reload_all_data() -> dict:
    from backend.ai_tts import reload_roster
    from backend.comment_phrases import reload_phrases
    from backend.items.catalog import load_catalog
    from backend.tenor_service import refresh_gif_pool

    catalog = load_catalog(force=True)
    reload_roster()
    reload_phrases()
    gif_count = refresh_gif_pool()

    return {
        "ok": True,
        "items": len(catalog),
        "commentPhrases": True,
        "ttsRoster": True,
        "gifPoolSize": gif_count,
        "note": "Списки игр и casino_news.txt читаются с диска автоматически.",
    }
