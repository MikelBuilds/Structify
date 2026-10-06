import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    TESSERACT_PATH = os.getenv("TESSERACT_PATH") or None
    POPPLER_PATH = os.getenv("POPPLER_PATH") or None
    CORS_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",") if origin.strip()]

    def validate(self):
        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be configured")
        if "*" in self.CORS_ORIGINS:
            raise RuntimeError("CORS_ORIGINS must contain explicit origins, not *")


settings = Settings()
