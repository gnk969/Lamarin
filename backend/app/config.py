"""Pengaturan dari environment variable (lihat .env.example)."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_TIMEOUT = float(os.environ.get("GEMINI_TIMEOUT", "40"))
AI_ENABLED = os.environ.get("RAMBU_AI", "on").lower() != "off"
RATE_PER_MINUTE = int(os.environ.get("RAMBU_RATE", "20"))
MAX_TEXT_CHARS = 6000
MAX_IMAGE_BYTES = 4 * 1024 * 1024


def ai_available() -> bool:
    return AI_ENABLED and bool(GEMINI_API_KEY)
