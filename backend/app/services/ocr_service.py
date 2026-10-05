import logging

import pytesseract
from pdf2image import convert_from_path

from app.config import settings

if settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

logger = logging.getLogger(__name__)


def extract_text_ocr(pdf_path: str) -> str:
    """
    Extract text from scanned PDFs using OCR.
    """

    extracted_text = []

    try:
        logger.info("OCR Started")

        images = convert_from_path(
            pdf_path,
            poppler_path=settings.POPPLER_PATH
        )

        if len(images) == 0:
            logger.warning("No images generated from PDF.")
            raise ValueError("No pages found in PDF")

        for page_number, image in enumerate(images, start=1):

            page_text = pytesseract.image_to_string(image)

            logger.debug(page_text)

            extracted_text.append(
                f"\n----- PAGE {page_number} -----\n"
            )

            extracted_text.append(page_text)

        return "\n".join(extracted_text)

    except Exception:
        logger.exception("OCR extraction failed.")
        raise