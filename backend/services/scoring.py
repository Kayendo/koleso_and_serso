from __future__ import annotations

import math


def round_hours(value: float) -> float:
    return round(value, 1)


def points_for_completion(
    hltb_hours: float | None,
    judge_hours: float | None,
    is_question: bool = False,
) -> int:
    hours = hltb_hours if hltb_hours is not None else judge_hours
    if hours is None:
        base = 2
    else:
        h = round_hours(hours)
        base = 2 + int(h // 10)
        if h >= 50:
            base += 2
    if is_question:
        base = math.ceil(base * 1.5)
    return base
