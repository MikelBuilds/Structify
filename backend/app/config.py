import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TESSERACT_PATH = os.getenv("TESSERACT_PATH")
    POPPLER_PATH = os.getenv("POPPLER_PATH")
    DATABASE_URL = os.getenv("DATABASE_URL")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads/originals")
    CORS_ORIGINS = [origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",") if origin.strip()]
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

settings = Settings()