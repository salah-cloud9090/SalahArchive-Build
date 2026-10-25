# -*- coding: utf-8 -*-
"""Safe, explicit migration of all SQLite tables to a pre-created MySQL database.
Default is dry-run. Run with --execute only after reviewing output and making backups.
The app remains SQLite-backed until its database access layer is switched and tested.
"""
import argparse, json, shutil, sqlite3, sys
from pathlib import Path
APP_DIR=Path(__file__).resolve().parent
DB_PATH=APP_DIR/'docuware_archive.db'
CFG=APP_DIR/'mysql_config.json'

def qid(s): return '`'+s.replace('`','``')+'`'
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

def main():
    ap=argparse.ArgumentParser(description='Migrate SQLite archive tables to MySQL; dry-run by default.')
    ap.add_argument('--execute',action='store_true',help='Perform migration after backup')
    ap.add_argument('--sqlite',default=str(DB_PATH),help='SQLite database path')
    ap.add_argument('--config',default=str(CFG),help='mysql_config.json path')
    args=ap.parse_args(); db=Path(args.sqlite); cfgp=Path(args.config)
    if not db.exists(): sys.exit('SQLite database not found: '+str(db))
    cfg=json.loads(cfgp.read_text(encoding='utf-8')) if cfgp.exists() else None
    src=sqlite3.connect(str(db)); src.row_factory=sqlite3.Row
    tables=get_schema(src)
    print('SQLite:',db)
    print('Tables to migrate:',len(tables))
    for name,_,_ in tables:
        n=src.execute(f'SELECT COUNT(*) FROM {qid(name)}').fetchone()[0]
        print(f'  {name}: {n} rows')
    print('Files in local_archive_files are not stored inside SQLite; keep/copy that folder separately.')
    print('This script migrates records and schema. It does NOT switch main.py to MySQL automatically.')
    if not args.execute:
        print('\nDRY RUN ONLY. Review table counts, back up the DB and file folder, then rerun with --execute.')
        src.close(); return
    if not cfg: sys.exit('MySQL config not found. Save/test MySQL settings in the app first.')
    backup=db.with_suffix(db.suffix+'.pre_mysql_backup')
    if backup.exists(): sys.exit('Backup already exists; move it safely or choose another SQLite path: '+str(backup))
    shutil.copy2(db,backup)
    print('SQLite backup created:',backup)
    try:
        import mysql.connector
    except Exception: sys.exit('Install mysql-connector-python first: pip install mysql-connector-python')
    conn=mysql.connector.connect(**cfg, connection_timeout=10, autocommit=False)
    cur=conn.cursor()
    try:
        cur.execute('SET FOREIGN_KEY_CHECKS=0')
        # Refuse to overwrite existing populated tables.
        existing=set()
        cur.execute('SHOW TABLES')
        existing={r[0] for r in cur.fetchall()}
        for name,_,_ in tables:
            if name in existing:
                cur.execute('SELECT COUNT(*) FROM '+qid(name)); count=cur.fetchone()[0]
                if count: raise RuntimeError(f'MySQL table {name} already contains {count} rows; refusing to overwrite.')
        for name,info,cols in tables:
            if name in existing:
                cur.execute('DROP TABLE '+qid(name))
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
        print('Migration failed and MySQL transaction was rolled back where supported. SQLite backup remains at:',backup)
        raise
    finally:
        try: cur.execute('SET FOREIGN_KEY_CHECKS=1')
        except Exception: pass
        cur.close(); conn.close(); src.close()
if __name__=='__main__': main()
