# -*- coding: utf-8 -*-
import unittest
from mysql_sql_compat import translate_sql, SQLCompatibilityError

class SQLCompatibilityTests(unittest.TestCase):
    def test_parameter_placeholders(self):
        self.assertEqual(translate_sql("SELECT * FROM t WHERE a=? AND b=?"), "SELECT * FROM t WHERE a=%s AND b=%s")
    def test_preserves_question_marks_in_strings_and_comments(self):
        sql="SELECT '?' AS a, col FROM t WHERE x=? -- ? ignored\n/* ? ignored */"
        got=translate_sql(sql)
        self.assertIn("SELECT '?' AS a",got)
        self.assertIn("x=%s",got)
        self.assertIn("-- ? ignored",got)
        self.assertIn("/* ? ignored */",got)
    def test_datetime_now(self):
        self.assertEqual(translate_sql("UPDATE t SET at=datetime('now')"),"UPDATE t SET at=CURRENT_TIMESTAMP")
    def test_preserves_datetime_text_literal(self):
        sql="SELECT 'datetime(''now'')', datetime('now') FROM t"
        got=translate_sql(sql)
        self.assertIn("'datetime(''now'')'",got)
        self.assertTrue(got.endswith("CURRENT_TIMESTAMP FROM t"))
    def test_insert_or_ignore(self):
        self.assertEqual(translate_sql("INSERT OR IGNORE INTO t(a) VALUES(?)"),"INSERT IGNORE INTO t(a) VALUES(%s)")
    def test_rejects_pragma(self):
        with self.assertRaises(SQLCompatibilityError): translate_sql("PRAGMA foreign_keys=ON")
    def test_rejects_autoincrement_ddl(self):
        with self.assertRaises(SQLCompatibilityError): translate_sql("CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    def test_rewrites_known_basket_group_reassignment(self):
        sql = "INSERT OR REPLACE INTO scan_inbox_group_items(group_id,inbox_id) VALUES(?,?)"
        self.assertEqual(
            translate_sql(sql),
            "INSERT INTO scan_inbox_group_items(group_id,inbox_id) VALUES(%s,%s) ON DUPLICATE KEY UPDATE group_id=VALUES(group_id)",
        )

    def test_rejects_unreviewed_insert_or_replace(self):
        with self.assertRaises(SQLCompatibilityError): translate_sql("INSERT OR REPLACE INTO t VALUES(?)")
    def test_rejects_executescript(self):
        with self.assertRaises(SQLCompatibilityError): translate_sql("executescript('CREATE TABLE t(x)')")

    def test_safety_checks_ignore_keywords_inside_literals(self):
        sql = "SELECT 'INSERT OR REPLACE', 'AUTOINCREMENT', 'PRAGMA x', 'executescript('"
        self.assertEqual(translate_sql(sql), sql)

    def test_safety_checks_ignore_keywords_inside_comments(self):
        sql = "SELECT 1 /* INSERT OR REPLACE AUTOINCREMENT PRAGMA x executescript( */"
        self.assertEqual(translate_sql(sql), sql)

    def test_safety_checks_still_reject_real_construct_after_comment(self):
        with self.assertRaises(SQLCompatibilityError):
            translate_sql("/* harmless */ INSERT OR REPLACE INTO t VALUES (?)")

    def test_pragma_with_leading_comment_is_not_silently_translated(self):
        # A leading comment is retained by the mask; conservative handling must reject PRAGMA anywhere in syntax.
        with self.assertRaises(SQLCompatibilityError):
            translate_sql("/* setup */ PRAGMA foreign_keys=ON")
if __name__=="__main__": unittest.main(verbosity=2)
