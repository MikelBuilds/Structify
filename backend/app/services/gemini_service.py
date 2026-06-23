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
You are an invoice extraction system.

Extract:

- invoice_number
- invoice_date
- customer_name
- amount

Return ONLY valid JSON.

Invoice Text:

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

