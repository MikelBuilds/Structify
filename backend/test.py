# extraction_service.py
from app.services.extraction_service import extract_text


pdf_path = "test_files/scanned.pdf"

result = extract_text(pdf_path)

print("\nPDF TYPE:")
print(result["pdf_type"])

print("\nMETHOD:")
print(result["method"])

print("\nTEXT:")
print(result["text"][:1000])