# -*- coding: utf-8 -*-
import sqlite3
import unittest
from archive_repository import SQLiteRepository

class SQLiteRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.repo = SQLiteRepository(self.connection)
        self.repo.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    def tearDown(self):
        self.connection.close()
    def test_insert_returns_generated_id(self):
        self.assertEqual(self.repo.insert("INSERT INTO items(name) VALUES (?)", ("alpha",)), 1)
    def test_fetch_one_returns_dict(self):
        self.repo.execute("INSERT INTO items(name) VALUES (?)", ("alpha",))
        self.assertEqual(self.repo.fetch_one("SELECT id, name FROM items WHERE name = ?", ("alpha",)), {"id": 1, "name": "alpha"})
    def test_fetch_all_returns_dict_rows(self):
        self.repo.execute("INSERT INTO items(name) VALUES (?)", ("a",))
        self.repo.execute("INSERT INTO items(name) VALUES (?)", ("b",))
        self.assertEqual(self.repo.fetch_all("SELECT name FROM items ORDER BY id"), [{"name": "a"}, {"name": "b"}])
    def test_missing_fetch_one_returns_none(self):
        self.assertIsNone(self.repo.fetch_one("SELECT * FROM items WHERE id = ?", (404,)))
    def test_transaction_commits_on_success(self):
        with self.repo.transaction():
            self.repo.execute("INSERT INTO items(name) VALUES (?)", ("committed",))
        self.assertEqual(self.repo.fetch_one("SELECT name FROM items"), {"name": "committed"})
    def test_transaction_rolls_back_on_error(self):
        with self.assertRaises(ValueError):
            with self.repo.transaction():
                self.repo.execute("INSERT INTO items(name) VALUES (?)", ("rolled back",))
                raise ValueError("force rollback")
        self.assertEqual(self.repo.fetch_all("SELECT * FROM items"), [])
    def test_rejects_non_sqlite_connection(self):
        with self.assertRaises(TypeError):
            SQLiteRepository(object())

if __name__ == "__main__":
    unittest.main(verbosity=2)
