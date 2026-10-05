from contextlib import asynccontextmanager
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore

from botocore.exceptions import ClientError
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import engine, get_db, SessionLocal
from app.database.schema import initialize_database, mark_interrupted
from app.crud.document_crud import (
    create_document, get_document, update_document, mark_failed, get_all_documents,
)
from app.services.extraction_service import extract_text
from app.services.gemini_service import extract_invoice_data
from app.services.storage_service import get_storage, new_storage_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
# Only one OCR job at a time within the single worker's small memory budget.
processing_slot = BoundedSemaphore(1)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@asynccontextmanager
async def lifespan(app):
    settings.validate()
    try:
        initialize_database()
        with SessionLocal() as db:
            mark_interrupted(db)
    except Exception:
        raise RuntimeError("Unable to initialize PostgreSQL. Check DATABASE_URL, SSL, connectivity and schema permissions.") from None
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}


def process_document(document_id: int, storage_key: str):
    stage = "PDF download"
    try:
        with processing_slot, TemporaryDirectory(prefix="structify-ocr-") as directory:
            file_path = Path(directory) / "original.pdf"
            get_storage().download_pdf(storage_key, file_path)
            stage = "Text extraction"
            ocr_result = extract_text(str(file_path))
            stage = "Gemini processing"
            structured_data = extract_invoice_data(ocr_result["text"])
            stage = "Saving results"
            with SessionLocal() as db:
                document = get_document(db, document_id)
                if document:
                    update_document(db, document, ocr_result, structured_data)
    except Exception as error:
        # Store a useful stage/type, not a provider exception that may contain secrets.
        message = f"{stage} failed ({type(error).__name__}). Please try again."
        logger.error("Document %s: %s", document_id, message)
        try:
            with SessionLocal() as db:
                document = get_document(db, document_id)
                if document:
                    mark_failed(db, document, message)
        except Exception:
            logger.error("Could not persist failure for document %s", document_id)
        # TemporaryDirectory removes local files even on processing/DB failure.


@app.post("/upload")
def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...),
               db: Session = Depends(get_db)):
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    # Sync route runs in FastAPI's threadpool; R2/DB/file I/O do not block the event loop.
    with TemporaryDirectory(prefix="structify-upload-") as directory:
        file_path = Path(directory) / "original.pdf"
        with file_path.open("wb") as target:
            size = 0
            while chunk := file.file.read(1024 * 1024):
                if size == 0 and not chunk.startswith(b"%PDF-"):
                    raise HTTPException(status_code=400, detail="File is not a valid PDF.")
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Maximum file size is 20 MB.")
                target.write(chunk)
            if size == 0:
                raise HTTPException(status_code=400, detail="File is not a valid PDF.")
        key = new_storage_key(filename)
        document = create_document(db, filename, key)
        try:
            get_storage().upload_pdf(file_path, key, filename)
        except Exception as error:
            mark_failed(db, document, f"PDF storage failed ({type(error).__name__}). Please upload again.")
            raise HTTPException(status_code=502, detail="Unable to store PDF in R2. Please try again.") from None
    # Pass only durable identifiers. Background work obtains its own temporary copy.
    background_tasks.add_task(process_document, document.id, key)
    return {"message": "Document uploaded successfully", "task_id": document.id, "status": "processing"}


@app.get("/results/{document_id}")
def get_result(document_id: int, db: Session = Depends(get_db)):
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"id": document.id, "filename": document.filename, "status": document.status,
            "created_at": document.created_at, "structured_data": document.structured_json,
            "error_message": document.error_message, "updated_at": document.updated_at}


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return get_all_documents(db)


@app.get("/pdf/{document_id}")
def serve_pdf(document_id: int, db: Session = Depends(get_db)):
    document = get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.storage_key:
        raise HTTPException(status_code=404, detail="Original PDF has not been migrated to R2")
    try:
        url = get_storage().signed_pdf_url(document.storage_key, document.filename)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            raise HTTPException(status_code=404, detail="PDF not found in storage") from None
        raise HTTPException(status_code=502, detail="PDF storage is unavailable") from None
    except Exception:
        raise HTTPException(status_code=502, detail="PDF storage is unavailable") from None
    return RedirectResponse(url, status_code=307, headers={"Cache-Control": "no-store"})
