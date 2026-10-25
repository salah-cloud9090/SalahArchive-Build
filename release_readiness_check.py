# -*- coding: utf-8 -*-
"""Local pre-release checks. This script never connects to or modifies any database."""
from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(label, command):
    p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    ok = p.returncode == 0
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    out = (p.stdout + '\n' + p.stderr).strip()
    if out:
        print(out[-3000:])
    return ok

def main():
    results = []
    py_files = [ROOT/'main.py', ROOT/'mysql_safety.py', ROOT/'migrate_sqlite_to_mysql.py', ROOT/'safe_migrate_sqlite_to_mysql.py', ROOT/'test_mysql_safety.py', ROOT/'test_migration_safety.py']
    results.append(run('Python syntax compilation', [sys.executable, '-m', 'py_compile', *map(str, py_files)]))
    results.append(run('Isolated MySQL guard helper tests (not integrated into main.py)', [sys.executable, 'test_mysql_safety.py']))
    results.append(run('Guarded migration helper unit tests (no MySQL connection)', [sys.executable, 'test_migration_safety.py']))
    spec = importlib.util.spec_from_file_location('integrity_guard', ROOT/'integrity_guard.py')
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    ok, detail = mod.verify_integrity(ROOT)
    results.append(ok)
    print(('PASS' if ok else 'FAIL') + ': signed package integrity: ' + detail)
    print('\nSUMMARY: %d/%d checks passed' % (sum(results), len(results)))
    print('No MySQL connection was attempted. No database was created, migrated, or modified.')
    return 0 if all(results) else 2

if __name__ == '__main__':
    raise SystemExit(main())
