from fastapi import (
    FastAPI,
    UploadFile,
    File,
    BackgroundTasks,
    Depends,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.config import settings

from sqlalchemy.orm import Session

from app.database.connection import (
    Base,
    engine,
    get_db,
    SessionLocal,
)

from app.crud.document_crud import (
    create_document,
    get_document,
    update_document,
    mark_failed,
    get_all_documents,
)

from app.services.extraction_service import extract_text
from app.services.gemini_service import extract_invoice_data

import logging


logger = logging.getLogger(__name__)

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s %(levelname)s %(name)s : %(message)s"

)


UPLOAD_DIR = Path(settings.UPLOAD_DIR).resolve()


@asynccontextmanager
async def lifespan(app):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY must be configured")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # This deployment uses one worker; interrupted in-process tasks cannot resume.
    with SessionLocal() as db:
        db.execute(text("UPDATE documents SET status = 'failed' WHERE status = 'processing'"))
        db.commit()
    yield
    engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok"}


def process_document(
    document_id: int,
    file_path: str,
):

    db = SessionLocal()

    try:

        ocr_result = extract_text(file_path)

        structured_data = extract_invoice_data(
            ocr_result["text"]
        )

        document = get_document(
            db,
            document_id
        )

        if not document:
            return

        update_document(
            db,
            document,
            ocr_result,
            structured_data
        )

    except Exception as e:

        db.rollback()
        document = get_document(
            db,
            document_id
        )

        if document:
            mark_failed(
                db,
                document
            )

        logger.exception(e)

    finally:

        db.close()


@app.post("/upload")
async def upload_pdf(

    background_tasks: BackgroundTasks,

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Bound memory use even when Content-Length is absent or incorrect.
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum file size is 20 MB.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF.")

    document = create_document(db, filename)
    file_path = UPLOAD_DIR / f"{document.id}.pdf"
    try:
        file_path.write_bytes(content)
    except Exception:
        mark_failed(db, document)
        raise HTTPException(status_code=500, detail="Unable to store PDF")

    background_tasks.add_task(
        process_document,
        document.id,
        str(file_path)
    )

    return {

        "message": "Document uploaded successfully",

        "task_id": document.id,

        "status": "processing"

    }


@app.get("/results/{document_id}")
def get_result(

    document_id: int,

    db: Session = Depends(get_db)

):

    document = get_document(
        db,
        document_id
    )

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return {

        "id": document.id,

        "filename": document.filename,

        "status": document.status,

        "created_at": document.created_at,

        "structured_data": document.structured_json

    }


@app.get("/documents")
def list_documents(

    db: Session = Depends(get_db)

):

    return get_all_documents(db)


@app.get("/pdf/{document_id}")
def serve_pdf(

    document_id: int,

    db: Session = Depends(get_db)

):

    document = get_document(db, document_id)

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    file_path = UPLOAD_DIR / f"{document.id}.pdf"
    if not file_path.exists():
        # Support existing uploads without allowing paths outside the upload folder.
        legacy_path = (UPLOAD_DIR / document.filename).resolve()
        if legacy_path.parent == UPLOAD_DIR:
            file_path = legacy_path

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="PDF file not found on disk"
        )

    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        filename=document.filename,
        content_disposition_type="inline"
    )


app.add_middleware(

    CORSMiddleware,

    allow_origins=settings.CORS_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)