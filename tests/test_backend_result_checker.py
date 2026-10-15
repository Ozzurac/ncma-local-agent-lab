"""Deterministic checks of the optional fresh-run oracle comparison CLI."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_backend_result.py"
REFERENCE = ROOT / "benchmarks" / "g4h" / "evidence" / "final_results.json"


def check_file(path: Path):
    p = subprocess.run([sys.executable, str(SCRIPT), "--result", str(path)],
                       cwd=ROOT, capture_output=True, text=True, check=False)
    return p.returncode, json.loads(p.stdout)


class VerifyFreshBackendResultTests(unittest.TestCase):
    def test_published_reference_matches(self):
        code, report = check_file(REFERENCE)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["fields_correct"], 60)

    def test_modified_terminal_fails(self):
        data = json.loads(REFERENCE.read_text(encoding="utf-8"))
        data["results"][0]["terminal"] = "INCORRECT-SYNTHETIC"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "final_results.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, report = check_file(path)
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(x.startswith("FIELD_MISMATCH:") for x in report["errors"]))

    def test_duplicate_case_fails(self):
        data = json.loads(REFERENCE.read_text(encoding="utf-8"))
        data["results"][1] = data["results"][0]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "final_results.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, report = check_file(path)
        self.assertEqual(code, 1)
        self.assertTrue(any(x.startswith("DUPLICATE_CASE:") for x in report["errors"]))

    def test_missing_result_reports_nonzero(self):
        code, report = check_file(ROOT / "runs" / "nonexistent-trial" / "final_results.json")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "INCOMPLETE_OR_INVALID")


if __name__ == "__main__":
    unittest.main()
