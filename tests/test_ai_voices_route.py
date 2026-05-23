"""GET /api/ai/voices — только TTS."""


def test_ai_voices_route(client):
    r = client.get("/api/ai/voices")
    assert r.status_code == 200
    data = r.get_json()
    assert "active" in data
    assert data.get("activeCount", 0) >= 1
