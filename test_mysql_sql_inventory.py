import unittest
from pathlib import Path
import re

class SQLInventorySanityTests(unittest.TestCase):
    def test_main_contains_known_sqlite_migration_markers(self):
        source = Path("main.py").read_text(encoding="utf-8", errors="replace")
        self.assertRegex(source, r"sqlite3\.connect")
        self.assertRegex(source, r"\bPRAGMA\b")
        self.assertRegex(source, r"INSERT\s+OR\s+IGNORE")
        self.assertRegex(source, r"\.lastrowid\b")

    def test_main_still_uses_sqlite_and_is_not_claimed_migrated(self):
        source = Path("main.py").read_text(encoding="utf-8", errors="replace")
        self.assertRegex(source, r"sqlite3\.connect")
        self.assertNotRegex(source, r"mysql_repository\s*=\s*MySQLRepository\(")

if __name__ == "__main__":
    unittest.main(verbosity=2)
