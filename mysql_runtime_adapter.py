# -*- coding: utf-8 -*-
"""Experimental SQLite-shaped facade for MySQL; intentionally not wired into main.py.

The facade preserves the small subset used by the local archive's request handlers:
execute/fetchone/fetchall/lastrowid and connection context-manager transactions.
It refuses SQLite schema/session operations instead of guessing their MySQL meaning.
"""
from __future__ import annotations
import sqlite3
from typing import Any
from mysql_sql_compat import translate_sql, SQLCompatibilityError

class MySQLRuntimeError(RuntimeError):
    pass

class HybridRow:
    """Row supporting both sqlite3.Row-style name and integer indexing."""
    __slots__ = ("_names", "_values", "_index")
    def __init__(self, names, values):
        self._names = tuple(names or ())
        self._values = tuple(values or ())
        self._index = {name: i for i, name in enumerate(self._names)}
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index[key]]
    def __iter__(self):
        return iter(self._values)
    def __len__(self):
        return len(self._values)
    def keys(self):
        return self._names
    def values(self):
        return self._values
    def items(self):
        return zip(self._names, self._values)
    def get(self, key, default=None):
        try: return self[key]
        except (KeyError, IndexError, TypeError): return default
    def __repr__(self):
        return f"HybridRow({dict(self.items())!r})"

def _raise_compatible_db_error(exc):
    """Map MySQL integrity-constraint failures to the sqlite-compatible type used by handlers."""
    errno = getattr(exc, "errno", None)
    sqlstate = getattr(exc, "sqlstate", None)
    if errno in {1048, 1062, 1451, 1452} or (isinstance(sqlstate, str) and sqlstate.startswith("23")):
        raise sqlite3.IntegrityError(str(exc)) from exc
    raise exc

class MySQLCursorFacade:
    def __init__(self, cursor, owner):
        self._cursor = cursor
        self._owner = owner
        self._closed = False
        owner._cursors.add(self)
    def execute(self, sql, params=()):
        if self._closed: raise MySQLRuntimeError("Cursor is closed")
        try:
            translated = translate_sql(sql)
        except SQLCompatibilityError as exc:
            raise MySQLRuntimeError(str(exc)) from exc
        try:
            self._cursor.execute(translated, tuple(params or ()))
        except Exception as exc:
            _raise_compatible_db_error(exc)
        return self
    def executemany(self, sql, seq_params):
        if self._closed: raise MySQLRuntimeError("Cursor is closed")
        try: translated = translate_sql(sql)
        except SQLCompatibilityError as exc: raise MySQLRuntimeError(str(exc)) from exc
        try:
            self._cursor.executemany(translated, seq_params)
        except Exception as exc:
            _raise_compatible_db_error(exc)
        return self
    @property
    def lastrowid(self): return self._cursor.lastrowid
    @property
    def rowcount(self): return self._cursor.rowcount
    @property
    def description(self): return self._cursor.description
    def _row(self, row):
        if row is None: return None
        desc = self._cursor.description or ()
        names = [item[0] for item in desc]
        return HybridRow(names, row)
    def fetchone(self):
        if self._closed: return None
        try: return self._row(self._cursor.fetchone())
        finally: self.close()
    def fetchall(self):
        if self._closed: return []
        try: return [self._row(row) for row in self._cursor.fetchall()]
        finally: self.close()
    def fetchmany(self, size=None):
        if self._closed: return []
        try:
            rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
            return [self._row(row) for row in rows]
        finally: self.close()
    def close(self):
        if self._closed: return
        self._closed = True
        try: self._cursor.close()
        finally: self._owner._cursors.discard(self)

class MySQLConnectionFacade:
    def __init__(self, connection):
        self._connection = connection
        self._cursors = set()
        self._closed = False
    def execute(self, sql, params=()):
        cur = self._connection.cursor()
        wrapper = MySQLCursorFacade(cur, self)
        try: return wrapper.execute(sql, params)
        except Exception:
            wrapper.close()
            raise
    def executemany(self, sql, seq_params):
        cur = self._connection.cursor()
        wrapper = MySQLCursorFacade(cur, self)
        try: return wrapper.executemany(sql, seq_params)
        except Exception:
            wrapper.close()
            raise
    def executescript(self, _sql):
        raise MySQLRuntimeError("executescript is not supported; apply a reviewed MySQL schema separately")
    def cursor(self):
        return MySQLCursorFacade(self._connection.cursor(), self)
    def commit(self): self._connection.commit()
    def rollback(self): self._connection.rollback()
    def close(self):
        if self._closed: return
        self._closed = True
        for cur in tuple(self._cursors): cur.close()
        self._connection.close()
    def __enter__(self):
        if self._closed: raise MySQLRuntimeError("Connection is closed")
        return self
    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None: self.commit()
            else: self.rollback()
        finally: self.close()
        return False


def connect_test_database(app_dir, connector=None, profile=None):
    """Connect only to the isolated test database; never to production."""
    from pathlib import Path
    from mysql_secure_config import load_config
    cfg = load_config(Path(app_dir), require_password=True, enforce_test_db=True, profile=profile)
    if connector is None:
        try: import mysql.connector as connector
        except ImportError as exc: raise MySQLRuntimeError("mysql-connector-python is not installed") from exc
    raw = connector.connect(**cfg, connection_timeout=5, autocommit=False)
    return MySQLConnectionFacade(raw)
