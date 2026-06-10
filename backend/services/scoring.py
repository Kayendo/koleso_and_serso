from __future__ import annotations

import math


def round_hours(value: float) -> float:
    return round(value, 1)


def _hours_ceiled(hltb_hours: float | None, judge_hours: float | None) -> int | None:
    hours = hltb_hours if hltb_hours is not None else judge_hours
    if hours is None:
        return None
    return int(math.ceil(float(hours)))


def _hours_rounded_to_tens(hltb_hours: float | None, judge_hours: float | None) -> int | None:
    """Округление часов до ближайших 10 (14→10, 15→20)."""
    hours = hltb_hours if hltb_hours is not None else judge_hours
    if hours is None:
        return None
    return int(round(float(hours) / 10) * 10)


def _totem_hltb_bonus(rounded_hours: int) -> int:
    """+1 за каждые 10 ч до 50, с 50 ч — +2 за каждые 10 ч."""
    bonus = 0
    for tens in range(10, rounded_hours + 1, 10):
        bonus += 2 if tens >= 50 else 1
    return bonus


def points_for_completion(
    hltb_hours: float | None,
    judge_hours: float | None,
    is_question: bool = False,
) -> int:
    h = _hours_ceiled(hltb_hours, judge_hours)
    if h is None:
        base = 2
    else:
        base = 2 + (h // 10)
        if h >= 50:
            base += 2
    if is_question:
        base = math.ceil(base * 1.5)
    return base


def points_for_totem(
    hltb_hours: float | None,
    judge_hours: float | None,
    is_question: bool = False,
) -> int:
    """Тотем мошны: 3 базовых + бонус за каждые 10 ч HLTB (часы округляются до 10)."""
    rh = _hours_rounded_to_tens(hltb_hours, judge_hours)
    if rh is None:
        pts = 3
    else:
        pts = 3 + _totem_hltb_bonus(rh)
    if is_question:
        pts = math.ceil(pts * 1.5)
    return pts


def points_for_hurry(
    hltb_hours: float | None,
    judge_hours: float | None,
    is_question: bool = False,
) -> int:
    """Торопыга: 1 базовый поинт + бонусы за HLTB (часы округляются вверх)."""
    h = _hours_ceiled(hltb_hours, judge_hours)
    if h is None:
        pts = 1
    else:
        pts = 1 + (h // 10)
        if h >= 5:
            pts += 1
        if h >= 50:
            pts += 2
    if is_question:
        pts = math.ceil(pts * 1.5)
    return pts
