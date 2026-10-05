import logging
from tempfile import TemporaryDirectory

import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from app.config import settings

if settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

logger = logging.getLogger(__name__)


def extract_text_ocr(pdf_path: str) -> str:
    """Render one page at a time, keeping the free instance's memory bounded."""
    info = pdfinfo_from_path(pdf_path, poppler_path=settings.POPPLER_PATH, timeout=30)
    pages = int(info["Pages"])
    if pages < 1:
        raise ValueError("No pages found in PDF")
    extracted_text = []
    for number in range(1, pages + 1):
        with TemporaryDirectory(prefix="structify-page-") as directory:
            paths = convert_from_path(
                pdf_path, poppler_path=settings.POPPLER_PATH, first_page=number,
                last_page=number, output_folder=directory, paths_only=True,
                thread_count=1, timeout=60, size=2500,
            )
            if not paths:
                raise ValueError("Unable to render PDF page")
            with Image.open(paths[0]) as image:
                page_text = pytesseract.image_to_string(image, timeout=60)
            if page_text.strip():
                extracted_text.append(f"\n----- PAGE {number} -----\n{page_text}")
    return "\n".join(extracted_text)
