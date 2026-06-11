import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads" / "avatars"

SECRET_KEY = os.environ.get("SECRET_KEY", "kolesoblya-dev-change-me")

# Истинный рандом: random.org (атмосферный шум), опционально API-ключ для большего лимита
RANDOM_ORG_API_KEY = os.environ.get("RANDOM_ORG_API_KEY", "")
TRUE_RANDOM_ENABLED = os.environ.get("TRUE_RANDOM_ENABLED", "1") not in ("0", "false", "no")
TRUE_RANDOM_TIMEOUT = float(os.environ.get("TRUE_RANDOM_TIMEOUT", "4"))
TENOR_API_KEY = os.environ.get("TENOR_API_KEY", "LIVDSRZULELA")
TENOR_CLIENT_KEY = os.environ.get("TENOR_CLIENT_KEY", "kolesoblya")

# Озвучка Edge TTS — см. data/ai_tts_characters.json и GET /api/ai/voices
AI_TTS_VOICE = os.environ.get("AI_TTS_VOICE", "random")
DATABASE_URI = os.environ.get(
    "DATABASE_URI", f"sqlite:///{BASE_DIR / 'kolesoblya.db'}"
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

GENRE_FILES = {
    1: DATA_DIR / "genre_1_puzzle.txt",
    2: DATA_DIR / "genre_2_shooter.txt",
    3: DATA_DIR / "genre_3_action.txt",
    4: DATA_DIR / "genre_4_adventure.txt",
    5: DATA_DIR / "genre_5_platformer.txt",
    6: DATA_DIR / "genre_6_simulator.txt",
    7: DATA_DIR / "genre_7_horror.txt",
    8: DATA_DIR / "genre_8_rpg.txt",
    9: DATA_DIR / "genre_9_strategy.txt",
}

QUESTION_FILE = DATA_DIR / "games_question.txt"
TRALLALERO_FILE = DATA_DIR / "games_trallalero.txt"

WHEEL_SPIN_SECONDS = 30
PASS_START_POINTS = 5
DROP_PENALTY = 2
from backend.board import (
    DURKA_CELL_ID,
    LOTTERY_CELL_ID,
    START_CELL_ID,
    TRALLALERO_CELL_ID,
)
