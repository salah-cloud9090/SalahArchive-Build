# -*- coding: utf-8 -*-
"""Safe, explicit migration of all SQLite tables to a pre-created MySQL database.
Default is dry-run. Run with --execute only after reviewing output and making backups.
The app remains SQLite-backed until its database access layer is switched and tested.
"""
import argparse, json, os, sqlite3, sys
from pathlib import Path
APP_DIR=Path(__file__).resolve().parent
DB_PATH=APP_DIR/'docuware_archive.db'
CFG=APP_DIR/'mysql_config.json'

def qid(s): return '`'+s.replace('`','``')+'`'

def validate_target(target, confirmation):
    target = str(target or '').strip()
    confirmation = str(confirmation or '').strip()
    if not target:
        raise ValueError('MySQL config must contain a database name.')
    if target.casefold() == 'salah_archive':
        raise ValueError('SAFETY STOP: refusing migration into the protected original database salah_archive.')
    # This continuation is deliberately scoped to the isolated test database.
    if target.casefold() != 'salah_archive_test':
        raise ValueError('SAFETY STOP: this build only permits the isolated test database salah_archive_test.')
    if confirmation != target:
        raise ValueError('SAFETY STOP: --execute requires --confirm-target-database with an exact match to the configured database ('+target+'). No migration was started.')
    return target


def create_sqlite_backup(src, backup_path):
    # SQLite's backup API includes committed WAL state; a raw file copy may not.
    if backup_path.exists():
        raise FileExistsError('Backup already exists; refusing to overwrite: '+str(backup_path))
    dst = sqlite3.connect(str(backup_path))
    try:
        src.backup(dst)
        dst.commit()
    except Exception:
        dst.close()
        try: backup_path.unlink()
        except OSError: pass
        raise
    else:
        dst.close()
    return backup_path

def mysql_type(decl, pk=False, name='', default=None):
    d=(decl or '').upper()
    if pk: return 'BIGINT NOT NULL AUTO_INCREMENT'
    if default and ("datetime('now')" in str(default).lower() or 'current_timestamp' in str(default).lower()): return 'DATETIME'
    if 'INT' in d: return 'BIGINT'
    if 'REAL' in d or 'FLOA' in d or 'DOUB' in d: return 'DOUBLE'
    if 'BLOB' in d: return 'LONGBLOB'
    if 'CHAR' in d or 'CLOB' in d: return 'VARCHAR(512)' if 'CHAR' in d else 'LONGTEXT'
    return 'LONGTEXT'
def get_schema(src):
    tables=[]
    for row in src.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        name=row['name']; info=src.execute(f'PRAGMA table_info({qid(name)})').fetchall()
        if not info: continue
        cols=[]; pkcols=[]
        for c in info:
            pk=bool(c['pk'])
            if pk: pkcols.append((c['pk'],c['name']))
            typ=mysql_type(c['type'], pk and len([x for x in info if x['pk']])==1 and c['name']=='id', c['name'], c['dflt_value'])
            col=qid(c['name'])+' '+typ
            if c['notnull'] and not pk: col+=' NOT NULL'
            default=c['dflt_value']
            if default and not (pk and 'AUTO_INCREMENT' in typ):
                dv=str(default).strip()
                if dv.lower() in ("datetime('now')", "current_timestamp") or dv.lower()=='current_timestamp':
                    dv='CURRENT_TIMESTAMP'; col=col.replace(' LONGTEXT',' DATETIME').replace(' VARCHAR(512)',' DATETIME')
                elif dv.upper() in ('NULL','TRUE','FALSE') or dv.replace('.','',1).lstrip('-').isdigit(): pass
                elif dv.startswith("'") and dv.endswith("'"): dv=dv.replace("'","''")
                else: dv="'"+dv.replace("'","''")+"'"
                col+=' DEFAULT '+dv
            cols.append(col)
        if pkcols and not any('AUTO_INCREMENT' in c for c in cols):
            pkcols.sort(); cols.append('PRIMARY KEY ('+', '.join(qid(n) for _,n in pkcols)+')')
        elif pkcols and any('AUTO_INCREMENT' in c for c in cols):
            cols.append('PRIMARY KEY ('+', '.join(qid(n) for _,n in sorted(pkcols))+')')
        # Preserve foreign-key relationships where possible.
        fkrows=src.execute(f'PRAGMA foreign_key_list({qid(name)})').fetchall()
        grouped={}
        for fk in fkrows: grouped.setdefault(fk['id'],[]).append(fk)
        for group in grouped.values():
            group.sort(key=lambda x:x['seq']); first=group[0]
            cols.append('FOREIGN KEY ('+', '.join(qid(x['from']) for x in group)+') REFERENCES '+qid(first['table'])+' ('+', '.join(qid(x['to']) for x in group)+')')
        tables.append((name,info,cols))
    return tables

