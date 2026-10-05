"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from backend/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Also try backend-local .env
    _env_local = Path(__file__).resolve().parent.parent / ".env"
    if _env_local.exists():
        load_dotenv(_env_local)


class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    LLM_MAX_OUTPUT_TOKENS: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "800"))
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    ]
    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "8"))

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY) and bool(self.GEMINI_MODEL)


settings = Settings()
