import unittest
from mysql_schema_index_audit import build_report
from mysql_schema_manager import expected_indexes

class SchemaIndexCoverageTests(unittest.TestCase):
    def test_candidate_schema_has_primary_keys_and_declared_index_columns(self):
        report = build_report()
        self.assertEqual(report['status'], 'PASS_STATIC', report['errors'])
        self.assertEqual(report['tables_checked'], 16)
        self.assertGreaterEqual(report['indexes_checked'], 35)
        self.assertEqual(report['errors'], [])

    def test_candidate_schema_parses_all_foreign_keys_and_targets(self):
        report = build_report()
        self.assertEqual(report['foreign_keys_checked'], 14, report['foreign_keys'])
        self.assertEqual(report['errors'], [])
        self.assertTrue(all(fk['references_table'] for fk in report['foreign_keys']))

    def test_inline_unique_index_uses_mysql_default_index_name(self):
        _, indexes = expected_indexes('CREATE TABLE IF NOT EXISTS sample (id BIGINT PRIMARY KEY, name VARCHAR(190) UNIQUE) ENGINE=InnoDB;')
        self.assertEqual(indexes['name'], (True, (('name', None),)))

if __name__ == '__main__':
    unittest.main(verbosity=2)
