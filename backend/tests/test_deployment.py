import asyncio
from contextlib import ExitStack
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

# Never connect to developer services or use their credentials.
os.environ.update(CORS_ORIGINS="http://localhost:5173", DATABASE_URL="postgresql://test:test@localhost/test", GEMINI_API_KEY="test",
                  R2_ACCOUNT_ID="test", R2_ACCESS_KEY_ID="test", R2_SECRET_ACCESS_KEY="test",
                  R2_BUCKET_NAME="test", R2_ENDPOINT="https://test.r2.cloudflarestorage.com")

from botocore.exceptions import ClientError
from botocore.stub import Stubber, ANY
from urllib.parse import urlparse, parse_qs
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

import main
from app.config import Settings
from app.crud.document_crud import create_document, get_document, get_all_documents, update_document, mark_failed
from app.database.connection import Base, database_url
from app.database.models import Document
from app.database.schema import mark_interrupted
from app.services import storage_service, gemini_service, ocr_service, extraction_service
from scripts.migrate_local_pdfs import locate_pdf
from scripts import migrate_local_pdfs


def document(**overrides):
    values = dict(id=1, filename="invoice.pdf", status="processing", storage_key="documents/test/original.pdf",
                  structured_json={}, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
                  error_message=None)
    values.update(overrides)
    return SimpleNamespace(**values)


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.db = MagicMock()
        main.app.dependency_overrides[main.get_db] = lambda: self.db
        self.addCleanup(main.app.dependency_overrides.clear)
        # No lifespan here: schema startup is tested independently, without a live DB.
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)
        self.storage = self.stack.enter_context(patch.object(main, "get_storage")).return_value
        self.worker = self.stack.enter_context(patch.object(main, "process_document"))
        self.created = self.stack.enter_context(patch.object(main, "create_document", return_value=document()))
        self.get = self.stack.enter_context(patch.object(main, "get_document", return_value=document()))
        self.failed = self.stack.enter_context(patch.object(main, "mark_failed"))

    def test_health_database_failure(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.db.execute.side_effect = RuntimeError("offline")
        self.assertEqual(self.client.get("/health").status_code, 503)
        self.storage.head_object.assert_not_called()

    def test_invalid_uploads(self):
        for name, body, status in [("a.txt", b"hi", 400), ("a.pdf", b"bad", 400),
                                    ("a.pdf", b"", 400), ("a.pdf", b"%PDF-" + b"x" * (20*1024*1024), 413)]:
            with self.subTest(name=name, size=len(body)):
                self.assertEqual(self.client.post("/upload", files={"file": (name, body)}).status_code, status)
        self.storage.upload_pdf.assert_not_called()
        self.created.assert_not_called()

    def test_duplicate_names_unique_keys_and_temp_cleanup(self):
        paths, keys = [], []
        def uploaded(path, key, name):
            self.assertEqual(Path(path).read_bytes(), b"%PDF-test")
            self.assertEqual(name, "same.pdf")
            paths.append(Path(path))
            keys.append(key)
        self.storage.upload_pdf.side_effect = uploaded
        for _ in range(2):
            response = self.client.post("/upload", files={"file": ("../../same.pdf", b"%PDF-test")})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["task_id"], 1)
        self.assertNotEqual(keys[0], keys[1])
        self.assertTrue(all(not path.exists() for path in paths))
        self.assertEqual(self.worker.call_count, 2)

    def test_r2_upload_failure_marks_failed_and_cleans_temp(self):
        paths = []
        def fail(path, *args):
            paths.append(Path(path))
            raise RuntimeError("secret-provider-detail")
        self.storage.upload_pdf.side_effect = fail
        result = self.client.post("/upload", files={"file": ("a.pdf", b"%PDF-test")})
        self.assertEqual(result.status_code, 502)
        self.assertFalse(paths[0].exists())
        self.assertIn("PDF storage failed", self.failed.call_args.args[2])
        self.assertNotIn("secret-provider-detail", self.failed.call_args.args[2])
        self.worker.assert_not_called()

    def test_results_and_history_contract(self):
        response = self.client.get("/results/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["structured_data"], {})
        self.assertIn("error_message", response.json())
        with patch.object(main, "get_all_documents", return_value=[document()]):
            self.assertEqual(self.client.get("/documents").json()[0]["filename"], "invoice.pdf")
        self.get.return_value = None
        self.assertEqual(self.client.get("/results/123").status_code, 404)

    def test_pdf_redirect_and_missing_original(self):
        self.storage.signed_pdf_url.return_value = "https://test.r2.cloudflarestorage.com/test?signature=example"
        result = self.client.get("/pdf/1", follow_redirects=False)
        self.assertEqual(result.status_code, 307)
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.get.return_value = document(storage_key=None)
        self.assertEqual(self.client.get("/pdf/1").status_code, 404)
        self.get.return_value = None
        self.assertEqual(self.client.get("/pdf/1").status_code, 404)

    def test_r2_preview_failure_codes(self):
        for code, status in [("404", 404), ("NoSuchKey", 404), ("AccessDenied", 502)]:
            self.storage.signed_pdf_url.side_effect = ClientError({"Error": {"Code": code}}, "HeadObject")
            self.assertEqual(self.client.get("/pdf/1").status_code, status)

    def test_cors_explicit_origin(self):
        good = self.client.options("/upload", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
        self.assertEqual(good.headers["access-control-allow-origin"], "http://localhost:5173")
        bad = self.client.options("/upload", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        self.assertNotIn("access-control-allow-origin", bad.headers)


class ProcessingTests(unittest.TestCase):
    def test_success_and_each_failure_clean_temporary_original(self):
        for failure in (None, "download", "ocr", "gemini", "save"):
            with self.subTest(failure=failure), ExitStack() as stack:
                storage = stack.enter_context(patch.object(main, "get_storage")).return_value
                paths = []
                def download(key, path):
                    paths.append(Path(path))
                    Path(path).write_bytes(b"%PDF-test")
                    if failure == "download":
                        raise RuntimeError("download failure")
                storage.download_pdf.side_effect = download
                stack.enter_context(patch.object(main, "SessionLocal"))
                stack.enter_context(patch.object(main, "get_document", return_value=document()))
                ocr = stack.enter_context(patch.object(main, "extract_text", return_value={"text": "test"}))
                gemini = stack.enter_context(patch.object(main, "extract_invoice_data", return_value={"total": 10}))
                saved = stack.enter_context(patch.object(main, "update_document"))
                failed = stack.enter_context(patch.object(main, "mark_failed"))
                for name, mocked in (("ocr", ocr), ("gemini", gemini), ("save", saved)):
                    if failure == name:
                        mocked.side_effect = ValueError("private provider response")
                main.process_document(1, "documents/test.pdf")
                self.assertFalse(paths[0].exists())
                if failure:
                    self.assertIn("failed", failed.call_args.args[2])
                    self.assertNotIn("private provider", failed.call_args.args[2])
                else:
                    failed.assert_not_called()
                    saved.assert_called_once()
                storage.delete_object.assert_not_called()

    def test_failure_to_persist_error_does_not_escape_worker(self):
        with patch.object(main, "get_storage", side_effect=RuntimeError()), patch.object(main, "SessionLocal", side_effect=RuntimeError()):
            main.process_document(1, "test")

    def test_gemini_sdk_parsing_and_rejections(self):
        with patch.object(gemini_service.genai, "Client") as factory:
            client = factory.return_value.__enter__.return_value
            for body, expected in [('```json\n{"total": 12}\n```', {"total": 12}), ('{"x": null}', {"x": None})]:
                client.models.generate_content.return_value.text = body
                self.assertEqual(gemini_service.extract_invoice_data("invoice"), expected)
            for body in ("", None, "not json"):
                client.models.generate_content.return_value.text = body
                with self.assertRaises(ValueError):
                    gemini_service.extract_invoice_data("invoice")
            self.assertEqual(factory.call_args.kwargs["http_options"].timeout, 120000)

    def test_ocr_renders_one_page_and_cleans_on_failure(self):
        for fail in (False, True):
            with patch.object(ocr_service, "pdfinfo_from_path", return_value={"Pages": 2}), patch.object(ocr_service, "convert_from_path") as render, patch.object(ocr_service.Image, "open"), patch.object(ocr_service.pytesseract, "image_to_string", return_value="hello") as ocr:
                folders = []
                def convert(*args, **kwargs):
                    self.assertEqual(kwargs["first_page"], kwargs["last_page"])
                    folders.append(Path(kwargs["output_folder"]))
                    return [str(folders[-1] / "page.ppm")]
                render.side_effect = convert
                if fail:
                    ocr.side_effect = RuntimeError("OCR timeout")
                    with self.assertRaises(RuntimeError):
                        ocr_service.extract_text_ocr("test.pdf")
                else:
                    self.assertIn("PAGE 2", ocr_service.extract_text_ocr("test.pdf"))
                self.assertTrue(all(not folder.exists() for folder in folders))

    def test_digital_vs_scanned_routing(self):
        with patch.object(extraction_service, "extract_text_pdfplumber", return_value="digital") as digital, patch.object(extraction_service, "extract_text_ocr", return_value="scan") as ocr:
            self.assertEqual(extraction_service.extract_text("test")["pdf_type"], "digital")
            ocr.assert_not_called()
            digital.return_value = ""
            self.assertEqual(extraction_service.extract_text("test")["method"], "tesseract")
            ocr.return_value = ""
            with self.assertRaises(ValueError):
                extraction_service.extract_text("test")


class StorageTests(unittest.TestCase):
    def test_r2_config_upload_download_and_signed_url(self):
        with patch.object(storage_service.boto3, "client") as factory, tempfile.TemporaryDirectory() as directory:
            storage = storage_service.R2Storage()
            path = Path(directory) / "original.pdf"
            path.write_bytes(b"%PDF-test")
            storage.upload_pdf(path, "key", 'invoice-₹.pdf')
            kwargs = factory.return_value.put_object.call_args.kwargs
            self.assertEqual(kwargs["ContentType"], "application/pdf")
            self.assertIn("%E2%82%B9", kwargs["ContentDisposition"])
            storage.download_pdf("key", path)
            factory.return_value.download_file.assert_called_once()
            storage.signed_pdf_url("key", 'invoice-₹.pdf')
            signed = factory.return_value.generate_presigned_url.call_args.kwargs
            self.assertEqual(signed["ExpiresIn"], 300)
            self.assertEqual(signed["Params"]["ResponseContentType"], "application/pdf")
            self.assertEqual(factory.call_args.kwargs["region_name"], "auto")

    def test_real_boto_client_signs_private_pdf_without_network(self):
        storage = storage_service.R2Storage()
        with Stubber(storage.client) as stub, tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file.pdf"
            path.write_bytes(b"%PDF-test")
            disposition = storage_service.content_disposition("invoice.pdf")
            stub.add_response("put_object", {}, {"Bucket": "test", "Key": "key", "Body": ANY,
                                               "ContentType": "application/pdf", "ContentDisposition": disposition})
            stub.add_response("head_object", {"ContentLength": 9}, {"Bucket": "test", "Key": "key"})
            storage.upload_pdf(path, "key", "invoice.pdf")
            url = storage.signed_pdf_url("key", "invoice.pdf")
            query = parse_qs(urlparse(url).query)
            self.assertEqual(query["X-Amz-Expires"], ["300"])
            self.assertEqual(query["response-content-type"], ["application/pdf"])
            self.assertIn("X-Amz-Signature", query)
            stub.assert_no_pending_responses()
        storage.client.close()

    def test_keys_are_safe_and_distinct(self):
        a = storage_service.new_storage_key("../../same.pdf")
        b = storage_service.new_storage_key("../../same.pdf")
        self.assertNotEqual(a, b)
        self.assertNotIn("..", a)
        self.assertTrue(a.endswith("/same.pdf"))

    def test_settings_and_database_url_validation(self):
        settings = Settings()
        settings.validate()
        settings.R2_SECRET_ACCESS_KEY = ""
        with self.assertRaisesRegex(RuntimeError, "R2_SECRET_ACCESS_KEY"):
            settings.validate_storage()
        for value in ("", "mongodb://host/database", "postgresql:///missing-host", "password"):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
                database_url(value)
        url = database_url("postgresql://u:p@ep-test.neon.tech/db?sslmode=disable")
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.query["sslmode"], "require")
        self.assertEqual(database_url("postgresql://u:p@host/db?sslmode=verify-full").query["sslmode"], "verify-full")


@compiles(JSONB, "sqlite")
def sqlite_jsonb(type_, compiler, **kwargs):
    return "JSON"


class DatabaseTests(unittest.TestCase):
    def test_crud_and_interrupted_jobs(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            first = create_document(db, "a.pdf", "key1")
            second = create_document(db, "a.pdf", "key2")
            self.assertNotEqual(first.id, second.id)
            update_document(db, first, {"pdf_type": "digital", "method": "pdfplumber", "text": "text"}, {"total": 42})
            mark_interrupted(db)
            db.expire_all()
            self.assertEqual(get_document(db, first.id).structured_json, {"total": 42})
            self.assertEqual(second.status, "failed")
            self.assertIn("interrupted", second.error_message)
            mark_failed(db, first, "OCR failed")
            self.assertEqual(first.error_message, "OCR failed")
            self.assertEqual(len(get_all_documents(db)), 2)
        engine.dispose()

    def test_postgres_schema_preserves_columns(self):
        ddl = str(CreateTable(Document.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn("JSONB", ddl)
        self.assertIn("TIMESTAMP WITH TIME ZONE", ddl)
        for name in ("storage_key", "error_message", "updated_at", "raw_text", "processing_method"):
            self.assertIn(name, ddl)

    def test_local_migration_paths_and_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "invoice.pdf").write_bytes(b"%PDF-test")
            doc = document()
            self.assertEqual(locate_pdf(root, doc, {"invoice.pdf": 1}), root / "invoice.pdf")
            with self.assertRaises(ValueError):
                locate_pdf(root, doc, {"invoice.pdf": 2})
            (root / "1.pdf").write_bytes(b"%PDF-id")
            self.assertEqual(locate_pdf(root, doc, {"invoice.pdf": 2}), root / "1.pdf")
            self.assertIsNone(locate_pdf(root, document(id=2, filename="../secret.pdf"), {}))

    def test_local_migration_is_rerunnable_and_preserves_data(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as db, tempfile.TemporaryDirectory() as directory:
            doc = create_document(db, "old.pdf", None)
            update_document(db, doc, {"text": "old", "pdf_type": "digital", "method": "pdfplumber"}, {"total": 7})
            before = doc.updated_at
            path = Path(directory) / f"{doc.id}.pdf"
            path.write_bytes(b"%PDF-old")
            with patch.object(migrate_local_pdfs, "SessionLocal") as sessions, patch.object(migrate_local_pdfs, "initialize_database"), patch.object(migrate_local_pdfs, "get_storage") as factory:
                # Prevent the context manager from closing this fixture's session.
                sessions.return_value.__enter__.return_value = db
                self.assertEqual(migrate_local_pdfs.migrate(directory, apply=False), 0)
                factory.assert_not_called()
                self.assertEqual(migrate_local_pdfs.migrate(directory, apply=True), 0)
                self.assertEqual(migrate_local_pdfs.migrate(directory, apply=True), 0)
                factory.return_value.upload_pdf.assert_called_once()
            db.refresh(doc)
            self.assertEqual(doc.structured_json, {"total": 7})
            self.assertEqual(doc.updated_at, before)
            self.assertTrue(path.exists())
            self.assertEqual(doc.storage_key, f"documents/legacy/{doc.id}/original.pdf")
        engine.dispose()

    def test_startup_checks_schema_and_marks_interrupted(self):
        async def start():
            async with main.lifespan(main.app):
                pass
        with patch.object(main, "initialize_database") as init, patch.object(main, "SessionLocal"), patch.object(main, "mark_interrupted") as interrupted, patch.object(main.engine, "dispose"):
            asyncio.run(start())
            init.assert_called_once()
            interrupted.assert_called_once()
            init.side_effect = RuntimeError("private DSN")
            with self.assertRaisesRegex(RuntimeError, "Unable to initialize PostgreSQL") as error:
                asyncio.run(start())
            self.assertNotIn("private DSN", str(error.exception))


if __name__ == "__main__":
    unittest.main()
