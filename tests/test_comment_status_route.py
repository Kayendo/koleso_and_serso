"""GET /api/comment/status — лёгкий статус без TTS."""


def test_comment_status(client):
    r = client.get("/api/comment/status")
    assert r.status_code == 200
    data = r.get_json()
    assert "phraseCount" in data
    assert data["enabled"] is False
    assert data["mode"] == "phrases_and_tts"
