"""Выбор соседних секторов на колесе (корона, магазины)."""

from __future__ import annotations

from typing import Any


def neighbor_indices(idx: int, n: int, *, span: int = 1) -> list[int]:
    """span=1 → 3 соседа (−1,0,+1); span=2 → 4 соседа (−2,−1,+1,+2)."""
    if n <= 0:
        return []
    if span == 1:
        return [(idx - 1) % n, idx, (idx + 1) % n]
    return [(idx - 2) % n, (idx - 1) % n, (idx + 1) % n, (idx + 2) % n]


def vertical_neighbor_indices(idx: int, n: int) -> list[int]:
    """Только секторы сверху и снизу от центра (без центра)."""
    if n <= 0:
        return []
    return [(idx - 1) % n, (idx + 1) % n]


def choices_for_titles(wheel: list[str], idx: int, *, four: bool = False) -> list[dict]:
    n = len(wheel)
    indices = neighbor_indices(idx, n, span=2 if four else 1)
    choices: list[dict] = []
    for i, wi in enumerate(indices):
        choices.append(
            {
                "choiceIndex": i,
                "wheelIndex": wi,
                "title": wheel[wi],
            }
        )
    return choices


def five_sector_indices(idx: int, n: int) -> list[int]:
    """Центр + два сверху + два снизу (5 секторов)."""
    if n <= 0:
        return []
    return [(idx - 2) % n, (idx - 1) % n, idx, (idx + 1) % n, (idx + 2) % n]


def choices_five_for_items(items: list[dict], idx: int) -> list[dict]:
    n = len(items)
    indices = five_sector_indices(idx, n)
    choices: list[dict] = []
    for i, wi in enumerate(indices):
        it = items[wi]
        choices.append(
            {
                "choiceIndex": i,
                "wheelIndex": wi,
                "itemId": it.get("id"),
                "title": it.get("wheelLabel") or it.get("name") or f"#{it.get('id')}",
            }
        )
    return choices


def choices_for_items(items: list[dict], idx: int, *, four: bool = False) -> list[dict]:
    n = len(items)
    indices = neighbor_indices(idx, n, span=2 if four else 1)
    choices: list[dict] = []
    for i, wi in enumerate(indices):
        it = items[wi]
        choices.append(
            {
                "choiceIndex": i,
                "wheelIndex": wi,
                "itemId": it.get("id"),
                "title": it.get("wheelLabel") or it.get("name") or f"#{it.get('id')}",
            }
        )
    return choices
