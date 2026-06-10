"""Каталог предметов из data/items.txt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.config import BASE_DIR

DATA_FILE = BASE_DIR / "data" / "items.txt"

_catalog_cache: dict[int, "ItemDef"] | None = None


@dataclass(frozen=True)
class ItemDef:
    id: int
    kind: str  # item | none | trap
    polarity: str  # buff | debuff
    instant: bool
    duration_turns: int
    name: str
    flavor: str
    description: str
    effect: str

    @property
    def wheel_label(self) -> str:
        tag = "▲" if self.polarity == "buff" else "▼"
        return f"#{self.id} {tag} {self.name}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "polarity": self.polarity,
            "instant": self.instant,
            "durationTurns": self.duration_turns,
            "name": self.name,
            "flavor": self.flavor,
            "description": self.description,
            "effect": self.effect,
            "wheelLabel": self.wheel_label,
        }


def _parse_bool(val: str) -> bool:
    v = (val or "").strip().lower()
    return v in ("1", "true", "yes", "да", "y")


def _parse_row(parts: list[str]) -> ItemDef | None:
    if len(parts) < 7:
        return None
    try:
        iid = int(parts[0].strip())
    except ValueError:
        return None
    if len(parts) >= 9:
        flavor = (parts[6] or "").strip()
        description = (parts[7] or "").strip()
        effect = (parts[8] if len(parts) > 8 else "").strip()
    else:
        flavor = ""
        description = (parts[6] or "").strip()
        effect = (parts[7] if len(parts) > 7 else "").strip()
    return ItemDef(
        id=iid,
        kind=(parts[1] or "item").strip().lower(),
        polarity=(parts[2] or "buff").strip().lower(),
        instant=_parse_bool(parts[3]),
        duration_turns=int(parts[4].strip() or "0"),
        name=(parts[5] or f"Предмет {iid}").strip(),
        flavor=flavor,
        description=description,
        effect=effect,
    )


def load_catalog(force: bool = False) -> dict[int, ItemDef]:
    global _catalog_cache
    if force:
        _catalog_cache = None
    if _catalog_cache is not None and not force:
        return _catalog_cache

    items: dict[int, ItemDef] = {}
    if not DATA_FILE.exists():
        _catalog_cache = items
        return items

    for raw in DATA_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("id\t") or line.lower().startswith("id,"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = [p.strip() for p in line.split("|")]
        item = _parse_row(parts)
        if item:
            items[item.id] = item

    _catalog_cache = items
    return items


def get_item(item_id: int) -> ItemDef | None:
    return load_catalog().get(int(item_id))


def all_items() -> list[ItemDef]:
    return sorted(load_catalog().values(), key=lambda x: x.id)


def wheel_pool(*, polarity: str | None = None) -> list[ItemDef]:
    pool = [i for i in all_items() if i.name]
    if polarity in ("buff", "debuff"):
        pool = [i for i in pool if i.polarity == polarity]
    return pool
