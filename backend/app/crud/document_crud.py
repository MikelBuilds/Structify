from sqlalchemy.orm import Session

from app.database.models import Document


def create_document(db: Session, filename: str):

    document = Document(
        filename=filename,
        pdf_type="",
        processing_method="",
        status="processing",
        raw_text="",
        structured_json={}
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_document(db: Session, document_id: int):

    return (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )


def update_document(
    db: Session,
    document: Document,
    ocr_result,
    structured_data
):

    document.pdf_type = ocr_result["pdf_type"]
    document.processing_method = ocr_result["method"]
    document.raw_text = ocr_result["text"]
    document.structured_json = structured_data
    document.status = "completed"
    document.error_message = None

    db.commit()


def mark_failed(db: Session, document: Document, message: str):

    document.status = "failed"
    document.error_message = message

    db.commit()


def get_all_documents(db: Session):

    return (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .all()
    )