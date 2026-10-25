import unittest
from mysql_main_static_audit import audit_text

def migration_readiness(source):
    r=audit_text(source); c=r["counts"]
    return {"checks":{
      "connection_factory":{"status":"BLOCKED" if c["sqlite_connect"] or c["row_factory"] else "REVIEW"},
      "schema_creation":{"status":"BLOCKED" if c["executescript"] or c["autoincrement"] else "REVIEW"},
      "duplicate_handling":{"status":"BLOCKED" if c["insert_or_replace"] or c["insert_or_ignore"] else "REVIEW"},
      "generated_ids":{"status":"REVIEW" if c["lastrowid"] else "UNKNOWN"},
      "runtime_integration":{"status":"NOT_STARTED"},
      "real_mysql_integration":{"status":"NOT_TESTED"}},
      "blockers":r["blockers"]}
class MigrationReadinessTests(unittest.TestCase):
    def test_flags_sqlite_connection_as_blocked(self):
        self.assertEqual(migration_readiness("conn = sqlite3.connect(path)\nconn.row_factory = sqlite3.Row")["checks"]["connection_factory"]["status"],"BLOCKED")
    def test_flags_schema_initialization(self):
        self.assertEqual(migration_readiness("conn.executescript(sql)\nCREATE TABLE x(id INTEGER PRIMARY KEY AUTOINCREMENT)")["checks"]["schema_creation"]["status"],"BLOCKED")
    def test_flags_duplicate_semantics(self):
        self.assertEqual(migration_readiness("INSERT OR REPLACE INTO x VALUES (?)\nINSERT OR IGNORE INTO y VALUES (?)")["checks"]["duplicate_handling"]["status"],"BLOCKED")
    def test_does_not_claim_mysql_tested(self):
        r=migration_readiness("def f(): pass")
        self.assertEqual(r["checks"]["real_mysql_integration"]["status"],"NOT_TESTED")
        self.assertEqual(r["checks"]["runtime_integration"]["status"],"NOT_STARTED")
if __name__=="__main__": unittest.main(verbosity=2)
