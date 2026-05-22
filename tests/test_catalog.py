"""Каталог предметов: полнота и уникальность."""

from backend.items.catalog import get_item, load_catalog


def test_catalog_has_48_items():
    cat = load_catalog(force=True)
    assert len(cat) == 48
    assert set(cat.keys()) == set(range(1, 49))


def test_every_item_has_effect_and_name():
    for iid in range(1, 49):
        item = get_item(iid)
        assert item is not None
        assert item.name
        assert item.effect or item.kind == "none"
