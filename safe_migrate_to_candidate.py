# -*- coding: utf-8 -*-
"""Safe SQLite -> reviewed MySQL candidate migration, TEST DATABASE ONLY.

Default is a read-only dry run. Execution requires an exact target confirmation,
checks that the target contains only empty candidate tables, creates a consistent
SQLite backup, installs the reviewed schema, copies rows in FK order, and verifies counts.
It never drops/truncates tables and refuses missing or hash-mismatched external files.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, sys
from pathlib import Path
from mysql_migration_gate import extract_create_tables
from mysql_schema_manager import ensure_schema, SchemaPreflightError
from mysql_secure_config import load_config

APP_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE = APP_DIR / 'docuware_archive.db'
DEFAULT_SCHEMA = APP_DIR / 'MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql'

def qid(name: str) -> str:
    if not name or not all(ch.isalnum() or ch == '_' for ch in name):
        raise ValueError('Unsafe SQL identifier: ' + repr(name))
    return '`' + name + '`'

def validate_target(target: str, confirmation: str = '') -> str:
    target = str(target or '').strip()
    if target.casefold() == 'salah_archive':
        raise ValueError('SAFETY STOP: original database salah_archive is protected.')
    if target.casefold() != 'salah_archive_test':
        raise ValueError('SAFETY STOP: only salah_archive_test is permitted in this build.')
    if confirmation and confirmation != target:
        raise ValueError('SAFETY STOP: confirmation does not exactly match the configured test database.')
    return target

def schema_tables(schema_path=DEFAULT_SCHEMA):
    text = Path(schema_path).read_text(encoding='utf-8')
    tables = extract_create_tables(text)
    if not tables: raise ValueError('No candidate CREATE TABLE statements were found.')
    return tables

def source_tables(src):
    result = {}
    rows = src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    for row in rows:
        name = row[0]
        columns = [r[1] for r in src.execute('PRAGMA table_info(' + qid(name) + ')').fetchall()]
        result[name] = columns
    return result

def verify_source_schema(src, candidate):
    actual = source_tables(src)
    errors=[]
    for table, cols in actual.items():
        if table not in candidate:
            errors.append(f'جدول SQLite غير موجود في مخطط MySQL المرشح: {table}')
            continue
        missing = sorted(set(c.lower() for c in cols) - set(candidate[table]))
        if missing: errors.append(f'{table}: أعمدة غير موجودة في مخطط MySQL: {", ".join(missing)}')
    return actual, errors

def verify_external_files(src, files_dir):
    files_dir = Path(files_dir)
    problems=[]; checked=0
    for table in ('local_documents','scan_inbox','local_case_attachments'):
        try: cols={r[1] for r in src.execute('PRAGMA table_info(' + qid(table) + ')').fetchall()}
        except sqlite3.Error: continue
        if 'stored_name' not in cols: continue
        selected=['stored_name']
        if 'sha256' in cols: selected.append('sha256')
        if 'file_size' in cols: selected.append('file_size')
        query='SELECT '+', '.join(qid(c) for c in selected)+' FROM '+qid(table)
        for row in src.execute(query):
            name=row[0]
            if not name: continue
            checked+=1; path=files_dir / str(name)
            if not path.is_file():
                problems.append(f'{table}: الملف غير موجود: {name}'); continue
            if 'sha256' in selected:
                expected=row[selected.index('sha256')]
                if expected:
                    h=hashlib.sha256()
                    with path.open('rb') as f:
                        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
                    if h.hexdigest().lower()!=str(expected).lower():
                        problems.append(f'{table}: بصمة SHA-256 غير مطابقة: {name}')
            if 'file_size' in selected:
                size=row[selected.index('file_size')]
                if size is not None and int(size or 0)!=path.stat().st_size:
                    problems.append(f'{table}: حجم الملف لا يطابق السجل: {name}')
    return {'checked_files':checked,'problems':problems}

def create_consistent_backup(src, backup_path):
    backup_path=Path(backup_path)
    if backup_path.exists(): raise FileExistsError('Backup already exists; refusing to overwrite: '+str(backup_path))
    dst=sqlite3.connect(str(backup_path))
    try:
        src.backup(dst); dst.commit()
    except Exception:
        dst.close()
        try: backup_path.unlink()
        except OSError: pass
        raise
    else: dst.close()
    return backup_path

def inspect_target(conn, candidate_names):
    cur=conn.cursor()
    try:
        cur.execute('SELECT DATABASE()'); row=cur.fetchone(); target=row[0] if row else ''
        validate_target(target)
        cur.execute('SHOW TABLES'); existing={str(r[0]) for r in cur.fetchall()}
        unexpected=sorted(existing-set(candidate_names))
        if unexpected: raise ValueError('SAFETY STOP: unexpected tables in target: '+', '.join(unexpected))
        populated=[]
        for table in sorted(existing):
            cur.execute('SELECT COUNT(*) FROM '+qid(table)); count=int(cur.fetchone()[0])
            if count: populated.append(f'{table}={count}')
        if populated: raise ValueError('SAFETY STOP: target contains data; no migration was started: '+', '.join(populated))
        return existing
    finally: cur.close()

def copy_rows(src, conn, source_schema, candidate_names, batch_size=500):
    cur=conn.cursor(); counts={}
    try:
        # Candidate schema order is dependency-aware (parents precede foreign-key children).
        order=list(candidate_names)
        for table in order:
            if table not in source_schema: continue
            columns=source_schema[table]
            if not columns: counts[table]=0; continue
            select='SELECT '+', '.join(qid(c) for c in columns)+' FROM '+qid(table)
            insert='INSERT INTO '+qid(table)+' ('+', '.join(qid(c) for c in columns)+') VALUES ('+', '.join(['%s']*len(columns))+')'
            batch=[]; source_count=0
            for row in src.execute(select):
                batch.append(tuple(row[c] for c in columns)); source_count+=1
                if len(batch)>=batch_size:
                    cur.executemany(insert,batch); batch=[]
            if batch: cur.executemany(insert,batch)
            cur.execute('SELECT COUNT(*) FROM '+qid(table)); target_count=int(cur.fetchone()[0])
            if target_count!=source_count:
                raise RuntimeError(f'Row count mismatch in {table}: SQLite={source_count}, MySQL={target_count}')
            counts[table]=target_count
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        raise
    finally: cur.close()

def dry_run(sqlite_path, schema_path, files_dir):
    db=Path(sqlite_path)
    if not db.is_file(): raise FileNotFoundError('SQLite database not found: '+str(db))
    candidate=schema_tables(schema_path)
    src=sqlite3.connect(str(db)); src.row_factory=sqlite3.Row
    try:
        actual,errors=verify_source_schema(src,candidate)
        file_report=verify_external_files(src,files_dir)
        counts={t:int(src.execute('SELECT COUNT(*) FROM '+qid(t)).fetchone()[0]) for t in actual}
        return {'status':'BLOCKED' if errors or file_report['problems'] else 'DRY_RUN_PASS','sqlite':str(db),'target_database':'salah_archive_test','source_tables':len(actual),'candidate_tables':len(candidate),'row_counts':counts,'schema_errors':errors,'external_files':file_report,'execution_performed':False}
    finally: src.close()

def execute_migration(sqlite_path, schema_path, files_dir, config_dir, confirmation):
    report=dry_run(sqlite_path,schema_path,files_dir)
    if report['schema_errors'] or report['external_files']['problems']:
        raise ValueError('SAFETY STOP: source/schema or external-file preflight failed. No MySQL writes attempted. See report.')
    if confirmation!='salah_archive_test':
        raise ValueError('SAFETY STOP: --confirm-target-database salah_archive_test is required.')
    cfg=load_config(config_dir,require_password=True,enforce_test_db=True)
    validate_target(cfg['database'],confirmation)
    try: import mysql.connector
    except ImportError as exc: raise RuntimeError('mysql-connector-python is required on the target Windows machine.') from exc
    conn=mysql.connector.connect(**cfg,connection_timeout=8,autocommit=False)
    source=None; backup=None
    try:
        candidate=schema_tables(schema_path)
        inspect_target(conn,set(candidate))
        source=sqlite3.connect(str(sqlite_path)); source.row_factory=sqlite3.Row
        backup_path=Path(str(sqlite_path)+'.pre_mysql_backup')
        create_consistent_backup(source,backup_path)
        backup=backup_path
        # Use the snapshot for all copied rows, not the changing live SQLite file.
        source.close(); source=sqlite3.connect(str(backup)); source.row_factory=sqlite3.Row
        actual,errors=verify_source_schema(source,candidate)
        if errors: raise ValueError('Snapshot schema changed after preflight: '+'; '.join(errors))
        snapshot_files=verify_external_files(source,files_dir)
        if snapshot_files['problems']:
            raise ValueError('SAFETY STOP: external files changed or are missing in the consistent snapshot: '+'; '.join(snapshot_files['problems'][:20]))
        ensure_schema(conn,schema_path)
        counts=copy_rows(source,conn,actual,list(candidate))
        return {'status':'MIGRATION_DATA_COPIED','target_database':cfg['database'],'backup':str(backup),'row_counts':counts,'source_tables':len(actual),'candidate_tables':len(candidate),'execution_performed':True,'note':'MySQL DDL/data transfer completed, but application runtime still requires official integration/signing and live workflow verification.'}
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        if source is not None: source.close()
        conn.close()

def main():
    ap=argparse.ArgumentParser(description='Safe migration to reviewed MySQL candidate; test database only.')
    ap.add_argument('--sqlite',default=str(DEFAULT_SQLITE))
    ap.add_argument('--schema',default=str(DEFAULT_SCHEMA))
    ap.add_argument('--files',default=str(APP_DIR/'local_archive_files'))
    ap.add_argument('--config-dir',default=str(APP_DIR))
    ap.add_argument('--execute',action='store_true',help='Copy data only after all safety checks pass')
    ap.add_argument('--confirm-target-database',default='')
    ap.add_argument('--report',default=str(APP_DIR/'MYSQL_SAFE_MIGRATION_PREFLIGHT.json'))
    args=ap.parse_args()
    try:
        if args.execute:
            report=execute_migration(args.sqlite,args.schema,args.files,args.config_dir,args.confirm_target_database)
        else:
            report=dry_run(args.sqlite,args.schema,args.files)
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if report['status']=='BLOCKED': sys.exit(2)
    except Exception as exc:
        error={'status':'BLOCKED','error':str(exc),'execution_performed':False}
        try: Path(args.report).write_text(json.dumps(error,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        except Exception: pass
        print(json.dumps(error,ensure_ascii=False,indent=2),file=sys.stderr)
        sys.exit(2)
if __name__=='__main__': main()
