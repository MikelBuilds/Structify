import os
from pathlib import Path
from urllib.parse import urlparse

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
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "").strip()
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "").strip()
    R2_ENDPOINT = os.getenv("R2_ENDPOINT", "").strip().rstrip("/") or (
        f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else ""
    )

    def validate_storage(self):
        required = ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
        missing = [key for key in required if not getattr(self, key)]
        if not self.R2_ENDPOINT:
            missing.append("R2_ENDPOINT (or R2_ACCOUNT_ID)")
        if missing:
            raise RuntimeError("Missing storage configuration: " + ", ".join(missing))
        endpoint = urlparse(self.R2_ENDPOINT)
        if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
                or endpoint.password or endpoint.path or endpoint.query or endpoint.fragment):
            raise RuntimeError("R2_ENDPOINT must be an HTTPS origin")

    def validate(self):
        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be configured")
        if "*" in self.CORS_ORIGINS:
            raise RuntimeError("CORS_ORIGINS must contain explicit origins, not *")
        self.validate_storage()


settings = Settings()
