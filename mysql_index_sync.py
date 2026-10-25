# -*- coding: utf-8 -*-
"""Optional MySQL metadata index mirror. PDF bytes remain outside MySQL."""
import json, sqlite3
from pathlib import Path
LOG_NAME='mysql_index_sync.log'
SCHEMA_SQL = [
"CREATE TABLE IF NOT EXISTS archive_index (document_id BIGINT PRIMARY KEY, cabinet_id BIGINT, cabinet_name VARCHAR(255), doc_type VARCHAR(40), document_number VARCHAR(255), document_date VARCHAR(32), subject TEXT, sender_recipient TEXT, employee_name TEXT, keywords TEXT, notes LONGTEXT, original_name VARCHAR(1024), stored_name VARCHAR(255), mime_type VARCHAR(255), file_size BIGINT, sha256 CHAR(64), created_by VARCHAR(190), created_at VARCHAR(32), updated_at VARCHAR(32), indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, INDEX idx_archive_number (document_number), INDEX idx_archive_date (document_date), INDEX idx_archive_sha (sha256)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
"CREATE TABLE IF NOT EXISTS archive_index_fields (document_id BIGINT NOT NULL, field_name VARCHAR(190) NOT NULL, field_value LONGTEXT, PRIMARY KEY(document_id,field_name), INDEX idx_archive_field_name(field_name), CONSTRAINT fk_archive_index_fields_document FOREIGN KEY(document_id) REFERENCES archive_index(document_id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
]
def _log(app_dir, message):
    try:
        with (Path(app_dir)/LOG_NAME).open('a',encoding='utf-8') as f: f.write(str(message)+'\n')
    except Exception: pass
def _connect(app_dir):
    cfgp=Path(app_dir)/'mysql_config.json'
    if not cfgp.is_file(): return None
    import mysql.connector
    cfg=json.loads(cfgp.read_text(encoding='utf-8'))
    conn=mysql.connector.connect(**cfg,connection_timeout=5,autocommit=False)
    cur=conn.cursor()
    for sql in SCHEMA_SQL: cur.execute(sql)
    cur.close(); conn.commit()
    return conn
def sync_document(document_id, app_dir):
    app_dir=Path(app_dir); dbpath=app_dir/'docuware_archive.db'
    if not (app_dir/'mysql_config.json').is_file() or not dbpath.is_file(): return False
    conn=None
    try:
        src=sqlite3.connect(str(dbpath)); src.row_factory=sqlite3.Row
        row=src.execute('SELECT d.*,c.name AS cabinet_name FROM local_documents d LEFT JOIN local_cabinets c ON c.id=d.cabinet_id WHERE d.id=?',(int(document_id),)).fetchone()
        fields=src.execute('SELECT field_name,field_value FROM local_document_fields WHERE document_id=?',(int(document_id),)).fetchall() if row else []
        src.close()
        if not row: return delete_index_record(document_id,app_dir)
        conn=_connect(app_dir)
        if conn is None: return False
        cur=conn.cursor()
        vals=[row[k] for k in ('id','cabinet_id','cabinet_name','doc_type','document_number','document_date','subject','sender_recipient','employee_name','keywords','notes','original_name','stored_name','mime_type','file_size','sha256','created_by','created_at','updated_at')]
        sql="INSERT INTO archive_index(document_id,cabinet_id,cabinet_name,doc_type,document_number,document_date,subject,sender_recipient,employee_name,keywords,notes,original_name,stored_name,mime_type,file_size,sha256,created_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE cabinet_id=VALUES(cabinet_id),cabinet_name=VALUES(cabinet_name),doc_type=VALUES(doc_type),document_number=VALUES(document_number),document_date=VALUES(document_date),subject=VALUES(subject),sender_recipient=VALUES(sender_recipient),employee_name=VALUES(employee_name),keywords=VALUES(keywords),notes=VALUES(notes),original_name=VALUES(original_name),stored_name=VALUES(stored_name),mime_type=VALUES(mime_type),file_size=VALUES(file_size),sha256=VALUES(sha256),created_by=VALUES(created_by),updated_at=VALUES(updated_at)"
        cur.execute(sql,vals)
        cur.execute('DELETE FROM archive_index_fields WHERE document_id=%s',(int(document_id),))
        if fields: cur.executemany('INSERT INTO archive_index_fields(document_id,field_name,field_value) VALUES(%s,%s,%s)',[(int(document_id),x['field_name'],x['field_value']) for x in fields])
        conn.commit(); cur.close(); conn.close(); return True
    except Exception as e:
        _log(app_dir,'SYNC '+str(document_id)+': '+repr(e))
        try:
            if conn: conn.rollback(); conn.close()
        except Exception: pass
        return False
def delete_index_record(document_id, app_dir):
    app_dir=Path(app_dir)
    if not (app_dir/'mysql_config.json').is_file(): return False
    conn=None
    try:
        conn=_connect(app_dir)
        if conn is None: return False
        cur=conn.cursor(); cur.execute('DELETE FROM archive_index WHERE document_id=%s',(int(document_id),)); conn.commit(); cur.close(); conn.close(); return True
    except Exception as e:
        _log(app_dir,'DELETE INDEX '+str(document_id)+': '+repr(e))
        try:
            if conn: conn.rollback(); conn.close()
        except Exception: pass
        return False
def rebuild_index(app_dir):
    """Resync all local document metadata into the configured MySQL index."""
    app_dir=Path(app_dir); dbpath=app_dir/'docuware_archive.db'
    if not dbpath.is_file() or not (app_dir/'mysql_config.json').is_file(): return (0,0)
    src=sqlite3.connect(str(dbpath))
    try: ids=[r[0] for r in src.execute('SELECT id FROM local_documents ORDER BY id').fetchall()]
    finally: src.close()
    ok=0; failed=0
    for did in ids:
        if sync_document(did,app_dir): ok+=1
        else: failed+=1
    return ok,failed
