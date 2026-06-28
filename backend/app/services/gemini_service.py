import os
import json
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")



def extract_invoice_data(text):

    prompt = f"""
You are an OCR data extraction assistant. Extract fields from the text below, correcting obvious OCR errors (O→0, l→1, I→1, S→5, etc.) only when unambiguous.

Extract these fields:
- invoice_number (string)
- invoice_date (YYYY-MM-DD)
- customer_name (string)
- amount (number, grand total, no symbols)

Rules:
- Set missing or uncertain fields to null
- Never hallucinate values
- Return ONLY valid JSON, no explanation

{{
  "invoice_number": ...,
  "invoice_date": ...,
  "customer_name": ...,
  "amount": ...
}}

{text}
"""

    print("\n===== CALLING GEMINI =====")

    response = model.generate_content(prompt)

    print("\n===== RAW GEMINI RESPONSE =====")
    print(response.text)

    response_text = (
        response.text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    return json.loads(response_text)

