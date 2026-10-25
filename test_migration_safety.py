"""Tests for the separate guarded migration helper; no MySQL connection is made."""
import hashlib
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
import safe_migrate_sqlite_to_mysql as migration


def test_exact_test_database_confirmation():
    assert migration.validate_target('salah_archive_test', 'salah_archive_test') == 'salah_archive_test'
    for confirmation in ('Salah_archive_test', '', 'salah_archive'):
        try:
            migration.validate_target('salah_archive_test', confirmation)
        except ValueError:
            pass
        else:
            raise AssertionError(f'confirmation was accepted: {confirmation!r}')


def test_original_and_other_databases_blocked():
    for target in ('salah_archive', 'Salah_Archive', 'production_archive', 'salah_archive2', ''):
        try:
            migration.validate_target(target, target)
        except ValueError:
            pass
        else:
            raise AssertionError(f'unsafe target accepted: {target!r}')


def test_backup_preserves_committed_rows():
    with tempfile.TemporaryDirectory() as td:
        source_path = Path(td) / 'source.db'
        backup_path = Path(td) / 'backup.db'
        src = sqlite3.connect(source_path)
        src.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)')
        src.execute('INSERT INTO sample(value) VALUES (?)', ('أرشفة-اختبار',))
        src.commit()
        migration.create_sqlite_backup(src, backup_path)
        dst = sqlite3.connect(backup_path)
        assert dst.execute('SELECT value FROM sample').fetchone()[0] == 'أرشفة-اختبار'
        dst.close(); src.close()


def test_existing_backup_not_overwritten():
    with tempfile.TemporaryDirectory() as td:
        src = sqlite3.connect(Path(td) / 'source.db')
        backup = Path(td) / 'backup.db'
        backup.write_bytes(b'preserve-existing')
        before = hashlib.sha256(backup.read_bytes()).hexdigest()
        try:
            migration.create_sqlite_backup(src, backup)
        except FileExistsError:
            pass
        else:
            raise AssertionError('existing backup was overwritten')
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == before
        src.close()


def test_migration_helper_has_no_drop_table():
    source = Path(migration.__file__).read_text(encoding='utf-8').upper()
    assert 'DROP TABLE' not in source


def test_schema_preview_on_sample_database():
    with tempfile.TemporaryDirectory() as td:
        db = sqlite3.connect(Path(td) / 'sample.db')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, title TEXT NOT NULL)')
        db.execute('INSERT INTO sample(title) VALUES (?)', ('عنوان عربي',))
        tables = migration.get_schema(db)
        assert len(tables) == 1 and tables[0][0] == 'sample'
        assert db.execute('SELECT COUNT(*) FROM sample').fetchone()[0] == 1
        db.close()


def test_preflight_detects_partial_indexes():
    with tempfile.TemporaryDirectory() as td:
        db = sqlite3.connect(Path(td) / 'sample.db')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, status VARCHAR(20))')
        db.execute("CREATE INDEX ix_sample_status ON sample(status) WHERE status='active'")
        problems = migration.schema_preflight(db)
        assert any('partial index' in p for p in problems), problems
        db.close()


def test_preflight_detects_text_indexes():
    with tempfile.TemporaryDirectory() as td:
        db = sqlite3.connect(Path(td) / 'sample.db')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, description TEXT)')
        db.execute('CREATE INDEX ix_sample_description ON sample(description)')
        problems = migration.schema_preflight(db)
        assert any('long/unbounded column' in p for p in problems), problems
        db.close()


def test_dry_run_cli_does_not_require_mysql_or_write_target():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / 'sample.db'
        db = sqlite3.connect(db_path)
        db.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, title TEXT)')
        db.execute('INSERT INTO sample(title) VALUES (?)', ('dry-run',))
        db.commit(); db.close()
        result = subprocess.run([sys.executable, str(Path(migration.__file__)), '--sqlite', str(db_path)],
                                text=True, capture_output=True, timeout=20)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert 'DRY RUN ONLY' in output, output
        assert 'Schema preflight' in output, output
        check = sqlite3.connect(db_path)
        assert check.execute('SELECT COUNT(*) FROM sample').fetchone()[0] == 1
        check.close()


if __name__ == '__main__':
    tests = [test_exact_test_database_confirmation,
             test_original_and_other_databases_blocked,
             test_backup_preserves_committed_rows,
             test_existing_backup_not_overwritten,
             test_migration_helper_has_no_drop_table,
             test_schema_preview_on_sample_database,
             test_preflight_detects_partial_indexes,
             test_preflight_detects_text_indexes,
             test_dry_run_cli_does_not_require_mysql_or_write_target]
    for test in tests:
        test(); print('PASS', test.__name__)
    print(f'{len(tests)}/{len(tests)} tests passed; no MySQL connection made.')
