# -*- coding: utf-8 -*-
"""Isolated SQLite repository pilot; deliberately not wired into main.py."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

class SQLiteRepository:
    """Repository adapter around a caller-owned sqlite3 connection."""
    def __init__(self, connection: sqlite3.Connection):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("SQLiteRepository requires a sqlite3.Connection")
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        return self.connection.execute(sql, tuple(params))

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[dict[str, Any]]:
        row = self.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.execute(sql, params).fetchall()]

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        cursor = self.execute(sql, params)
        if cursor.lastrowid is None:
            raise RuntimeError("The statement did not provide a generated row id")
        return int(cursor.lastrowid)

    @contextmanager
    def transaction(self) -> Iterator["SQLiteRepository"]:
        with self.connection:
            yield self

    def close(self) -> None:
        """Close the connection only when explicitly requested by the caller."""
        self.connection.close()
