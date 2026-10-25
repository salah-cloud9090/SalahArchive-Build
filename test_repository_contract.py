# -*- coding: utf-8 -*-
import sqlite3
import unittest

from archive_repository import SQLiteRepository
from mysql_repository import MySQLRepository
from repository_contract import REQUIRED_METHODS, missing_repository_methods

class Cursor:
    def __init__(self):
        self.lastrowid = 1
        self.description = [("id",)]
    def execute(self, sql, params=()): pass
    def fetchone(self): return (1,)
    def fetchall(self): return [(1,)]
    def close(self): pass

class FakeConnection:
    def cursor(self, dictionary=False): return Cursor()
    def commit(self): pass
    def rollback(self): pass
    def close(self): pass

class RepositoryContractTests(unittest.TestCase):
    def test_sqlite_adapter_exposes_contract(self):
        repo = SQLiteRepository(sqlite3.connect(":memory:"))
        self.assertEqual(missing_repository_methods(repo), [])
        repo.close()

    def test_mysql_adapter_exposes_contract_without_connecting(self):
        repo = MySQLRepository(FakeConnection())
        self.assertEqual(missing_repository_methods(repo), [])

    def test_required_methods_are_stable(self):
        self.assertEqual(REQUIRED_METHODS,
            ("execute", "fetch_one", "fetch_all", "insert", "transaction", "close"))

    def test_contract_checker_does_not_execute_methods(self):
        class Empty: pass
        self.assertEqual(missing_repository_methods(Empty()), list(REQUIRED_METHODS))

if __name__ == "__main__":
    unittest.main(verbosity=2)
