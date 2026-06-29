from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import Document

from fastapi import Depends

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends
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


def process_document(
    document_id: int,
    file_path: str,
    db: Session
):
    try:

        ocr_result = extract_text(file_path)

        structured_data = extract_invoice_data(
            ocr_result["text"]
        )

        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        document.pdf_type = ocr_result["pdf_type"]
        document.processing_method = ocr_result["method"]
        document.raw_text = ocr_result["text"]
        document.structured_json = structured_data
        document.status = "completed"

        db.commit()

    except Exception as e:

        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if document:
            document.status = "failed"
            db.commit()

        print(e)

@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    file_path = UPLOAD_DIR / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(

        filename=file.filename,

        pdf_type="",

        processing_method="",

        status="processing",

        raw_text="",

        structured_json={}
    )

    db.add(document)

    db.commit()

    db.refresh(document)

    background_tasks.add_task(

        process_document,

        document.id,

        str(file_path),

        db

    )

    return {

        "task_id": document.id,

        "status": "processing"

    }


@app.get("/results/{document_id}")
def get_result(
    document_id: int,
    db: Session = Depends(get_db)
):

    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:

        return {

            "message": "Document not found"

        }

    return {

        "status": document.status,

        "structured_data": document.structured_json

    }



app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
