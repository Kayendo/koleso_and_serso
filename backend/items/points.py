"""Начисление очков с учётом slave (fisting) и журналом."""

from __future__ import annotations

from backend.items.modifiers import _has_mod
from backend.models import User, db


def _log_fisting_gain(owner: User, victim: User, taken: int, factors: list[str]) -> None:
    from backend.items.inventory import log_turn

    log_turn(
        owner.id,
        summary=f"«Рука для fisting»: +{taken} очк. от {victim.username}",
        factors=list(factors) + [f"Начислено: +{taken} очк."],
        extra={
            "fisting": True,
            "fromUserId": victim.id,
            "fromUsername": victim.username,
            "pointsTaken": taken,
            "points": taken,
        },
    )


def grant_points(
    user: User,
    amount: int,
    factors: list[str],
) -> int:
    """
    Добавить очки игроку. Каждый 5-й очко при «Руке для fisting» уходит владельцу.
    Возвращает сколько очков осталось у игрока.
    """
    if amount <= 0:
        return 0

    kept = amount
    slave = _has_mod(user.id, "slave")
    if slave:
        owner = db.session.get(User, int(slave.effect_value or "0"))
        if owner:
            bank = int(slave.description or "0")
            pool = bank + amount
            taken = 0
            while pool >= 5 and slave.turns_remaining > 0:
                pool -= 5
                slave.turns_remaining -= 1
                taken += 1
                owner.points += 1
            slave.description = str(pool)
            if taken:
                msg = f"«Рука для fisting»: {taken} очк. → {owner.username}"
                factors.append(msg)
                _log_fisting_gain(owner, user, taken, [msg])
            if slave.turns_remaining <= 0:
                db.session.delete(slave)
            kept = max(0, amount - taken)

    user.points += kept
    db.session.commit()
    return kept
