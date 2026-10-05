import json
import logging
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)


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

    with genai.Client(api_key=settings.GEMINI_API_KEY,
                      http_options=types.HttpOptions(timeout=120_000)) as client:
        response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
    if not response.text:
        raise ValueError("Gemini returned no text")


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