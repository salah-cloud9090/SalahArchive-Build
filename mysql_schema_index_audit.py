# -*- coding: utf-8 -*-
"""Static index-coverage audit for the isolated MySQL candidate schema."""
from __future__ import annotations
import json
from pathlib import Path
from mysql_schema_manager import split_sql_statements, expected_column_types, expected_indexes, expected_foreign_keys

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / 'MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql'
REPORT = ROOT / 'MYSQL_INDEX_PREFLIGHT_V15_78.json'

def build_report():
    statements = split_sql_statements(SCHEMA.read_text(encoding='utf-8'))
    tables = []
    errors = []
    seen_tables = set()
    foreign_key_count = 0
    foreign_keys_report = []
    for statement in statements:
        table, columns = expected_column_types(statement)
        if not table:
            continue
        _, indexes = expected_indexes(statement)
        _, foreign_keys = expected_foreign_keys(statement)
        foreign_key_count += len(foreign_keys)
        for local_cols, ref_table, ref_cols in sorted(foreign_keys):
            foreign_keys_report.append({'table': table, 'columns': list(local_cols), 'references_table': ref_table, 'references_columns': list(ref_cols)})
        if table in seen_tables:
            errors.append(f'duplicate CREATE TABLE definition: {table}')
        seen_tables.add(table)
        if 'PRIMARY' not in indexes:
            errors.append(f'{table}: no primary key parsed')
        for name, (unique, cols) in indexes.items():
            if not cols:
                errors.append(f'{table}.{name}: empty index definition')
            for col, _prefix in cols:
                if col not in columns:
                    errors.append(f'{table}.{name}: index column {col} is not declared')
        tables.append({
            'table': table,
            'column_count': len(columns),
            'index_count': len(indexes),
            'indexes': [
                {'name': name, 'unique': unique,
                 'columns': [{'name': col, 'prefix_length': prefix} for col, prefix in cols]}
                for name, (unique, cols) in sorted(indexes.items())
            ],
        })
    known_tables = {item['table'] for item in tables}
    for fk in foreign_keys_report:
        if fk['references_table'] not in known_tables:
            errors.append(f"{fk['table']}: foreign key target table {fk['references_table']} is not declared")
        declared_cols = next((item for item in tables if item['table'] == fk['references_table']), None)
        if declared_cols is None:
            continue
        # Column-level FK target coverage is verified by parsing each table's declared columns.
        target_statement = next((st for st in statements if expected_column_types(st)[0] == fk['references_table']), None)
        _, target_columns = expected_column_types(target_statement) if target_statement else (None, {})
        for col in fk['references_columns']:
            if col not in target_columns:
                errors.append(f"{fk['table']}: foreign key target column {fk['references_table']}.{col} is not declared")
    return {
        'version': '15.78',
        'status': 'PASS_STATIC' if tables and not errors else 'BLOCKED',
        'target_database': 'salah_archive_test',
        'tables_checked': len(tables),
        'indexes_checked': sum(t['index_count'] for t in tables),
        'foreign_keys_checked': foreign_key_count,
        'foreign_keys': foreign_keys_report,
        'errors': errors,
        'limitations': [
            'Static parsing only; no MySQL server connection was made.',
            'Existing database columns, indexes, and foreign keys are checked at runtime by ensure_schema before CREATE TABLE statements.',
            'Foreign-key definitions are parsed statically and checked against existing test tables before DDL; server collation/version still require live validation.',
            'The production database salah_archive was not accessed or modified.'
        ],
        'tables': tables,
    }

if __name__ == '__main__':
    report = build_report()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('version','status','tables_checked','indexes_checked','errors','limitations')}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['status'] == 'PASS_STATIC' else 2)
