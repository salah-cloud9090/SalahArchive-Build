# -*- coding: utf-8 -*-
"""Isolated MySQL repository adapter for test-database-only migration work.

This module is not wired into main.py. It refuses connection configs that target
anything other than salah_archive_test and does not create or migrate schemas.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional, Sequence

from mysql_secure_config import load_config, MySQLConfigError
from mysql_sql_compat import translate_sql, SQLCompatibilityError


class MySQLRepositoryError(RuntimeError):
    """Raised when the MySQL adapter cannot safely execute an operation."""


class MySQLRepository:
    def __init__(self, connection: Any):
        self.connection = connection

    def execute(self, sql: str, params: Sequence[Any] = ()):
        translated = translate_sql(sql)
        try:
            cursor = self.connection.cursor(dictionary=True)
        except TypeError:
            cursor = self.connection.cursor()
        try:
            cursor.execute(translated, tuple(params))
        except Exception:
            try:
                cursor.close()
            except Exception:
                pass
            raise
        return cursor

    @staticmethod
    def _as_dict(row: Any, cursor: Any) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        if isinstance(row, Mapping):
            return dict(row)
        description = getattr(cursor, "description", None) or ()
        names = [col[0] for col in description]
        if not names:
            raise MySQLRepositoryError(
                "Driver returned tuple rows without cursor column metadata"
            )
        return dict(zip(names, row))

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[dict[str, Any]]:
        cursor = self.execute(sql, params)
        try:
            return self._as_dict(cursor.fetchone(), cursor)
        finally:
            cursor.close()

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        cursor = self.execute(sql, params)
        try:
            return [self._as_dict(row, cursor) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        cursor = self.execute(sql, params)
        try:
            lastrowid = getattr(cursor, "lastrowid", None)
            if lastrowid is None:
                raise MySQLRepositoryError("Statement did not return a generated row id")
            return int(lastrowid)
        finally:
            cursor.close()

    @contextmanager
    def transaction(self) -> Iterator["MySQLRepository"]:
        try:
            yield self
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def commit(self) -> None:
        """Expose the connection commit operation used by sqlite-style callers."""
        self.connection.commit()

    def rollback(self) -> None:
        """Expose rollback for explicit error recovery paths."""
        self.connection.rollback()

    def __enter__(self) -> "MySQLRepository":
        """Support ``with db() as connection`` transaction boundaries."""
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        return False

    def executescript(self, script: str) -> None:
        """Fail closed: multi-statement schema setup needs a reviewed migration."""
        raise SQLCompatibilityError(
            "executescript is not supported by the runtime adapter; use the reviewed MySQL schema manager"
        )

    def close(self) -> None:
        self.connection.close()


def connect_test_repository(app_dir, *, connector=None) -> MySQLRepository:
    """Connect only to the configured test DB; connector injection enables offline tests."""
    config = load_config(app_dir, require_password=True, enforce_test_db=True)
    if connector is None:
        try:
            import mysql.connector as connector
        except ImportError as exc:
            raise MySQLRepositoryError(
                "حزمة mysql-connector-python غير مثبتة؛ لم يتم إجراء أي اتصال."
            ) from exc
    try:
        connection = connector.connect(**config)
    except Exception as exc:
        raise MySQLRepositoryError("تعذر الاتصال بقاعدة اختبار MySQL.") from exc
    return MySQLRepository(connection)
