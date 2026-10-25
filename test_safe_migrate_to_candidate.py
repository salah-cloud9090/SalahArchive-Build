import hashlib, sqlite3, tempfile, unittest
from pathlib import Path
from safe_migrate_to_candidate import validate_target, schema_tables, verify_source_schema, verify_external_files, create_consistent_backup, copy_rows

ROOT=Path(__file__).resolve().parent
class FakeCursor:
    def __init__(self, owner): self.owner=owner; self.row=None; self.rows=[]; self.closed=False
    def execute(self, sql, params=()):
        up=sql.upper()
        if 'SELECT COUNT(*) FROM `LOCAL_CABINETS`' in up: self.row=(len(self.owner.data['local_cabinets']),)
        elif 'SELECT DATABASE()' in up: self.row=(self.owner.database,)
        elif up.startswith('SHOW TABLES'): self.rows=[(x,) for x in self.owner.tables]
        elif 'SELECT COUNT(*) FROM' in up:
            table=sql.split('FROM',1)[1].strip().strip('`'); self.row=(len(self.owner.data.get(table,[])),)
        else: self.row=None
    def executemany(self, sql, rows):
        table=sql.split('INTO',1)[1].split('(',1)[0].strip().strip('`')
        self.owner.data.setdefault(table,[]).extend(list(rows))
    def fetchone(self): return self.row
    def fetchall(self): out=self.rows; self.rows=[]; return out
    def close(self): self.closed=True
class FakeConnection:
    def __init__(self): self.database='salah_archive_test'; self.tables=['local_cabinets']; self.data={'local_cabinets':[]}; self.commits=0; self.rollbacks=0
    def cursor(self): return FakeCursor(self)
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1

class SafeMigrationTests(unittest.TestCase):
    def test_only_test_database_is_allowed(self):
        self.assertEqual(validate_target('salah_archive_test','salah_archive_test'),'salah_archive_test')
        for target in ('salah_archive','production','other_db',''):
            with self.subTest(target=target), self.assertRaises(ValueError): validate_target(target,'salah_archive_test')
    def test_candidate_schema_contains_expected_archive_tables(self):
        tables=schema_tables(ROOT/'MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql')
        self.assertTrue({'local_cabinets','local_documents','scan_baskets','scan_inbox','local_case_attachments'} <= set(tables))
    def test_schema_preflight_detects_missing_columns(self):
        conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE local_cabinets (id INTEGER PRIMARY KEY, name TEXT, legacy_extra TEXT)')
        _,errors=verify_source_schema(conn,schema_tables(ROOT/'MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql'))
        self.assertTrue(any('legacy_extra' in x for x in errors)); conn.close()
    def test_external_file_preflight_detects_missing_or_wrong_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); file_dir=root/'files'; file_dir.mkdir(); (file_dir/'doc.pdf').write_bytes(b'actual')
            conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
            conn.execute('CREATE TABLE local_documents(stored_name TEXT, sha256 TEXT, file_size INTEGER)')
            conn.execute('INSERT INTO local_documents VALUES(?,?,?)',('doc.pdf','0'*64,6))
            conn.execute('INSERT INTO local_documents VALUES(?,?,?)',('missing.pdf','',0))
            result=verify_external_files(conn,file_dir)
            self.assertEqual(result['checked_files'],2); self.assertEqual(len(result['problems']),2); conn.close()
    def test_consistent_backup_uses_sqlite_backup_api(self):
        with tempfile.TemporaryDirectory() as d:
            src=sqlite3.connect(':memory:'); src.execute('CREATE TABLE t(v TEXT)'); src.execute("INSERT INTO t VALUES('ok')"); src.commit()
            backup=Path(d)/'backup.db'; create_consistent_backup(src,backup)
            out=sqlite3.connect(backup); self.assertEqual(out.execute('SELECT v FROM t').fetchone()[0],'ok'); out.close(); src.close()
    def test_copy_rows_uses_candidate_order_and_verifies_counts(self):
        src=sqlite3.connect(':memory:'); src.row_factory=sqlite3.Row
        src.execute('CREATE TABLE local_cabinets(id INTEGER PRIMARY KEY,name TEXT)')
        src.execute("INSERT INTO local_cabinets VALUES(1,'أرشيف')")
        conn=FakeConnection()
        counts=copy_rows(src,conn,{'local_cabinets':['id','name']},['local_cabinets'])
        self.assertEqual(counts,{'local_cabinets':1}); self.assertEqual(conn.data['local_cabinets'],[(1,'أرشيف')]); self.assertEqual(conn.commits,1)
        src.close()

if __name__=='__main__': unittest.main()
