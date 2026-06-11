"""Тест горячей перезагрузки data/."""

from backend.data_reload import reload_all_data
from backend.items.catalog import get_item, load_catalog


def test_reload_all_data(app):
    with app.app_context():
        before = len(load_catalog())
        result = reload_all_data()
        assert result["ok"] is True
        assert result["items"] == before
        assert get_item(1) is not None
