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
os.environ.update(CORS_ORIGINS="http://localhost:5173", DATABASE_URL="postgresql://test:test@localhost/test", GEMINI_API_KEY="test")

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
from app.services import gemini_service, ocr_service, extraction_service


def document(**overrides):
    values = dict(id=1, filename="invoice.pdf", status="processing",
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
        self.paths = []
        def worker(document_id, temporary):
            self.paths.append(Path(temporary.name) / "original.pdf")
            self.assertTrue(self.paths[-1].exists())
            temporary.cleanup()
        self.worker = self.stack.enter_context(patch.object(main, "process_document", side_effect=worker))
        self.created = self.stack.enter_context(patch.object(main, "create_document", return_value=document()))
        self.get = self.stack.enter_context(patch.object(main, "get_document", return_value=document()))
        self.failed = self.stack.enter_context(patch.object(main, "mark_failed"))

    def test_health_database_failure(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.db.execute.side_effect = RuntimeError("offline")
        self.assertEqual(self.client.get("/health").status_code, 503)

    def test_invalid_uploads(self):
        for name, body, status in [("a.txt", b"hi", 400), ("a.pdf", b"bad", 400),
                                    ("a.pdf", b"", 400), ("a.pdf", b"%PDF-" + b"x" * (20*1024*1024), 413)]:
            with self.subTest(name=name, size=len(body)):
                self.assertEqual(self.client.post("/upload", files={"file": (name, body)}).status_code, status)
        self.created.assert_not_called()

    def test_duplicate_names_unique_temp_paths_and_cleanup(self):
        for _ in range(2):
            response = self.client.post("/upload", files={"file": ("../../same.pdf", b"%PDF-test")})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["task_id"], 1)
        self.assertEqual(self.created.call_args.args[1], "same.pdf")
        self.assertNotEqual(self.paths[0], self.paths[1])
        self.assertTrue(all(not path.exists() for path in self.paths))
        self.assertEqual(self.worker.call_count, 2)

    def test_upload_validation_and_database_failure_clean_temp(self):
        directories = []
        real_temp = tempfile.TemporaryDirectory
        def create_temp(**kwargs):
            temp = real_temp(**kwargs)
            directories.append(Path(temp.name))
            return temp
        with patch.object(main, "TemporaryDirectory", side_effect=create_temp):
            self.assertEqual(self.client.post("/upload", files={"file": ("a.pdf", b"invalid")}).status_code, 400)
            self.created.side_effect = RuntimeError("database offline")
            with self.assertRaises(RuntimeError):
                self.client.post("/upload", files={"file": ("a.pdf", b"%PDF-test")})
        self.assertTrue(all(not path.exists() for path in directories))
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

    def test_original_pdf_endpoint_is_disabled(self):
        result = self.client.get("/pdf/1")
        self.assertEqual(result.status_code, 410)
        self.assertIn("deleted after processing", result.json()["detail"])
        self.get.assert_not_called()

    def test_cors_explicit_origin(self):
        good = self.client.options("/upload", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
        self.assertEqual(good.headers["access-control-allow-origin"], "http://localhost:5173")
        bad = self.client.options("/upload", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        self.assertNotIn("access-control-allow-origin", bad.headers)


class ProcessingTests(unittest.TestCase):
    def test_success_and_each_failure_clean_temporary_original(self):
        for failure in (None, "ocr", "gemini", "save"):
            with self.subTest(failure=failure), ExitStack() as stack:
                temporary = tempfile.TemporaryDirectory(prefix="structify-test-")
                stack.callback(temporary.cleanup)
                path = Path(temporary.name) / "original.pdf"
                path.write_bytes(b"%PDF-test")
                stack.enter_context(patch.object(main, "SessionLocal"))
                stack.enter_context(patch.object(main, "get_document", return_value=document()))
                ocr = stack.enter_context(patch.object(main, "extract_text", return_value={"text": "test"}))
                gemini = stack.enter_context(patch.object(main, "extract_invoice_data", return_value={"total": 10}))
                saved = stack.enter_context(patch.object(main, "update_document"))
                failed = stack.enter_context(patch.object(main, "mark_failed"))
                for name, mocked in (("ocr", ocr), ("gemini", gemini), ("save", saved)):
                    if failure == name:
                        mocked.side_effect = ValueError("private provider response")
                main.process_document(1, temporary)
                self.assertFalse(path.exists())
                self.assertFalse(path.parent.exists())
                if failure:
                    self.assertIn("failed", failed.call_args.args[2])
                    self.assertNotIn("private provider", failed.call_args.args[2])
                else:
                    failed.assert_not_called()
                    saved.assert_called_once()

    def test_failure_to_persist_error_still_cleans_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = tempfile.TemporaryDirectory(dir=directory)
            path = Path(temporary.name) / "original.pdf"
            path.write_bytes(b"%PDF-test")
            with patch.object(main, "extract_text", side_effect=RuntimeError()), patch.object(main, "SessionLocal", side_effect=RuntimeError()):
                main.process_document(1, temporary)
            self.assertFalse(path.exists())

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


class ConfigurationTests(unittest.TestCase):
    def test_settings_and_database_url_validation(self):
        settings = Settings()
        settings.validate()
        self.assertFalse(any(name.startswith("R2_") for name in vars(Settings)))
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
            first = create_document(db, "a.pdf")
            second = create_document(db, "a.pdf")
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
        self.assertNotIn("storage_key", ddl)
        self.assertIn("TIMESTAMP WITH TIME ZONE", ddl)
        for name in ("error_message", "updated_at", "raw_text", "processing_method"):
            self.assertIn(name, ddl)

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
