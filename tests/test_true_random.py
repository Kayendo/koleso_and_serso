"""Тесты внешнего истинного рандома."""

from unittest.mock import patch

import pytest

from backend.services import true_random as tr


def test_randbelow_uses_random_org_plain():
    with patch.object(tr, "_fetch_random_org_json", return_value=None):
        with patch.object(tr, "_fetch_random_org_plain", return_value=[3]):
            assert tr.randbelow(12) == 3
            assert tr.last_random_source() == "random.org (атмосферный шум)"


def test_randint_falls_back_to_secrets():
    with patch.object(tr, "fetch_integers", return_value=None):
        with patch("backend.services.true_random.secrets.randbelow", return_value=4):
            assert tr.randint(1, 6) == 5
            assert tr.last_random_source() == "secrets (OS CSPRNG)"


def test_fetch_integers_disabled():
    with patch("backend.services.true_random.TRUE_RANDOM_ENABLED", False):
        assert tr.fetch_integers(2, 1, 6) is None


def test_roll_dice_batch():
    from backend.services.turn_service import roll_dice

    with patch("backend.services.true_random.fetch_integers", return_value=[2, 5]):
        a, b, label = roll_dice()
        assert (a, b, label) == (2, 5, "2+5")
