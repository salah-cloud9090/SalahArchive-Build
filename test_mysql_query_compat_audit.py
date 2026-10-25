# -*- coding: utf-8 -*-
import unittest
from mysql_query_compat_audit import audit_source

class QueryCompatAuditTests(unittest.TestCase):
    def test_audits_literal_queries_and_marks_pragma_blocked(self):
        source = "SCHEMA = 'x'\nc.execute('SELECT * FROM t WHERE id=?', (1,))\nc.execute('PRAGMA foreign_keys=ON')"
        report = audit_source(source)
        self.assertEqual(report['statement_count'], 2)
        self.assertEqual(report['blocked_count'], 1)
        self.assertEqual(report['findings'][0]['status'], 'translated_candidate')
        self.assertEqual(report['findings'][1]['status'], 'blocked')

    def test_does_not_treat_non_sql_literal_as_query(self):
        report = audit_source("c.execute('hello world')")
        self.assertEqual(report['statement_count'], 0)

    def test_executescript_is_always_blocked_for_review(self):
        report = audit_source("c.executescript(SCHEMA)")
        self.assertEqual(report['findings'][0]['status'], 'blocked')

    def test_dynamic_fstring_is_reported_for_manual_review(self):
        report = audit_source("marks = ','.join('?' for _ in ids)\nc.execute(f'SELECT * FROM t WHERE id IN ({marks})', ids)")
        self.assertEqual(report['findings'][0]['status'], 'dynamic_review_required')

if __name__ == '__main__': unittest.main(verbosity=2)
