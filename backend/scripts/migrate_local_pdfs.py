"""Optional, rerunnable local PDFs -> R2 migration. Dry-run unless --apply."""
import argparse
from collections import Counter
from pathlib import Path
import sys
from sqlalchemy import update

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database.connection import SessionLocal
from app.database.schema import initialize_database
from app.database.models import Document
from app.services.storage_service import get_storage


def locate_pdf(root, document, filename_counts):
    # Newer local files used IDs; original versions used names (could collide).
    by_id = (root / f"{document.id}.pdf").resolve()
    if by_id.parent == root and by_id.is_file():
        return by_id
    legacy = (root / document.filename).resolve()
    if legacy.parent != root or not legacy.is_file():
        return None
    if filename_counts[document.filename] > 1:
        raise ValueError("Ambiguous duplicate filename; provide an ID-named PDF for each document")
    return legacy


def migrate(root, apply=False):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Upload directory must be a directory")
    if apply:
        initialize_database()
    with SessionLocal() as db:
        # Raw column selection lets dry-run work before the additive schema upgrade.
        rows = db.query(Document.id, Document.filename).all()
        counts = Counter(row.filename for row in rows)
        problems = 0
        for row in rows:
            if apply:
                document = db.get(Document, row.id)
                if document.storage_key:
                    print(f"{row.id}: already linked; skipped")
                    continue
            try:
                path = locate_pdf(root, row, counts)
                if path is None:
                    raise ValueError("Local PDF missing")
                # Stable per-ID key permits retry after upload succeeds but commit fails.
                key = f"documents/legacy/{row.id}/original.pdf"
                if apply:
                    get_storage().upload_pdf(path, key, row.filename)
                    db.execute(update(Document).where(Document.id == document.id).values(
                        storage_key=key, updated_at=document.updated_at
                    ))
                    db.commit()
                print(f"{row.id}: {'migrated' if apply else 'would migrate'}")
            except Exception as error:
                db.rollback()
                problems += 1
                reason = str(error) if isinstance(error, ValueError) else type(error).__name__
                print(f"{row.id}: needs attention ({reason})")
        return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload-dir", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sys.exit(1 if migrate(args.upload_dir, args.apply) else 0)
