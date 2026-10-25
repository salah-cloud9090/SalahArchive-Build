# -*- coding: utf-8 -*-
import unittest
from mysql_runtime_compat_audit import audit

class RuntimeCompatibilityAuditTests(unittest.TestCase):
    def setUp(self):
        self.findings={x["code"]:x for x in audit()}
    def test_runtime_is_not_misreported_as_mysql(self):
        self.assertGreater(self.findings["sqlite_connect"]["count"],0)
    def test_sqlite_pragmas_are_flagged(self):
        self.assertGreater(self.findings["sqlite_pragma"]["count"],0)
    def test_executescript_is_flagged(self):
        self.assertGreater(self.findings["sqlite_executescript"]["count"],0)
    def test_replace_semantics_are_flagged(self):
        self.assertGreater(self.findings["insert_or_replace"]["count"],0)
    def test_candidate_schema_covers_expected_tables(self):
        self.assertIn("missing=",self.findings["candidate_schema_coverage"]["detail"])
        self.assertIn("missing=; unexpected=",self.findings["candidate_schema_coverage"]["detail"])
if __name__=="__main__": unittest.main(verbosity=2)