def schema_preflight(src):
    """Return incompatibilities we refuse to silently drop during conversion."""
    problems = []
    for row in src.execute("SELECT type,name,sql FROM sqlite_master WHERE type IN ('view','trigger') ORDER BY type,name"):
        problems.append(f"unsupported SQLite {row['type']}: {row['name']}")
    for row in src.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        table = row['name']; sql = (row['sql'] or '').upper()
        if 'CREATE VIRTUAL TABLE' in sql:
            problems.append(f"virtual table is unsupported: {table}")
        if 'CHECK' in sql and 'CHECK (' in sql:
            problems.append(f"CHECK constraints need explicit MySQL translation: {table}")
        if 'GENERATED ALWAYS' in sql:
            problems.append(f"generated columns need explicit MySQL translation: {table}")
        for ix in src.execute(f'PRAGMA index_list({qid(table)})').fetchall():
            ixname = ix['name']
            ix_sql_row = src.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (ixname,)).fetchone()
            ix_sql = (ix_sql_row['sql'] or '').upper() if ix_sql_row else ''
            if ' WHERE ' in ix_sql:
                problems.append(f"partial index needs explicit MySQL translation: {table}.{ixname}")
            cols = src.execute(f'PRAGMA index_info({qid(ixname)})').fetchall()
            if not cols or any(not c['name'] for c in cols):
                problems.append(f"expression/empty index needs explicit MySQL translation: {table}.{ixname}")
                continue
            info = src.execute(f'PRAGMA table_info({qid(table)})').fetchall()
            type_map = {c['name']: (c['type'] or '').upper() for c in info}
            key_bytes = 0
            for col in cols:
                typ = type_map.get(col['name'], '')
                if not typ or any(x in typ for x in ('TEXT','CLOB','BLOB')):
                    problems.append(f"index on long/unbounded column needs explicit MySQL translation: {table}.{ixname}.{col['name']}")
                    continue
                if 'CHAR' in typ:
                    import re
                    match = re.search(r'\((\d+)\)', typ)
                    key_bytes += (int(match.group(1)) if match else 512) * 4
                elif 'INT' in typ or 'REAL' in typ or 'FLOA' in typ or 'DOUB' in typ or 'NUM' in typ:
                    key_bytes += 8
                else:
                    key_bytes += 8
            if key_bytes > 3072:
                problems.append(f"index key may exceed MySQL InnoDB limit: {table}.{ixname}")
    return sorted(set(problems))

