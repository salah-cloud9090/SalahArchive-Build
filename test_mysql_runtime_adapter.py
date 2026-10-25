import unittest
from mysql_runtime_adapter import MySQLConnectionFacade, HybridRow, MySQLRuntimeError

class FakeCursor:
    def __init__(self, rows=(), lastrowid=7):
        self.rows=list(rows); self.description=(('id',),('name',)); self.lastrowid=lastrowid; self.rowcount=1; self.closed=False; self.executed=[]
    def execute(self, sql, params=()): self.executed.append((sql,params))
    def executemany(self, sql, params): self.executed.append((sql,params))
    def fetchone(self): return self.rows.pop(0) if self.rows else None
    def fetchall(self): rows=self.rows; self.rows=[]; return rows
    def fetchmany(self, size=1): rows=self.rows[:size]; self.rows=self.rows[size:]; return rows
    def close(self): self.closed=True
class FakeConnection:
    def __init__(self): self.cursors=[]; self.commits=0; self.rollbacks=0; self.closed=False
    def cursor(self): c=FakeCursor([(1,'أرشيف')]); self.cursors.append(c); return c
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1
    def close(self): self.closed=True

class RuntimeAdapterTests(unittest.TestCase):
    def setUp(self): self.raw=FakeConnection(); self.conn=MySQLConnectionFacade(self.raw)
    def test_question_mark_translation_and_parameters(self):
        cur=self.conn.execute('SELECT id,name FROM local_cabinets WHERE id=?',(1,))
        self.assertEqual(self.raw.cursors[0].executed[0],('SELECT id,name FROM local_cabinets WHERE id=%s',(1,)))
        self.assertEqual(cur.fetchone()['name'],'أرشيف')
        self.assertTrue(self.raw.cursors[0].closed)
    def test_row_supports_numeric_and_named_indexing(self):
        row=HybridRow(('id','name'),(2,'وارد'))
        self.assertEqual(row[0],2); self.assertEqual(row['name'],'وارد'); self.assertEqual(tuple(row),(2,'وارد'))
    def test_fetchall_wraps_rows_and_closes_cursor(self):
        self.raw.cursor=lambda: FakeCursor([(1,'أ'),(2,'ب')])
        cur=self.conn.execute('SELECT id,name FROM local_cabinets')
        rows=cur.fetchall()
        self.assertEqual([r['id'] for r in rows],[1,2]); self.assertTrue(cur._closed)
    def test_lastrowid_available_after_insert(self):
        cur=self.conn.execute('INSERT INTO local_cabinets(name) VALUES(?)',('أرشيف',))
        self.assertEqual(cur.lastrowid,7)
    def test_reviewed_replace_reassignment_translates_to_upsert(self):
        cur=self.conn.execute('INSERT OR REPLACE INTO scan_inbox_group_items(group_id,inbox_id) VALUES(?,?)',(4,8))
        self.assertEqual(self.raw.cursors[0].executed[0],('INSERT INTO scan_inbox_group_items(group_id,inbox_id) VALUES(%s,%s) ON DUPLICATE KEY UPDATE group_id=VALUES(group_id)',(4,8)))
        self.assertEqual(cur.lastrowid,7)

    def test_cursor_created_before_sql_error_is_closed(self):
        with self.assertRaises(MySQLRuntimeError):
            self.conn.execute('PRAGMA table_info(local_documents)')
        self.assertTrue(self.raw.cursors[0].closed)

    def test_duplicate_key_maps_to_sqlite_integrity_error_for_existing_handlers(self):
        class DuplicateKeyError(Exception):
            errno=1062
            sqlstate="23000"
        class ErrorCursor(FakeCursor):
            def execute(self, sql, params=()): raise DuplicateKeyError("Duplicate entry")
        self.raw.cursor=lambda: ErrorCursor()
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO local_cabinets(name) VALUES(?)", ("أرشيف",))

    def test_non_integrity_database_error_is_not_misclassified(self):
        class ConnectionLostError(Exception):
            errno=2013
            sqlstate="HY000"
        class ErrorCursor(FakeCursor):
            def execute(self, sql, params=()): raise ConnectionLostError("lost")
        self.raw.cursor=lambda: ErrorCursor()
        with self.assertRaises(ConnectionLostError):
            self.conn.execute("SELECT 1")

    def test_executescript_refused(self):
        with self.assertRaises(MySQLRuntimeError): self.conn.executescript('CREATE TABLE x(id INT)')
    def test_pragma_refused_not_translated(self):
        with self.assertRaises(MySQLRuntimeError): self.conn.execute('PRAGMA table_info(local_cabinets)')
    def test_context_commits_and_closes(self):
        with self.conn: pass
        self.assertEqual(self.raw.commits,1); self.assertTrue(self.raw.closed)
    def test_context_rolls_back_and_closes_on_exception(self):
        with self.assertRaises(ValueError):
            with self.conn: raise ValueError('test')
        self.assertEqual(self.raw.rollbacks,1); self.assertTrue(self.raw.closed)


    def test_connect_test_database_uses_selected_profile_and_profile_password(self):
        import json, os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from mysql_deployment_profiles import save_profiles
        from mysql_runtime_adapter import connect_test_database
        class Connector:
            def __init__(self): self.kwargs=None; self.raw=FakeConnection()
            def connect(self, **kwargs): self.kwargs=kwargs; return self.raw
        with tempfile.TemporaryDirectory() as d:
            save_profiles(Path(d), {
                'local': {'host':'127.0.0.1','port':3306,'database':'salah_archive_test','user':'local_test'},
                'server': {'host':'10.0.0.5','port':3306,'database':'salah_archive_test','user':'server_test'},
            })
            fake=Connector()
            env={'SALAH_ARCHIVE_DB_PROFILE':'server','SALAH_MYSQL_PASSWORD_SERVER':'server-secret'}
            with patch.dict(os.environ,env,clear=False):
                conn=connect_test_database(d,connector=fake)
            self.assertEqual(fake.kwargs['host'],'10.0.0.5')
            self.assertEqual(fake.kwargs['user'],'server_test')
            self.assertEqual(fake.kwargs['password'],'server-secret')
            self.assertEqual(fake.kwargs['database'],'salah_archive_test')
            conn.close()

    def test_runtime_connector_never_receives_production_database(self):
        import os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from mysql_deployment_profiles import save_profiles
        from mysql_runtime_adapter import connect_test_database
        class Connector:
            def __init__(self): self.kwargs=None; self.raw=FakeConnection()
            def connect(self, **kwargs): self.kwargs=kwargs; return self.raw
        with tempfile.TemporaryDirectory() as d:
            save_profiles(Path(d), {
                'local': {'host':'127.0.0.1','port':3306,'database':'salah_archive_test','user':'local_test'},
                'server': {'host':'10.0.0.5','port':3306,'database':'salah_archive_test','user':'server_test'},
            })
            fake=Connector()
            with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'local','SALAH_MYSQL_PASSWORD_LOCAL':'test-secret'},clear=False):
                conn=connect_test_database(d,connector=fake)
            self.assertEqual(fake.kwargs['database'],'salah_archive_test')
            self.assertNotEqual(fake.kwargs['database'],'salah_archive')
            conn.close()

if __name__=='__main__': unittest.main()
