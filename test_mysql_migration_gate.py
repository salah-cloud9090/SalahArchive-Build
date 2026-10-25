# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
from mysql_migration_gate import extract_create_tables, build_report, split_top_level

class MigrationGateTests(unittest.TestCase):
    def test_split_top_level_respects_nested_commas_and_literals(self):
        self.assertEqual(split_top_level("id INT, name VARCHAR(20), note TEXT DEFAULT 'a,b', UNIQUE(id,name)"), ["id INT", "name VARCHAR(20)", "note TEXT DEFAULT 'a,b'", "UNIQUE(id,name)"])

    def test_extract_tables_ignores_constraints_as_columns(self):
        schema = "CREATE TABLE IF NOT EXISTS sample (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, FOREIGN KEY(id) REFERENCES parent(id), UNIQUE(id,name));"
        self.assertEqual(extract_create_tables(schema)["sample"], {"id", "name"})

    def test_gate_finds_missing_table_and_column(self):
        main = "SCHEMA = \"CREATE TABLE IF NOT EXISTS a (id INTEGER, name TEXT); CREATE TABLE IF NOT EXISTS b (id INTEGER);\""
        mysql = "CREATE TABLE IF NOT EXISTS a (id BIGINT);"
        report = build_report(main, mysql)
        self.assertEqual(report["missing_tables"], ["b"])
        self.assertEqual(report["missing_columns"], {"a": ["name"]})
        self.assertEqual(report["status"], "BLOCKED")

    def test_gate_does_not_claim_ready_when_runtime_markers_remain(self):
        main = "SCHEMA = 'CREATE TABLE IF NOT EXISTS a (id INTEGER);'\nconn = sqlite3.connect('x')\nconn.execute('PRAGMA foreign_keys=ON')"
        mysql = "CREATE TABLE IF NOT EXISTS a (id BIGINT);"
        report = build_report(main, mysql)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertGreater(report["marker_line_count"], 0)

    def test_project_candidate_has_table_and_column_coverage_but_is_still_blocked(self):
        root = Path(__file__).parent
        main = (root / "main_mysql_candidate_v15_79.py").read_text(encoding="utf-8")
        mysql = (root / "MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql").read_text(encoding="utf-8")
        report = build_report(main, mysql)
        self.assertEqual(report["missing_tables"], [])
        self.assertEqual(report["missing_columns"], {})
        self.assertEqual(report["status"], "BLOCKED")
        self.assertGreater(report["marker_line_count"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
