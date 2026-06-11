"""Каталог предметов: полнота и уникальность."""

from backend.items.catalog import get_item, load_catalog


def test_catalog_has_47_items():
    cat = load_catalog(force=True)
    removed = {13, 18, 21, 23, 31, 32, 35, 38, 39, 45}
    assert len(cat) == 48 - len(removed)
    assert set(cat.keys()) == set(range(1, 49)) - removed


def test_every_item_has_effect_and_name():
    removed = {13, 18, 21, 23, 31, 32, 35, 38, 39, 45}
    for iid in range(1, 49):
        if iid in removed:
            continue
        item = get_item(iid)
        assert item is not None
        assert item.name
        assert item.flavor
        assert item.description
        assert item.effect or item.kind == "none"
