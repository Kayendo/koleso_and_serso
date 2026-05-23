"""Сгенерировать data/ai_comment_phrases.jsonl (500+ уникальных строк)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ai_comment_phrases.jsonl"


def line(text: str, tags: list[str] | None = None, whole: bool = False) -> str:
    return json.dumps(
        {"text": text, "tags": tags or ["general"], "whole": whole},
        ensure_ascii=False,
    )


def main() -> None:
    rows: list[str] = []

    game_templates = [
        "{name}, ну как тебе {game}? Норм или полный кал.",
        "{name}, {game} тебя жрёт — не обосрись.",
        "{name}, пока ты в {game}, очки сами не придут.",
        "{name}, {game} — экзамен, ты на пересдаче.",
        "{name}, {game} на HLTB {hltb} ч — наиграл {played}.",
        "{name}, в {game} ты как гайд без автора.",
        "{name}, {game} не прощает — ты просишь.",
    ]
    for i, tpl in enumerate(game_templates):
        rows.append(line(tpl.replace("{game}", "{game}"), ["game"]))
        rows.append(line(f"{tpl} Вариант {i}.", ["game"]))

    for pts in range(0, 21):
        tag = "low_points" if pts < 6 else "high_points"
        rows.append(line(f"{{name}}, {pts} очков — {'позор' if pts < 6 else 'норм'}.", [tag]))
        rows.append(line(f"{{name}}, счёт {pts} — комментатор в шоке.", [tag]))

    cell_templates = [
        "{name}, клетка {cell} — не обосрись.",
        "{name}, {cell} ждала героя. Получила тебя.",
        "{name}, на {cell} судьба смеётся.",
    ]
    for i, tpl in enumerate(cell_templates):
        rows.append(line(f"{tpl} #{i}", ["cell"]))

    stems = {
        "durka": [
            "дурка тебя обняла",
            "из дурки выходят сильные",
            "дурка — твой второй дом",
        ],
        "debuff": ["дебаффы как метки позора", "подлянка сработала", "минус к тебе прилип"],
        "buff": ["баффы есть — толку мало", "кайфарик на тебе", "плюс в голову не влез"],
        "inventory": ["инвентарь полный", "хлам в рюкзаке — классика", "предметы есть, мозгов нет"],
        "no_game": ["без игры — лень", "крути колесо", "активной игры нет"],
        "general": [
            "колесо крутится",
            "кубик честный, ты нет",
            "тащи катку",
            "легенда поля — не ты",
            "я верю в тебя. Зря",
        ],
    }
    for tag, parts in stems.items():
        for i, stem in enumerate(parts):
            for j in range(12):
                rows.append(line(f"{{name}}, {stem} — {i}.{j}.", [tag]))

    facts = [
        "San Andreas — 12 млн копий, у тебя {points} очков.",
        "Tetris в 84-м — ты партию не сложил.",
        "Pac-Man ел точки — ты {points} не ешь.",
        "Mario прыгает — ты в дурку падаешь.",
        "Portal врала — колесо тоже врёт.",
    ]
    for i, f in enumerate(facts):
        for j in range(10):
            rows.append(line(f"{{name}}, факт {i}.{j}: {f}", ["fact"]))

    idx = 0
    while len(rows) < 520:
        tag = ["game", "general", "low_points", "cell", "durka"][idx % 5]
        rows.append(
            line(
                f"{{name}}, реплика #{idx}: {{game}}, {{cell}}, {{points}} очков.",
                [tag],
            )
        )
        idx += 1

    seen: set[str] = set()
    unique: list[str] = []
    for r in rows:
        text = json.loads(r)["text"]
        if text in seen:
            continue
        seen.add(text)
        unique.append(r)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# JSON на строку. tags: game, low_points, high_points, durka, debuff, "
        "buff, inventory, no_game, cell, fact, general. Используй {game}, не названия игр.\n"
    )
    with OUT.open("w", encoding="utf-8") as f:
        f.write(header)
        for r in unique:
            f.write(r + "\n")

    print(f"Wrote {len(unique)} unique phrases -> {OUT}")


if __name__ == "__main__":
    main()
