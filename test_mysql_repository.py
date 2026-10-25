# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mysql_repository import (
    MySQLRepository, MySQLRepositoryError, connect_test_repository
)
from mysql_sql_compat import SQLCompatibilityError


class FakeCursor:
    def __init__(self, rows=None, lastrowid=1, description=None):
        self.rows = list(rows or [])
        self.lastrowid = lastrowid
        self.description = description or []
        self.sql = None
        self.params = None
        self.closed = False

    def execute(self, sql, params=()):
        self.sql, self.params = sql, params

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursors = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.rows_next = []
        self.lastrowid = 7

    def cursor(self, dictionary=False):
        cur = FakeCursor(self.rows_next, self.lastrowid,
                         [("id",), ("title",)])
        self.rows_next = []
        self.cursors.append(cur)
        return cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FakeConnector:
    def __init__(self, connection):
        self.connection = connection
        self.kwargs = None

    def connect(self, **kwargs):
        self.kwargs = kwargs
        return self.connection


class MySQLRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = FakeConnection()
        self.repo = MySQLRepository(self.connection)

    def test_translates_placeholders_and_preserves_literal_question_mark(self):
        cur = self.repo.execute("SELECT '?' AS literal, id FROM t WHERE id = ?", (3,))
        self.assertIn("WHERE id = %s", cur.sql)
        self.assertIn("'?'", cur.sql)
        self.assertEqual(cur.params, (3,))

    def test_fetch_one_maps_tuple_row(self):
        self.connection.rows_next = [(4, "hello")]
        self.assertEqual(self.repo.fetch_one("SELECT id, title FROM t"),
                         {"id": 4, "title": "hello"})

    def test_fetch_one_accepts_mapping_row(self):
        self.connection.rows_next = [{"id": 4, "title": "hello"}]
        self.assertEqual(self.repo.fetch_one("SELECT id, title FROM t"),
                         {"id": 4, "title": "hello"})

    def test_fetch_all_maps_rows(self):
        self.connection.rows_next = [(1, "a"), (2, "b")]
        self.assertEqual(self.repo.fetch_all("SELECT id, title FROM t"),
                         [{"id": 1, "title": "a"}, {"id": 2, "title": "b"}])

    def test_insert_returns_id(self):
        self.assertEqual(self.repo.insert("INSERT INTO t(title) VALUES (?)", ("x",)), 7)

    def test_transaction_commits(self):
        with self.repo.transaction():
            pass
        self.assertEqual(self.connection.commits, 1)
        self.assertEqual(self.connection.rollbacks, 0)

    def test_context_manager_commits_on_success(self):
        with self.repo as conn:
            self.assertIs(conn, self.repo)
        self.assertEqual(self.connection.commits, 1)
        self.assertEqual(self.connection.rollbacks, 0)

    def test_context_manager_rolls_back_on_error(self):
        with self.assertRaises(RuntimeError):
            with self.repo:
                raise RuntimeError("expected test error")
        self.assertEqual(self.connection.commits, 0)
        self.assertEqual(self.connection.rollbacks, 1)

    def test_executescript_fails_closed(self):
        with self.assertRaises(SQLCompatibilityError):
            self.repo.executescript("CREATE TABLE sample(id INT)")
        self.assertEqual(self.connection.cursors, [])

    def test_explicit_commit_and_rollback_are_exposed(self):
        self.repo.commit()
        self.repo.rollback()
        self.assertEqual(self.connection.commits, 1)
        self.assertEqual(self.connection.rollbacks, 1)

    def test_transaction_rolls_back(self):
        with self.assertRaises(ValueError):
            with self.repo.transaction():
                raise ValueError("rollback")
        self.assertEqual(self.connection.rollbacks, 1)

    def test_rejects_unsupported_sql_before_cursor(self):
        with self.assertRaises(SQLCompatibilityError):
            self.repo.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(self.connection.cursors, [])

    def test_connect_is_test_db_only_and_uses_env_password(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "mysql_config.json").write_text(json.dumps({
                "host": "127.0.0.1", "port": 3306, "user": "tester",
                "database": "salah_archive_test", "password": "legacy-secret"
            }), encoding="utf-8")
            fake = FakeConnector(self.connection)
            with patch.dict(os.environ, {"SALAH_MYSQL_PASSWORD": "env-secret"}):
                repo = connect_test_repository(d, connector=fake)
            self.assertIsInstance(repo, MySQLRepository)
            self.assertEqual(fake.kwargs["database"], "salah_archive_test")
            self.assertEqual(fake.kwargs["password"], "env-secret")

    def test_connect_rejects_original_database(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "mysql_config.json").write_text(json.dumps({
                "host": "127.0.0.1", "port": 3306, "user": "tester",
                "database": "salah_archive"
            }), encoding="utf-8")
            with patch.dict(os.environ, {"SALAH_MYSQL_PASSWORD": "env-secret"}):
                with self.assertRaises(ValueError):
                    connect_test_repository(d, connector=FakeConnector(self.connection))
        self.assertEqual(self.connection.cursors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
