"""Персонажи TTS (characters pool)."""

from backend.ai_tts import (
    _find_by_id,
    _resolve_edge_voice,
    _use_characters_pool,
    list_active_voices,
    pick_voice,
)


def test_characters_pool_used():
    assert _use_characters_pool() is True


def test_active_includes_ded_moroz():
    active = list_active_voices()
    ids = {v["id"] for v in active}
    assert "ded_moroz" in ids
    assert "peter_griffin" in ids


def test_find_by_id():
    p = _find_by_id("drevniy_rus")
    assert p is not None
    assert p["provider"] == "edge"
    assert p["voice"] == "ru-RU-DmitryNeural"


def test_pick_voice_random(monkeypatch):
    monkeypatch.delenv("AI_TTS_VOICE", raising=False)
    v = pick_voice()
    assert v.get("id")
    assert v.get("provider") in ("edge", "silero", "http")


def test_resolve_edge_voice_russian_text():
    profile = {
        "id": "peter_griffin",
        "voice": "en-US-GuyNeural",
        "rate": "+18%",
        "pitch": "+12Hz",
    }
    text = "Иван, ну как тебе Metro? Норм или полный кал."
    assert _resolve_edge_voice(text, profile) == "ru-RU-DmitryNeural"


def test_all_characters_use_ru_or_uk_voice():
    for v in list_active_voices():
        if v.get("provider") != "edge":
            continue
        voice = _find_by_id(v["id"])
        assert voice is not None
        loc = (voice.get("voice") or "").split("-")
        prefix = f"{loc[0]}-{loc[1]}" if len(loc) >= 2 else ""
        assert prefix in ("ru-RU", "uk-UA"), v["id"]
