import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Never connect to the developer database or call Gemini in regression tests.
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
os.environ["GEMINI_API_KEY"] = "test-key"

from fastapi import BackgroundTasks, HTTPException, UploadFile
import main


def upload(test, name, body):
    file = tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024)
    test.addCleanup(file.close)
    file.write(body)
    file.seek(0)
    return UploadFile(filename=name, file=file)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_dir = main.UPLOAD_DIR
        main.UPLOAD_DIR = Path(self.temp.name)
        self.db = MagicMock()

    def tearDown(self):
        main.UPLOAD_DIR = self.old_dir
        self.temp.cleanup()

    def test_health_checks_database(self):
        self.assertEqual(main.health(self.db), {"status": "ok"})
        self.db.execute.side_effect = RuntimeError("offline")
        with self.assertRaises(HTTPException) as error:
            main.health(self.db)
        self.assertEqual(error.exception.status_code, 503)

    def test_invalid_and_oversized_uploads(self):
        for name, body, status in [
            ("a.txt", b"hello", 400),
            ("a.pdf", b"not a pdf", 400),
            ("a.pdf", b"%PDF-" + b"x" * (20 * 1024 * 1024), 413),
        ]:
            with self.assertRaises(HTTPException) as error:
                asyncio.run(main.upload_pdf(BackgroundTasks(), upload(self, name, body), self.db))
            self.assertEqual(error.exception.status_code, status)

    def test_duplicate_names_have_distinct_storage(self):
        with patch.object(main, "create_document", side_effect=[SimpleNamespace(id=1), SimpleNamespace(id=2)]) as create, patch.object(main, "process_document"):
            for body in [b"%PDF-first", b"%PDF-second"]:
                response = asyncio.run(main.upload_pdf(BackgroundTasks(), upload(self, "../../same.pdf", body), self.db))
                self.assertEqual(response["status"], "processing")
            self.assertEqual(create.call_args.args[1], "same.pdf")
        self.assertEqual((main.UPLOAD_DIR / "1.pdf").read_bytes(), b"%PDF-first")
        self.assertEqual((main.UPLOAD_DIR / "2.pdf").read_bytes(), b"%PDF-second")

    def test_legacy_path_cannot_escape_upload_directory(self):
        with patch.object(main, "get_document", return_value=SimpleNamespace(id=1, filename="../secret.pdf")):
            with self.assertRaises(HTTPException) as error:
                main.serve_pdf(1, self.db)
            self.assertEqual(error.exception.status_code, 404)

    def test_pdf_preview_handles_unicode_filename(self):
        (main.UPLOAD_DIR / "1.pdf").write_bytes(b"%PDF-test")
        with patch.object(main, "get_document", return_value=SimpleNamespace(id=1, filename="facture-₹.pdf")):
            response = main.serve_pdf(1, self.db)
        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
