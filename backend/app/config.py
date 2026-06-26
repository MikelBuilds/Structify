import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TESSERACT_PATH = os.getenv("TESSERACT_PATH")
    POPPLER_PATH = os.getenv("POPPLER_PATH")
    DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()