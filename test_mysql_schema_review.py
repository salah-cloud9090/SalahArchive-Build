# -*- coding: utf-8 -*-
import re, unittest
from pathlib import Path

SQL_PATH=Path(__file__).with_name("MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql")
SQL=SQL_PATH.read_text(encoding="utf-8")

class MySQLSchemaReviewTests(unittest.TestCase):
    def test_expected_core_tables_present(self):
        names=set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)",SQL,re.I))
        expected={"local_cabinets","local_documents","local_document_fields","local_users","local_audit","local_cases","local_case_events","scan_baskets","scan_inbox","local_case_inbox_links","local_case_documents","local_case_attachments","scan_inbox_groups","scan_inbox_group_items","archive_index","archive_index_fields"}
        self.assertEqual(names,expected)
    def test_all_tables_use_innodb_utf8mb4(self):
        self.assertEqual(len(re.findall(r"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",SQL)),16)
    def test_no_destructive_statements(self):
        self.assertIsNone(re.search(r"(?im)^\s*(DROP|TRUNCATE|DELETE|ALTER)\b",SQL))
    def test_no_sqlite_only_pragmas(self):
        self.assertNotRegex(SQL,r"(?i)\bPRAGMA\b")
    def test_primary_keys_are_auto_increment(self):
        self.assertEqual(len(re.findall(r"AUTO_INCREMENT PRIMARY KEY",SQL)),13)
    def test_unique_text_columns_are_bounded_varchar(self):
        self.assertNotRegex(SQL,r"(?is)LONGTEXT\s+NOT NULL\s+UNIQUE")
        self.assertNotRegex(SQL,r"(?is)TEXT\s+NOT NULL\s+UNIQUE")
    def test_every_foreign_key_target_exists(self):
        tables=set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)",SQL,re.I))
        refs=re.findall(r"REFERENCES\s+([a-z_]+)\s*\(",SQL,re.I)
        self.assertTrue(refs)
        self.assertTrue(set(refs).issubset(tables),set(refs)-tables)
    def test_uses_utf8mb4(self):
        self.assertIn("SET NAMES utf8mb4",SQL)
if __name__=="__main__": unittest.main(verbosity=2)
