import pytesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


from pdf2image import convert_from_path


def extract_text_ocr(pdf_path: str) -> str:
    """
    Extract text from scanned PDFs using OCR.
    """

    extracted_text = []

    try:
        images = convert_from_path(
        pdf_path,
        poppler_path=r"D:\poppler\Release-26.02.0-0\poppler-26.02.0\Library\bin"
)

        for page_number, image in enumerate(images, start=1):

            page_text = pytesseract.image_to_string(image)

            extracted_text.append(
                f"\n----- PAGE {page_number} -----\n"
            )

            extracted_text.append(page_text)

        return "\n".join(extracted_text)

    except Exception as e:
        print(f"OCR extraction error: {e}")
        return ""