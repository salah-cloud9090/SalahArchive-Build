# -*- coding: utf-8 -*-
"""Live integration test for the isolated MySQL test DB only."""
from __future__ import annotations
import datetime, hashlib, json, os, secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / ('MYSQL_LIVE_INTEGRATION_RESULT_' + os.environ.get('SALAH_ARCHIVE_DB_PROFILE', 'local').upper() + '.json')

def write_report(status, profile, passed, detail, cleanup_errors):
    report = {
        'version': '15.81', 'status': status,
        'timestamp_local': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'profile': profile, 'database': 'salah_archive_test',
        'passed_checks': list(passed), 'detail': detail,
        'cleanup_errors': list(cleanup_errors),
        'production_database_opened': False,
        'password_written_to_report': False,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main() -> int:
    os.environ['SALAH_ARCHIVE_DB_BACKEND'] = 'mysql'
    profile = os.environ.get('SALAH_ARCHIVE_DB_PROFILE', 'local')
    token = secrets.token_hex(8)
    cabinet_name = '__V1581_TEST_CABINET_' + token
    doc_number = '__V1581_TEST_DOC_' + token
    case_number = '__V1581_TEST_CASE_' + token
    rollback_name = '__V1581_TEST_ROLLBACK_' + token
    app = None
    db_ready = False
    file_path = None
    cabinet_id = document_id = case_id = None
    passed = []
    cleanup_errors = []
    status = 'BLOCKED'
    detail = ''
    exit_code = 3
    try:
        from integrity_guard import verify_integrity
        ok, integrity_detail = verify_integrity(ROOT)
        if not ok:
            raise RuntimeError('signed base integrity check failed: ' + integrity_detail)
        from mysql_secure_config import load_config
        cfg = load_config(ROOT, require_password=True, enforce_test_db=True)
        if cfg['database'] != 'salah_archive_test':
            raise RuntimeError('only salah_archive_test is permitted')
        import main_mysql_candidate_v15_81 as app_module
        app = app_module
        # Real application startup path: schema preflight, default data, admin bootstrap.
        app.initialize()
        db_ready = True
        passed.append('application initialize + reviewed schema preflight')
        file_path = app.FILES_DIR / ('__v1581_test_' + token + '.txt')
        payload = ('اختبار الأرشفة العربية ' + token + '\n').encode('utf-8')
        file_path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        with app.db() as conn:
            cabinets = conn.execute('SELECT id,name FROM local_cabinets ORDER BY id').fetchall()
            if len(cabinets) < 3:
                raise AssertionError('default cabinets were not initialized')
            cur = conn.execute('INSERT INTO local_cabinets(name,description) VALUES(?,?)', (cabinet_name, 'temporary integration test'))
            cabinet_id = cur.lastrowid
            cur = conn.execute(
                'INSERT INTO local_documents (cabinet_id,doc_type,document_number,document_date,subject,sender_recipient,original_name,stored_name,mime_type,file_size,sha256,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (cabinet_id,'incoming',doc_number,'24/10/2026','موضوع عربي أولي','جهة اختبار',file_path.name,file_path.name,'text/plain',len(payload),digest,'integration-test'))
            document_id = cur.lastrowid
            row = conn.execute('SELECT id,document_number,subject,sha256 FROM local_documents WHERE id=?',(document_id,)).fetchone()
            assert row and row['document_number']==doc_number and row['subject']=='موضوع عربي أولي' and row['sha256']==digest
        passed.append('insert/select Arabic metadata + SHA-256 file check')

        with app.db() as conn:
            conn.execute('UPDATE local_documents SET subject=? WHERE id=?', ('موضوع بعد التعديل',document_id))
            found = conn.execute('SELECT id FROM local_documents WHERE document_number LIKE ?',(doc_number,)).fetchone()
            assert found and found['id']==document_id
            conn.execute('INSERT INTO local_document_fields(document_id,field_name,field_value) VALUES(?,?,?)',(document_id,'جهة الاختبار','مديرية الجنسية والمعلومات المدنية'))
            field = conn.execute('SELECT field_value FROM local_document_fields WHERE document_id=? AND field_name=?',(document_id,'جهة الاختبار')).fetchone()
            assert field and field['field_value']=='مديرية الجنسية والمعلومات المدنية'
        passed.append('update + search + dynamic archive field')

        with app.db() as conn:
            cur = conn.execute('INSERT INTO local_cases(case_number,title,case_type,status,priority,created_by) VALUES(?,?,?,?,?,?)',(case_number,'معاملة اختبار','administrative','open','normal','integration-test'))
            case_id = cur.lastrowid
            conn.execute('INSERT INTO local_case_documents(case_id,document_id,linked_by) VALUES(?,?,?)',(case_id,document_id,'integration-test'))
            conn.execute('INSERT INTO local_case_attachments(case_id,original_name,stored_name,mime_type,file_size,notes,added_by) VALUES(?,?,?,?,?,?,?)',(case_id,file_path.name,file_path.name,'text/plain',len(payload),'temporary integration attachment','integration-test'))
            link = conn.execute('SELECT document_id FROM local_case_documents WHERE case_id=?',(case_id,)).fetchone()
            attach = conn.execute('SELECT stored_name,file_size FROM local_case_attachments WHERE case_id=?',(case_id,)).fetchone()
            assert link and link['document_id']==document_id
            assert attach and attach['stored_name']==file_path.name and attach['file_size']==len(payload)
        passed.append('case link + attachment metadata + real file on disk')

        try:
            with app.db() as conn:
                conn.execute('INSERT INTO local_cabinets(name,description) VALUES(?,?)',(rollback_name,'must roll back'))
                raise RuntimeError('intentional rollback probe')
        except RuntimeError as exc:
            if str(exc) != 'intentional rollback probe': raise
        with app.db() as conn:
            absent = conn.execute('SELECT id FROM local_cabinets WHERE name=?',(rollback_name,)).fetchone()
            assert absent is None
        passed.append('transaction rollback')

        with app.db() as conn:
            if case_id is not None: conn.execute('DELETE FROM local_cases WHERE id=?',(case_id,))
            if document_id is not None: conn.execute('DELETE FROM local_documents WHERE id=?',(document_id,))
            if cabinet_id is not None: conn.execute('DELETE FROM local_cabinets WHERE id=?',(cabinet_id,))
            conn.execute('DELETE FROM local_cabinets WHERE name=?',(rollback_name,))
        with app.db() as conn:
            assert conn.execute('SELECT id FROM local_documents WHERE id=?',(document_id,)).fetchone() is None
            assert conn.execute('SELECT id FROM local_cabinets WHERE id=?',(cabinet_id,)).fetchone() is None
        passed.append('delete + foreign-key cascade verification')
        status = 'PASS'
        detail = 'All live integration checks passed on the isolated test database.'
        exit_code = 0
    except Exception as exc:
        status = 'FAIL' if app is not None else 'BLOCKED'
        detail = type(exc).__name__ + ': ' + str(exc)
        exit_code = 1 if app is not None else 3
    finally:
        if app is not None and db_ready:
            try:
                with app.db() as conn:
                    if case_id is not None: conn.execute('DELETE FROM local_cases WHERE id=?',(case_id,))
                    if document_id is not None: conn.execute('DELETE FROM local_documents WHERE id=?',(document_id,))
                    if cabinet_id is not None: conn.execute('DELETE FROM local_cabinets WHERE id=?',(cabinet_id,))
                    conn.execute('DELETE FROM local_cabinets WHERE name=?',(rollback_name,))
            except Exception as cleanup_exc:
                cleanup_errors.append(type(cleanup_exc).__name__ + ': ' + str(cleanup_exc))
        if file_path is not None:
            try: file_path.unlink(missing_ok=True)
            except OSError as cleanup_exc: cleanup_errors.append('file cleanup: ' + str(cleanup_exc))
        if cleanup_errors and status == 'PASS':
            status = 'FAIL_CLEANUP'; detail += ' Cleanup needs review.'; exit_code = 1
        try: write_report(status, profile, passed, detail, cleanup_errors)
        except Exception as report_exc:
            print('WARNING: could not write integration report:', str(report_exc))
    print(f'MySQL live integration status: {status}')
    print('Profile:', profile, '| Database: salah_archive_test')
    for item in passed: print('PASS:', item)
    if detail: print('Details:', detail)
    for item in cleanup_errors: print('CLEANUP WARNING:', item)
    print('Report:', REPORT_PATH.name)
    print('Safety: production database was not opened.')
    return exit_code

if __name__ == '__main__':
    raise SystemExit(main())
