import unittest
from mysql_pre_final_audit import audit

class PreFinalAuditTests(unittest.TestCase):
    def test_detects_sqlite_runtime_and_keeps_gate_blocked(self):
        main = '''import sqlite3\ndef db():\n    return sqlite3.connect("x")\ndef init():\n    c=db()\n    c.execute("PRAGMA foreign_keys=ON")\n    c.executescript("CREATE TABLE x(id INTEGER)")\n'''
        repo = '''class MySQLRepository:\n    def __enter__(self): return self\n    def __exit__(self, *args): pass\n    def commit(self): pass\n    def rollback(self): pass\n    def executescript(self, script): raise SQLCompatibilityError()\n'''
        result = audit(main, repo)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["runtime_markers"]["runtime_sqlite_connect"])
        self.assertTrue(result["runtime_markers"]["runtime_executescript"])
        self.assertFalse(result["safety"]["original_database_opened"])

    def test_no_runtime_sqlite_markers_still_requires_review(self):
        result = audit("def db(): return MySQLRepository()", "class MySQLRepository: pass")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["blockers"], [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
