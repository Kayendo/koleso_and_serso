"""Криптографически стойкий рандом для кубиков и колеса (+ внешние источники)."""

from __future__ import annotations

from backend.services.true_random import (
    choice,
    randbelow,
    randint,
    random_meta,
    sample,
    shuffle,
)

__all__ = [
    "choice",
    "randbelow",
    "randint",
    "random_meta",
    "sample",
    "shuffle",
]