def main():
    ap=argparse.ArgumentParser(description='Migrate SQLite archive tables to MySQL; dry-run by default.')
    ap.add_argument('--execute',action='store_true',help='Perform migration after backup')
    ap.add_argument('--sqlite',default=str(DB_PATH),help='SQLite database path')
    ap.add_argument('--config',default=str(CFG),help='mysql_config.json path')
    ap.add_argument('--confirm-target-database', default='', help='Required with --execute; must exactly match the configured MySQL database name')
    args=ap.parse_args(); db=Path(args.sqlite); cfgp=Path(args.config)
    if not db.exists(): sys.exit('SQLite database not found: '+str(db))
    cfg=json.loads(cfgp.read_text(encoding='utf-8')) if cfgp.exists() else None
    src=sqlite3.connect(str(db)); src.row_factory=sqlite3.Row
    tables=get_schema(src)
    problems=schema_preflight(src)
    print('SQLite:',db)
    print('Tables to migrate:',len(tables))
    for name,_,_ in tables:
        n=src.execute(f'SELECT COUNT(*) FROM {qid(name)}').fetchone()[0]
        print(f'  {name}: {n} rows')
    print('Files in local_archive_files are not stored inside SQLite; keep/copy that folder separately.')
    if problems:
        print('SCHEMA PREFLIGHT BLOCKERS:')
        for problem in problems: print('  - '+problem)
        if args.execute:
            src.close(); sys.exit('SAFETY STOP: schema has unsupported constraints/indexes. No MySQL connection or writes were attempted.')
    else:
        print('Schema preflight: no known unsupported constructs found.')
    print('This helper migrates records/schema only; it does NOT switch main.py to MySQL automatically.')
    print('WARNING: MySQL integration cannot be certified until this schema is tested against the target MySQL 8.4 server.')
    if not args.execute:
        print('\nDRY RUN ONLY. Review table counts, back up the DB and file folder, then rerun with --execute.')
        src.close(); return
    if not cfg: sys.exit('MySQL config not found. Save/test MySQL settings in the app first.')
    # Safety gate: this package may write only to the explicitly isolated test DB.
    try:
        target=validate_target(cfg.get('database'), args.confirm_target_database)
    except ValueError as exc:
        sys.exit(str(exc))
    try:
        import mysql.connector
    except Exception:
        sys.exit('Install mysql-connector-python first: pip install mysql-connector-python')
    # Inspect target BEFORE making a backup or attempting any DDL.
    # Prefer an environment secret; never require a password literal in this helper.
    if os.environ.get('SALAH_MYSQL_PASSWORD'):
        cfg['password'] = os.environ['SALAH_MYSQL_PASSWORD']
    conn=mysql.connector.connect(**cfg, connection_timeout=10, autocommit=False)
    cur=conn.cursor()
    try:
        cur.execute('SHOW TABLES')
        existing={r[0] for r in cur.fetchall()}
        if existing:
            raise RuntimeError('SAFETY STOP: target database is not empty. No tables were changed. Existing tables: '+', '.join(sorted(existing)))
    except Exception:
        cur.close(); conn.close(); src.close(); raise
    backup=db.with_suffix(db.suffix+'.pre_mysql_backup')
    try:
        create_sqlite_backup(src, backup)
    except Exception:
        cur.close(); conn.close(); src.close(); raise
    print('Consistent SQLite backup created:',backup)
    try:
        # MySQL DDL may auto-commit; never drop or replace existing tables.
        # The target must be completely empty before schema creation begins.
        cur.execute('SET FOREIGN_KEY_CHECKS=0')
        for name,info,cols in tables:
            cur.execute('CREATE TABLE '+qid(name)+' ('+', '.join(cols)+') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci')
        # Preserve unique indexes and ordinary indexes.
        for name,info,_ in tables:
            for ix in src.execute(f'PRAGMA index_list({qid(name)})').fetchall():
                iname=ix['name']; colsix=src.execute(f'PRAGMA index_info({qid(iname)})').fetchall()
                names=[x['name'] for x in colsix if x['name']]
                if not names: continue
                kind='UNIQUE ' if ix['unique'] else ''
                idxname=('uniq_' if ix['unique'] else 'idx_')+name+'_'+iname
                cur.execute('CREATE '+kind+'INDEX '+qid(idxname[:60])+' ON '+qid(name)+' ('+', '.join(qid(x) for x in names)+')')
        conn.commit()
        for name,info,_ in tables:
            colnames=[x['name'] for x in info]
            select='SELECT '+', '.join(qid(x) for x in colnames)+' FROM '+qid(name)
            rows=src.execute(select).fetchall()
            if rows:
                placeholders=', '.join(['%s']*len(colnames))
                insert='INSERT INTO '+qid(name)+' ('+', '.join(qid(x) for x in colnames)+') VALUES ('+placeholders+')'
                batch=[]
                for row in rows:
                    batch.append(tuple(row[x] for x in colnames))
                    if len(batch)>=500: cur.executemany(insert,batch); batch=[]
                if batch: cur.executemany(insert,batch)
            cur.execute('SELECT COUNT(*) FROM '+qid(name)); mysql_count=cur.fetchone()[0]
            sqlite_count=src.execute('SELECT COUNT(*) FROM '+qid(name)).fetchone()[0]
            if mysql_count != sqlite_count: raise RuntimeError(f'Count mismatch in {name}: SQLite={sqlite_count}, MySQL={mysql_count}')
            print(f'VERIFIED {name}: {mysql_count} rows')
        conn.commit()
        print('\nMigration completed and row counts verified.')
        print('Original SQLite and backup were not deleted. Keep the attachment folder and verify file hashes.')
        print('Application still uses SQLite until the MySQL backend is explicitly enabled and tested.')
    except Exception:
        conn.rollback()
        print('Migration failed. MySQL DDL may have auto-committed; no existing target tables were dropped. Inspect the test database before retrying. SQLite backup remains at:',backup)
        raise
    finally:
        try: cur.execute('SET FOREIGN_KEY_CHECKS=1')
        except Exception: pass
        cur.close(); conn.close(); src.close()
if __name__=='__main__': main()
