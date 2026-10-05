"""Small, additive upgrade for the existing demo schema; never drops data."""
from sqlalchemy import text, update
from app.database.connection import Base, engine
from app.database.models import Document


def initialize_database():
    with engine.begin() as connection:
        Base.metadata.create_all(bind=connection)
        # create_all does not add columns to an existing table.
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_key TEXT"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"))
        connection.execute(text("UPDATE documents SET updated_at = COALESCE(created_at, NOW()) WHERE updated_at IS NULL"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN updated_at SET DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE documents ALTER COLUMN updated_at SET NOT NULL"))


def mark_interrupted(db):
    db.execute(update(Document).where(Document.status == "processing").values(
        status="failed", error_message="Processing interrupted by a server restart. Please upload again."
    ))
    db.commit()
