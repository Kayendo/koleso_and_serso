from __future__ import annotations

from pathlib import Path

from backend.random_utils import choice, randint, sample

from backend.config import GENRE_FILES, QUESTION_FILE, TRALLALERO_FILE


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def games_for_genre(genre_id: int) -> list[str]:
    path = GENRE_FILES.get(genre_id)
    if not path:
        return []
    return _read_lines(path)


def question_games() -> list[str]:
    return _read_lines(QUESTION_FILE)


def trallalero_games() -> list[str]:
    return _read_lines(TRALLALERO_FILE)


def pick_random(games: list[str], count: int = 1) -> list[str]:
    if not games:
        return []
    if count >= len(games):
        return sample(games, len(games))
    return sample(games, count)


def wheel_games(genre_id: int, count: int = 12) -> list[str]:
    pool = games_for_genre(genre_id)
    if len(pool) <= count:
        return pick_random(pool, len(pool)) if pool else []
    return pick_random(pool, count)


def pick_one_for_cell(cell_type: str, genre_id: int | None) -> str | None:
    if cell_type == "question":
        pool = question_games()
    elif cell_type == "trallalero":
        pool = trallalero_games()
    elif genre_id:
        pool = games_for_genre(genre_id)
    else:
        return None
    if not pool:
        return None
    return choice(pool)


def blazerd_genre_roll() -> int:
    return randint(1, 9)
