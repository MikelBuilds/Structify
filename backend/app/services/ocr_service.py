import pytesseract
from app.config import settings
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH


def extract_text_ocr(pdf_path: str) -> str:

    extracted_text = []

    try:
        print("OCR Started")

        images = convert_from_path(
            pdf_path,
            poppler_path=settings.POPPLER_PATH
        )

        if len(images) == 0:
            print("No images generated!")
            return ""

        print("Saving debug image...")

        images[0].save("debug.png")

        print("Debug image saved!")

        for page_number, image in enumerate(images, start=1):

            page_text = pytesseract.image_to_string(image)

            print(page_text)

            extracted_text.append(
                f"\n----- PAGE {page_number} -----\n"
            )

            extracted_text.append(page_text)

        return "\n".join(extracted_text)

    except Exception as e:
        print("OCR ERROR:")
        print(e)
        return ""