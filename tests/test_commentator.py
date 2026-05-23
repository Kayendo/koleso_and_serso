"""Комментатор: шаблоны + снимок (без TTS в тестах)."""

from unittest.mock import patch

from backend.comment_phrases import phrase_count, pick_line, situation_tags
from backend.comment_snapshot import build_tick_context
from backend.commentator import make_comment, status


def test_phrase_count(app):
    with app.app_context():
        assert phrase_count() >= 100


def test_pick_line_has_name(app, actor):
    with app.app_context():
        ctx = build_tick_context()
        assert ctx
        p = next(x for x in ctx["players"] if x["username"] == actor.username)
        line = pick_line(actor.username, p)
        assert actor.username in line
        assert "{" not in line


def test_situation_tags_game(app, actor):
    with app.app_context():
        ctx = build_tick_context()
        p = next(x for x in ctx["players"] if x["username"] == actor.username)
        tags = situation_tags(p)
        assert "game" in tags or "no_game" in tags


def test_make_comment_mock_tts(app, actor):
    with app.app_context():
        with patch(
            "backend.ai_tts.synthesize_speech_mp3",
            return_value=(b"\xff\xfb", {"id": "ded_moroz", "label": "test"}),
        ):
            out = make_comment()
        assert out["text"]
        assert out["audioBase64"]
        assert out["targetPlayer"]


def test_status_ok(app):
    with app.app_context():
        st = status()
        assert st["ok"] is True
        assert st["phraseCount"] >= 100
