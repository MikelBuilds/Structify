from app.services.pdf_service import extract_text_pdfplumber
from app.services.ocr_service import extract_text_ocr


def extract_text(pdf_path: str) -> dict:
    """
    Detect PDF type automatically.

    1. Try pdfplumber
    2. If text exists -> Digital PDF
    3. Else -> OCR fallback
    """

    text = extract_text_pdfplumber(pdf_path)

    if text.strip():

        return {
            "pdf_type": "digital",
            "method": "pdfplumber",
            "text": text
        }

    print("No text layer found. Running OCR...")

    ocr_text = extract_text_ocr(pdf_path)

    return {
        "pdf_type": "scanned",
        "method": "tesseract",
        "text": ocr_text
    }