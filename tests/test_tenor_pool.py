"""Tenor GIF pool refresh."""

from unittest.mock import patch

from backend.tenor_service import pick_meme_gif, pool_status, refresh_gif_pool


def test_refresh_gif_pool_dedupes():
    batches = [
        [{"url": "https://a/1.gif", "title": "a"}, {"url": "https://a/2.gif", "title": "b"}],
        [{"url": "https://a/1.gif", "title": "a"}, {"url": "https://a/3.gif", "title": "c"}],
    ]

    def fake_search(tag):
        return batches.pop(0) if batches else []

    with patch("backend.tenor_service._fetch_search", side_effect=fake_search):
        with patch("backend.tenor_service._fetch_trending", return_value=[]):
            with patch("backend.tenor_service._load_search_tags", return_value=["meme", "funny"]):
                size = refresh_gif_pool()
    assert size == 3
    st = pool_status()
    assert st["poolSize"] == 3
    assert st["lastRefresh"]


def test_pick_uses_pool_without_fetch():
    with patch("backend.tenor_service._POOL", [{"url": "https://x/p.gif", "title": "x"}]):
        with patch("backend.tenor_service._fetch_batch") as fetch:
            out = pick_meme_gif()
    fetch.assert_not_called()
    assert out["url"] == "https://x/p.gif"
