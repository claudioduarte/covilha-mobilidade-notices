import contextlib
import io
import os
import runpy
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fitz


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_notices.py"


class ExtractionTest(unittest.TestCase):
    def test_changed_notice_generates_pages_and_unchanged_notice_does_not_refresh(self):
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "New notice <test> & details")
        pdf_bytes = pdf.tobytes()
        pdf.close()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            script = root / "scripts" / SCRIPT.name
            shutil.copyfile(SCRIPT, script)
            (root / "output").mkdir()
            (root / "output" / "latest.txt").write_text("Old notice", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "index.html").write_text("Old page", encoding="utf-8")

            class Response:
                content = pdf_bytes
                status_code = 200

                def raise_for_status(self):
                    pass

            def run_extractor():
                with patch.dict(os.environ, {"PDF_URL": "https://example.com/notice.pdf"}), \
                     patch("requests.get", return_value=Response()), \
                     contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    runpy.run_path(str(script), run_name="__main__")

            run_extractor()
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            latest = (root / "output" / "latest.txt").read_text(encoding="utf-8")
            self.assertEqual(latest, "New notice <test> & details")
            self.assertEqual((root / "output" / f"notices-{date}.txt").read_text(encoding="utf-8"), latest)
            index = (root / "docs" / "index.html").read_text(encoding="utf-8")
            dated = (root / "docs" / f"notices-{date}.html").read_text(encoding="utf-8")
            archive = (root / "docs" / "archive.html").read_text(encoding="utf-8")
            self.assertIn("New notice &lt;test&gt; &amp; details", index)
            self.assertIn("New notice &lt;test&gt; &amp; details", dated)
            self.assertIn(f'./notices-{date}.html', archive)
            self.assertIn('href="./archive.html"', index)
            self.assertIn('href="./index.html"', dated)

            files = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            run_extractor()
            self.assertEqual(files, {path: path.read_bytes() for path in root.rglob("*") if path.is_file()})


if __name__ == "__main__":
    unittest.main()
