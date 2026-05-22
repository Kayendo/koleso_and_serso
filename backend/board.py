"""Поле 1:1 по макету: 40 клеток по часовой стрелке от Старта (нижний левый угол)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CellType = Literal[
    "start",
    "durka",
    "trallalero",
    "lottery",
    "company",
    "trap_joy",
    "question",
]

# id углов (для конфига)
START_CELL_ID = 0
LOTTERY_CELL_ID = 10
TRALLALERO_CELL_ID = 20
DURKA_CELL_ID = 30


@dataclass(frozen=True)
class BoardCell:
    id: int
    name: str
    cell_type: CellType
    genre_id: int | None = None
    company_key: str | None = None
    color_group: str | None = None
    genre_label: str | None = None


GENRE_LABELS = {
    1: "Puzzle / Point & Click / Quest / Walking sim",
    2: "Шутер FPS / TPS",
    3: "Action / Slasher / Roguelike / Soulslike",
    4: "Action Adventure / Interactive Drama",
    5: "Platformer / Metroidvania",
    6: "Racing / Sport / Simulator / Survival",
    7: "Horror / Survival Horror",
    8: "RPG / CRPG / ARPG / JRPG",
    9: "Strategy / 4X / RTS",
}

COMPANIES = {
    "kalawar": (1, "Kalawar"),
    "three_dp": (1, "THREE-DP"),
    "yea_games": (1, "YEA GAMES"),
    "dydoce": (2, "DYDOCE"),
    "big_dish": (2, "BIG DISH"),
    "deactivision": (2, "Deactivision"),
    "pornstar": (3, "Pornstar Games"),
    "naughty_boy": (3, "Naughty boy"),
    "porosad": (3, "PoroSad Studio"),
    "siga": (4, "SIGA"),
    "cumcom": (4, "CUMCOM"),
    "team_plum": (4, "Team Plum"),
    "team_vegan": (5, "Team Vegan"),
    "red_head": (5, "Red Head"),
    "legko": (5, "LEGKO"),
    "microguy": (6, "Microguy Games"),
    "noproofs": (6, "Noproofs games"),
    "bondage_nyamca": (6, "Bondage Nyamca"),
    "leather_club": (7, "Leather club door"),
    "vlomve": (7, "Vlomve"),
    "kawaimi": (7, "Kawaimi"),
    "besedka": (8, "Besedka"),
    "squidwardix": (8, "Squidwardix"),
    "dvd_bred": (8, "DVD PROJECT BRED"),
    "chelic": (9, "Chelic Entertainment"),
    "kunisoft": (9, "Kunisoft"),
    "piratix": (9, "Piratix Games"),
    "blazerd": (None, "Blazerd"),
}


def _c(cid: int, key: str, color: str) -> BoardCell:
    gid, name = COMPANIES[key]
    return BoardCell(
        id=cid,
        name=name,
        cell_type="company",
        genre_id=gid,
        company_key=key,
        color_group=color,
        genre_label=GENRE_LABELS.get(gid) if gid else "Рандом 1–9",
    )


def _sp(cid: int, name: str, ctype: CellType, color: str, label: str) -> BoardCell:
    return BoardCell(
        id=cid,
        name=name,
        cell_type=ctype,
        color_group=color,
        genre_label=label,
    )


# 0 Старт → низ → 10 Лотерея → правый борт → 20 Траллалеро → верх → 30 Дурка → левый борт
BOARD: list[BoardCell] = [
    _sp(0, "Старт", "start", "start", "Старт (+5 очков)"),
    # Низ (1–9)
    _c(1, "legko", "orange"),
    _c(2, "team_plum", "red"),
    _c(3, "kalawar", "blue"),
    _c(4, "three_dp", "yellow"),
    _sp(5, "?", "question", "question", "Сложные игры ×1.5"),
    _c(6, "dydoce", "gray"),
    _c(7, "big_dish", "yellow"),
    _sp(8, "Подлянка / Кайфарик", "trap_joy", "trap", "Особое"),
    _c(9, "noproofs", "orange"),
    _sp(10, "777 Лотерея", "lottery", "lottery", "Steam (Game Gauntlet)"),
    # Правый борт (11–19), снизу вверх
    _c(11, "porosad", "cyan"),
    _c(12, "red_head", "red"),
    _c(13, "yea_games", "blue"),
    _c(14, "chelic", "yellow"),
    _sp(15, "?", "question", "question", "Сложные игры ×1.5"),
    _c(16, "kawaimi", "red"),
    _c(17, "deactivision", "pink"),
    _sp(18, "Подлянка / Кайфарик", "trap_joy", "trap", "Особое"),
    _c(19, "leather_club", "gray"),
    _sp(20, "Траллалеро траллала", "trallalero", "trallalero", "Особый список"),
    # Верх (21–29), справа налево
    _c(21, "bondage_nyamca", "red"),
    _sp(22, "Подлянка / Кайфарик", "trap_joy", "trap", "Особое"),
    BoardCell(
        23,
        "Blazerd",
        "company",
        genre_id=None,
        company_key="blazerd",
        color_group="blue",
        genre_label="Рандом жанра 1–9",
    ),
    _c(24, "squidwardix", "gray"),
    _sp(25, "?", "question", "question", "Сложные игры ×1.5"),
    _c(26, "dvd_bred", "red"),
    _c(27, "naughty_boy", "red"),
    _c(28, "cumcom", "yellow"),
    _c(29, "siga", "blue"),
    _sp(30, "Дурка", "durka", "durka", "Дроп / штраф"),
    # Левый борт (31–39), сверху вниз
    _c(31, "piratix", "blue"),
    _c(32, "vlomve", "red"),
    _c(33, "besedka", "gray"),
    _c(34, "pornstar", "green"),
    _sp(35, "?", "question", "question", "Сложные игры ×1.5"),
    _c(36, "microguy", "red"),
    _c(37, "kunisoft", "pink"),
    _sp(38, "Подлянка / Кайфарик", "trap_joy", "trap", "Особое"),
    _c(39, "team_vegan", "yellow"),
]

BOARD_BY_ID = {c.id: c for c in BOARD}
BOARD_SIZE = len(BOARD)


def cell_to_dict(cell: BoardCell) -> dict:
    return {
        "id": cell.id,
        "name": cell.name,
        "type": cell.cell_type,
        "genreId": cell.genre_id,
        "companyKey": cell.company_key,
        "colorGroup": cell.color_group,
        "genreLabel": cell.genre_label,
    }


def get_board_json() -> list[dict]:
    return [cell_to_dict(c) for c in BOARD]


def resolve_genre_for_cell(cell_id: int) -> int | None:
    cell = BOARD_BY_ID[cell_id]
    if cell.cell_type == "company" and cell.company_key != "blazerd":
        return cell.genre_id
    return None
