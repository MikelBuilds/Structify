from fastapi import (
    FastAPI,
    UploadFile,
    File,
    BackgroundTasks,
    Depends,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
import shutil

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


app = FastAPI()

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = Path("uploads/originals")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

        document = get_document(
            db,
            document_id
        )

        if document:
            mark_failed(
                db,
                document
            )

        print(e)

    finally:

        db.close()


@app.post("/upload")
async def upload_pdf(

    background_tasks: BackgroundTasks,

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    content = await file.read()

    if len(content) > 20 * 1024 * 1024:

        raise HTTPException(
            status_code=400,
            detail="Maximum file size is 20 MB."
        )

    file.file.seek(0)

    file_path = UPLOAD_DIR / file.filename

    with open(file_path, "wb") as buffer:

        shutil.copyfileobj(file.file, buffer)

    document = create_document(
        db,
        file.filename
    )

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


app.add_middleware(

    CORSMiddleware,

    allow_origins=["http://localhost:5173"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)