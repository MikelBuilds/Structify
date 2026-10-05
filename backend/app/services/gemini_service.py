import os
import json
import logging

import google.generativeai as genai
from dotenv import load_dotenv
from app.config import settings

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(settings.GEMINI_MODEL)


def extract_invoice_data(text: str):

    prompt = f"""
You are an OCR data extraction assistant.

Extract information from the OCR text.

Correct obvious OCR mistakes only when completely unambiguous.

Examples:
O -> 0
I -> 1
l -> 1
S -> 5

Rules:

- Never hallucinate values.
- If a field is missing, return null.
- Amount must be a number.
- Date must be YYYY-MM-DD.

Return ONLY valid JSON.

OCR TEXT:

{text}
"""

    logger.info("Calling Gemini...")

    response = model.generate_content(prompt, request_options={"timeout": 120})

    logger.debug("Gemini Response: %s", response.text)

    response_text = (
        response.text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(response_text)

    except json.JSONDecodeError:
        logger.exception("Gemini returned invalid JSON.")
        raise ValueError("Gemini returned invalid JSON")