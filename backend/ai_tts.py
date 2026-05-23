"""Озвучка: персонажи (Edge / Silero / HTTP) + классический roster Edge."""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
from pathlib import Path

from backend.config import DATA_DIR

_ROSTER_FILE = DATA_DIR / "ai_tts_roster.json"
_CHARACTERS_FILE = DATA_DIR / "ai_tts_characters.json"
_CATALOG_FILE = DATA_DIR / "edge_tts_catalog.json"

_roster_cache: dict | None = None
_characters_cache: dict | None = None

# Edge: en/de/fr на кириллице озвучивают только латиницу (обрыв фразы).
_EDGE_LOCALES_RU = frozenset({"ru-RU", "uk-UA", "be-BY"})
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_FEMALE_CHARACTER_IDS = frozenset(
    {"babushka", "chipmunk", "silero_baya", "silero_xenia"}
)


def _text_is_russian(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    cyr = len(_CYRILLIC_RE.findall(text))
    return cyr >= max(2, len(letters) // 5)


def _edge_locale(voice_id: str) -> str:
    parts = voice_id.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return ""


def _resolve_edge_voice(text: str, profile: dict) -> str:
    """Для русских фраз — только ru/uk голос, иначе Edge читает кусок по-английски."""
    voice = (profile.get("voice") or "ru-RU-DmitryNeural").strip()
    override = (profile.get("voiceRu") or "").strip()
    if override:
        return override
    if not _text_is_russian(text):
        return voice
    if _edge_locale(voice) in _EDGE_LOCALES_RU:
        return voice
    cid = profile.get("id") or ""
    if cid in _FEMALE_CHARACTER_IDS:
        return "ru-RU-SvetlanaNeural"
    return "ru-RU-DmitryNeural"


def _load_roster() -> dict:
    global _roster_cache
    if _roster_cache is not None:
        return _roster_cache
    if _ROSTER_FILE.is_file():
        _roster_cache = json.loads(_ROSTER_FILE.read_text(encoding="utf-8"))
    else:
        _roster_cache = {"mode": "random", "pool": []}
    return _roster_cache


def _load_characters() -> dict:
    global _characters_cache
    if _characters_cache is not None:
        return _characters_cache
    if _CHARACTERS_FILE.is_file():
        _characters_cache = json.loads(
            _CHARACTERS_FILE.read_text(encoding="utf-8")
        )
    else:
        _characters_cache = {"mode": "random", "characters": []}
    return _characters_cache


def reload_roster() -> None:
    global _roster_cache, _characters_cache
    _roster_cache = None
    _characters_cache = None


def _use_characters_pool() -> bool:
    mode = (os.environ.get("AI_TTS_POOL") or "characters").strip().lower()
    if mode in ("roster", "edge", "classic"):
        return False
    return _CHARACTERS_FILE.is_file()


def _normalize_entry(raw: dict) -> dict | None:
    if not raw.get("enabled", True):
        return None
    cid = (raw.get("id") or "").strip()
    if not cid:
        return None
    provider = (raw.get("provider") or "edge").strip().lower()
    label = raw.get("label") or cid
    base = {"id": cid, "label": label, "provider": provider}

    if provider == "edge":
        voice = (raw.get("voice") or raw.get("edgeVoice") or cid).strip()
        return {
            **base,
            "voice": voice,
            "rate": raw.get("rate", "+0%"),
            "pitch": raw.get("pitch", "+0Hz"),
        }
    if provider == "silero":
        return {
            **base,
            "sileroSpeaker": raw.get("sileroSpeaker") or "xenia",
            "sileroSpeed": float(raw.get("sileroSpeed") or 1.0),
        }
    if provider == "http":
        url = (raw.get("httpUrl") or os.environ.get("AI_TTS_HTTP_URL") or "").strip()
        return {**base, "httpUrl": url}
    return {**base, "voice": cid, "rate": "+0%", "pitch": "+0Hz"}


def _all_pool_entries() -> list[dict]:
    if _use_characters_pool():
        data = _load_characters()
        rows = data.get("characters") or []
        mode = data.get("mode", "random")
    else:
        data = _load_roster()
        rows = data.get("pool") or []
        mode = data.get("mode", "random")
    out: list[dict] = []
    for raw in rows:
        norm = _normalize_entry(raw)
        if norm:
            out.append(norm)
    return out, mode


def list_active_voices() -> list[dict]:
    entries, _ = _all_pool_entries()
    return [
        {
            "id": v["id"],
            "label": v.get("label", v["id"]),
            "provider": v.get("provider", "edge"),
            "rate": v.get("rate", "+0%"),
            "pitch": v.get("pitch", "+0Hz"),
            "enabled": True,
        }
        for v in entries
    ]


def list_catalog_voices(locale_prefix: str | None = None) -> list[dict]:
    if not _CATALOG_FILE.is_file():
        return []
    raw = json.loads(_CATALOG_FILE.read_text(encoding="utf-8"))
    if locale_prefix:
        raw = [v for v in raw if (v.get("locale") or "").startswith(locale_prefix)]
    return raw


def list_character_catalog() -> list[dict]:
    data = _load_characters()
    return [
        {
            "id": c.get("id"),
            "label": c.get("label"),
            "provider": c.get("provider", "edge"),
            "enabled": bool(c.get("enabled", True)),
        }
        for c in data.get("characters") or []
        if c.get("id")
    ]


def voices_for_api() -> dict:
    active = list_active_voices()
    catalog = list_catalog_voices()
    by_locale: dict[str, list] = {}
    for v in catalog:
        loc = v.get("locale") or "?"
        by_locale.setdefault(loc, []).append(v)
    pool_kind = "characters" if _use_characters_pool() else "roster"
    silero_ok = False
    try:
        from backend.ai_tts_silero import silero_available

        silero_ok = silero_available()
    except Exception:
        pass
    return {
        "mode": _load_characters().get("mode", "random")
        if pool_kind == "characters"
        else _load_roster().get("mode", "random"),
        "poolKind": pool_kind,
        "rosterFile": "data/ai_tts_roster.json",
        "charactersFile": "data/ai_tts_characters.json",
        "catalogFile": "data/edge_tts_catalog.json",
        "activeCount": len(active),
        "catalogCount": len(catalog),
        "active": active,
        "characters": list_character_catalog(),
        "catalogByLocale": by_locale,
        "sileroAvailable": silero_ok,
        "howTo": (
            "Персонажи: data/ai_tts_characters.json (enabled:true). "
            "AI_TTS_POOL=characters | roster. AI_TTS_VOICE=ded_moroz | random. "
            "Silero: pip install torch pydub. HTTP-клон: AI_TTS_HTTP_URL."
        ),
    }


def _find_by_id(voice_id: str) -> dict | None:
    entries, _ = _all_pool_entries()
    for e in entries:
        if e["id"] == voice_id:
            return e
    return None


def pick_voice() -> dict:
    forced = (os.environ.get("AI_TTS_VOICE") or "").strip()
    entries, mode = _all_pool_entries()

    if forced and forced.lower() not in ("random", "auto", ""):
        found = _find_by_id(forced)
        if found:
            return found
        if not _use_characters_pool() or "." in forced or "-" in forced:
            return {
                "id": forced,
                "label": "из .env",
                "provider": "edge",
                "voice": forced,
                "rate": "+0%",
                "pitch": "+0Hz",
            }
        return {
            "id": forced,
            "label": "из .env (не найден в characters)",
            "provider": "edge",
            "voice": "ru-RU-DmitryNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
        }

    if not entries:
        return {
            "id": "ru-RU-DmitryNeural",
            "label": "fallback",
            "provider": "edge",
            "voice": "ru-RU-DmitryNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
        }

    if mode == "first":
        return entries[0]
    return random.choice(entries)


def list_voices() -> list[dict]:
    return list_active_voices()


async def _synthesize_edge_async(text: str, profile: dict) -> bytes:
    import edge_tts

    voice = _resolve_edge_voice(text, profile)
    communicate = edge_tts.Communicate(
        text.strip(),
        voice,
        rate=profile.get("rate") or "+0%",
        pitch=profile.get("pitch") or "+0Hz",
    )
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def _synthesize_edge(text: str, profile: dict) -> bytes:
    return asyncio.run(_synthesize_edge_async(text, profile))


def _synthesize_silero(text: str, profile: dict) -> bytes:
    from backend.ai_tts_silero import silero_available, synthesize_wav, wav_to_mp3

    if not silero_available():
        raise RuntimeError(
            "Silero: установи torch (pip install torch), затем включи персонажа silero_*"
        )
    wav = synthesize_wav(
        text,
        speaker=profile.get("sileroSpeaker") or "xenia",
        speed=float(profile.get("sileroSpeed") or 1.0),
    )
    try:
        return wav_to_mp3(wav)
    except RuntimeError:
        return wav


def _synthesize_http(text: str, profile: dict) -> bytes:
    from backend.ai_tts_http import synthesize_http

    return synthesize_http(
        text, profile.get("httpUrl"), voice_id=profile.get("id", "")
    )


def synthesize_speech_mp3(
    text: str, voice_profile: dict | None = None
) -> tuple[bytes, dict]:
    if not text or not text.strip():
        return b"", voice_profile or pick_voice()
    profile = voice_profile or pick_voice()
    provider = (profile.get("provider") or "edge").lower()

    if provider == "silero":
        audio = _synthesize_silero(text, profile)
    elif provider == "http":
        audio = _synthesize_http(text, profile)
    else:
        audio = _synthesize_edge(text, profile)

    return audio, profile
