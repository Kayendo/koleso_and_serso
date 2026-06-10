"""Очки за прохождение и «Торопыга»."""

from backend.services.scoring import points_for_completion, points_for_hurry


def test_completion_15_9_hours():
    assert points_for_completion(15.9, None) == 3


def test_hurry_15_9_hours():
    assert points_for_hurry(15.9, None) == 3


def test_hurry_only_base_without_hltb():
    assert points_for_hurry(None, None) == 1


def test_hurry_5_hours():
    assert points_for_hurry(5.0, None) == 2


def test_hurry_4_hours():
    assert points_for_hurry(4.1, None) == 2  # ceil → 5 ч
    assert points_for_hurry(4.0, None) == 1


def test_hurry_question_multiplier():
    assert points_for_hurry(15.9, None, is_question=True) == 5
