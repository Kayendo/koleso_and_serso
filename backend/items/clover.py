"""Четырехлистный клевер — клетки Траллалеро, Лотерея, «?»."""

from __future__ import annotations

from backend.board import BOARD_BY_ID

CLOVER_CELL_TYPES = frozenset({"trallalero", "lottery", "question"})


def clover_cell_label(cell_type: str) -> str:
    return {
        "trallalero": "Траллалеро",
        "lottery": "Лотерея",
        "question": "«?»",
    }.get(cell_type, "")


def is_clover_cell(position: int) -> bool:
    cell = BOARD_BY_ID.get(position)
    return bool(cell and cell.cell_type in CLOVER_CELL_TYPES)
