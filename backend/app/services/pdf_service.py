import pdfplumber


def extract_text_pdfplumber(pdf_path: str) -> str:
    """
    Extract text from a digital PDF using pdfplumber.
    Returns empty string if no text is found.
    """

    extracted_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    extracted_text.append(page_text)

        return "\n".join(extracted_text)

    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""