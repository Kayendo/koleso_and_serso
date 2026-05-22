"""Криптографически стойкий рандом для кубиков и колеса."""

from __future__ import annotations

import secrets


def randint(a: int, b: int) -> int:
    return secrets.randbelow(b - a + 1) + a


def randbelow(n: int) -> int:
    return secrets.randbelow(n)


def choice(seq):
    return seq[secrets.randbelow(len(seq))]


def sample(seq, k: int):
    items = list(seq)
    if k >= len(items):
        return secrets.SystemRandom().sample(items, len(items))
    return secrets.SystemRandom().sample(items, k)


def shuffle(seq):
    items = list(seq)
    secrets.SystemRandom().shuffle(items)
    return items
