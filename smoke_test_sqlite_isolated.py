# -*- coding: utf-8 -*-
"""Run a disposable SQLite startup + CRUD smoke test without touching user databases."""
from __future__ import annotations
import importlib.util
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = [
    ('main_mysql_candidate_v15_81.py', 'main.py'),
    ('document_tools.py', 'document_tools.py'),
    ('scanner_wia.py', 'scanner_wia.py'),
    ('license_core.py', 'license_core.py'),
    ('mysql_index_sync.py', 'mysql_index_sync.py'),
    ('mysql_runtime_adapter.py', 'mysql_runtime_adapter.py'),
    ('mysql_sql_compat.py', 'mysql_sql_compat.py'),
    ('mysql_secure_config.py', 'mysql_secure_config.py'),
    ('mysql_schema_manager.py', 'mysql_schema_manager.py'),
    ('mysql_deployment_profiles.py', 'mysql_deployment_profiles.py'),
]

def main():
    with tempfile.TemporaryDirectory(prefix='salah_archive_sqlite_smoke_') as raw:
        temp = Path(raw)
        for source, target in FILES:
            src = HERE / source
            if not src.is_file():
                raise SystemExit(f'Missing required candidate/dependency: {source}')
            shutil.copy2(src, temp / target)
        sys.path.insert(0, str(temp))
        try:
            spec = importlib.util.spec_from_file_location('salah_candidate_smoke', temp / 'main.py')
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            module.initialize()
            with module.db() as conn:
                cabinets = conn.execute('SELECT id,name FROM local_cabinets ORDER BY id').fetchall()
                if len(cabinets) < 3:
                    raise AssertionError(f'Expected default cabinets; got {len(cabinets)}')
                cabinet_id = cabinets[0]['id']
                cur = conn.execute(
                    'INSERT INTO local_documents(cabinet_id,doc_type,document_number,subject,original_name,stored_name,sha256) VALUES(?,?,?,?,?,?,?)',
                    (cabinet_id, 'incoming', 'SMOKE-001', 'اختبار تكاملي', 'smoke.pdf', 'smoke.bin', '0' * 64),
                )
                doc_id = cur.lastrowid
                row = conn.execute('SELECT id,document_number,subject FROM local_documents WHERE id=?', (doc_id,)).fetchone()
                assert row['document_number'] == 'SMOKE-001' and row['subject'] == 'اختبار تكاملي'
                conn.execute('UPDATE local_documents SET subject=? WHERE id=?', ('تعديل اختبار', doc_id))
                assert conn.execute('SELECT subject FROM local_documents WHERE id=?', (doc_id,)).fetchone()['subject'] == 'تعديل اختبار'
                conn.execute('DELETE FROM local_documents WHERE id=?', (doc_id,))
                assert conn.execute('SELECT id FROM local_documents WHERE id=?', (doc_id,)).fetchone() is None
            con = sqlite3.connect(temp / 'docuware_archive.db')
            table_count = len(con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
            con.close()
            print('PASS: isolated SQLite initialization')
            print(f'PASS: {len(cabinets)} default cabinets found')
            print('PASS: document insert / select / update / delete')
            print(f'PASS: disposable database created {table_count} tables')
            print('SAFE: temporary directory is deleted automatically; no user DB is opened')
        finally:
            sys.path.remove(str(temp))
            sys.modules.pop('salah_candidate_smoke', None)

if __name__ == '__main__':
    main()
