import unittest
from mysql_main_static_audit import audit_text
class MainStaticAuditTests(unittest.TestCase):
    def test_sqlite_connect(self):
        self.assertEqual(audit_text("sqlite3.connect(path)")["counts"]["sqlite_connect"],1)
    def test_executescript_and_pragma(self):
        r=audit_text("conn.executescript(sql)\nconn.execute('PRAGMA foreign_keys=ON')")
        self.assertEqual(r["counts"]["executescript"],1)
        self.assertEqual(r["counts"]["sqlite_pragma"],1)
        self.assertEqual(len(r["blockers"]),2)
    def test_replace_and_ignore(self):
        r=audit_text("INSERT OR REPLACE INTO x VALUES (?)\nINSERT OR IGNORE INTO y VALUES (?)")
        self.assertEqual(r["counts"]["insert_or_replace"],1)
        self.assertEqual(r["counts"]["insert_or_ignore"],1)
    def test_generated_ids(self):
        self.assertEqual(audit_text("x = cur.lastrowid")["counts"]["lastrowid"],1)
    def test_clean_source(self):
        self.assertEqual(audit_text("def f():\n return 1")["blockers"],[])
if __name__=="__main__": unittest.main(verbosity=2)
