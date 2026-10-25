import ast
import hashlib
import json
import warnings
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = (
    "main_mysql_candidate.py",
    "main_mysql_candidate_v15_76.py",
    "main_mysql_candidate_v15_81.py",
)

class EmbeddedJavaScriptWarningCleanupTests(unittest.TestCase):
    def test_all_mysql_candidates_compile_without_invalid_escape_warnings(self):
        for name in CANDIDATES:
            with self.subTest(candidate=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                with warnings.catch_warnings():
                    warnings.simplefilter("error", SyntaxWarning)
                    compile(source, name, "exec")

    def test_candidate_preserves_javascript_regex_backslashes_at_runtime(self):
        source = (ROOT / "main_mysql_candidate_v15_81.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        script_literal = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == "body":
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    continue
                if isinstance(value, str) and "document.querySelectorAll('textarea[list]')" in value:
                    script_literal = value
                    break
        self.assertIsNotNone(script_literal, "embedded JavaScript block was not found")
        self.assertIn(r"replace(/\s+/g,'')", script_literal)
        self.assertIn(r"replace(/\D/g,'')", script_literal)
        self.assertIn(r"^(\d{1,2})", script_literal)

    def test_current_main_matches_release_manifest(self):
        manifest = json.loads((ROOT / "integrity_manifest.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256((ROOT / "main.py").read_bytes()).hexdigest()
        self.assertEqual(digest, manifest["files"]["main.py"])

    def test_smoke_test_uses_latest_candidate(self):
        source = (ROOT / "smoke_test_sqlite_isolated.py").read_text(encoding="utf-8")
        self.assertIn("main_mysql_candidate_v15_81.py", source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
