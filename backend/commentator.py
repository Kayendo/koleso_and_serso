"""Комментатор: фраза из файла + Edge TTS (без LLM)."""

from __future__ import annotations

import base64

from backend.comment_phrases import phrase_count, pick_line
from backend.comment_snapshot import build_tick_context, focus_player


def make_comment() -> dict:
    ctx = build_tick_context()
    if not ctx:
        raise ValueError("Нет игроков для комментария")
    target = str(ctx.get("focusPlayer") or "игрок")
    player = focus_player(ctx, target)
    text = pick_line(target, player)

    from backend.ai_tts import pick_voice, synthesize_speech_mp3

    voice = pick_voice()
    audio, voice = synthesize_speech_mp3(text, voice)
    if not audio:
        raise ValueError("Озвучка вернула пустой файл")

    return {
        "text": text,
        "targetPlayer": target,
        "voice": voice.get("id"),
        "voiceLabel": voice.get("label"),
        "audioMime": "audio/mpeg",
        "audioBase64": base64.b64encode(audio).decode("ascii"),
    }


def status() -> dict:
    n = phrase_count()
    return {
        "ok": n > 0,
        "phraseCount": n,
        "phrasesFile": "data/ai_comment_phrases.jsonl",
        "mode": "phrases_and_tts",
    }
