from app.services.pdf_service import extract_text_pdfplumber
from app.services.ocr_service import extract_text_ocr
import logging

logger = logging.getLogger(__name__) 


def extract_text(pdf_path: str) -> dict:

    text = extract_text_pdfplumber(pdf_path)

    if text.strip():

        return {
            "pdf_type": "digital",
            "method": "pdfplumber",
            "text": text
        }

    logger.info("No text layer found. Running OCR...")

    ocr_text = extract_text_ocr(pdf_path)

    if not ocr_text.strip():
        raise ValueError("No text could be extracted from PDF")

    return {
        "pdf_type": "scanned",
        "method": "tesseract",
        "text": ocr_text
    }