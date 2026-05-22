"""Проверки фаз хода — нельзя перескакивать шаги."""

from backend.models import User


def require_phase(user: User, *allowed: str) -> str | None:
    if not user.is_player:
        return "Админ не участвует в игре"
    if user.turn_phase not in allowed:
        labels = {
            "idle": "ожидание хода",
            "dice_choice": "выбор кубиков",
            "rolling": "бросок кубика / движение",
            "wheel_ready": "готовность к колесу",
            "wheel": "колесо",
            "playing": "прохождение игры",
            "reward_items": "награда — колёса предметов",
            "durka": "дурка",
        }
        cur = labels.get(user.turn_phase, user.turn_phase)
        return f"Сейчас этап «{cur}». Действие недоступно."
    return None
