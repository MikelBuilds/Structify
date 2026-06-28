from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil

from app.services.extraction_service import extract_text
from app.services.gemini_service import extract_invoice_data

from app.config import settings

from app.database.connection import Base, engine
from app.database import models


app = FastAPI()

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = Path("uploads/originals")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    file_path = UPLOAD_DIR / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ocr_result = extract_text(str(file_path))

    print("\n===== OCR RESULT =====")
    print(ocr_result)

    structured_data = extract_invoice_data(
        ocr_result["text"]
    )

    print("\n===== FINAL STRUCTURED DATA =====")
    print(structured_data)

    return {
        "message": "File processed successfully",
        "filename": file.filename,
        "pdf_type": ocr_result["pdf_type"],
        "method": ocr_result["method"],
        "structured_data": structured_data
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
