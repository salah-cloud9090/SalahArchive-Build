# -*- coding: utf-8 -*-
"""Conservative MySQL schema installer for the isolated Salah Archive test DB."""
from pathlib import Path
import re

class SchemaPreflightError(RuntimeError):
    pass

_FORBIDDEN = re.compile(r"(?im)^\s*(DROP|TRUNCATE|DELETE|ALTER)\b")

def split_sql_statements(sql_text):
    """Split this project's DDL on semicolons; schema deliberately has no procedural SQL."""
    if _FORBIDDEN.search(sql_text):
        raise SchemaPreflightError("Schema file contains a destructive/altering statement; refusing to run.")
    cleaned = re.sub(r"(?m)^\s*--.*$", "", sql_text)
    return [part.strip() for part in cleaned.split(";") if part.strip() and part.strip().upper() != "SET NAMES UTF8MB4"]

def _split_top_level(body):
    parts, current = [], []
    depth, quote, i = 0, None, 0
    while i < len(body):
        ch = body[i]
        if quote:
            current.append(ch)
            if ch == quote:
                if i + 1 < len(body) and body[i + 1] == quote:
                    current.append(body[i + 1]); i += 1
                else:
                    quote = None
        elif ch in "'\"`":
            quote = ch; current.append(ch)
        elif ch == "(":
            depth += 1; current.append(ch)
        elif ch == ")":
            depth -= 1; current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip()); current = []
        else:
            current.append(ch)
        i += 1
    if "".join(current).strip(): parts.append("".join(current).strip())
    return parts

def expected_column_types(statement):
    match = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_]+)\s*\((.*)\)\s*ENGINE\s*=", statement, re.I | re.S)
    if not match:
        return None, {}
    table, body = match.group(1), match.group(2)
    columns = {}
    for part in _split_top_level(body):
        m = re.match(r"\s*`?([a-zA-Z][a-zA-Z0-9_]*)`?\s+([a-zA-Z]+(?:\s*\([^)]*\))?)", part, re.I)
        if not m or m.group(1).lower() in {"primary", "unique", "foreign", "constraint", "check", "key", "index", "fulltext", "spatial"}:
            continue
        columns[m.group(1).lower()] = re.sub(r"\s+", "", m.group(2)).lower()
    return table.lower(), columns


def _balanced_parenthesized(text, open_pos):
    """Return content inside balanced parentheses, handling index prefixes like subject(191)."""
    if open_pos >= len(text) or text[open_pos] != "(":
        return None, open_pos
    depth, quote, i = 0, None, open_pos
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_pos + 1:i], i + 1
        i += 1
    return None, open_pos


def _index_definition(text, pattern):
    """Parse an index declaration while respecting nested prefix-length parentheses."""
    m = re.match(pattern, text, re.I)
    if not m:
        return None
    name = (m.group(1) or "") if m.lastindex else ""
    pos = m.end()
    while pos < len(text) and text[pos].isspace():
        pos += 1
    raw, end = _balanced_parenthesized(text, pos)
    if raw is None:
        return None
    return name, raw


def expected_indexes(statement):
    """Return explicit index definitions: name -> (is_unique, ordered columns)."""
    match = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_]+)\s*\((.*)\)\s*ENGINE\s*=", statement, re.I | re.S)
    if not match:
        return None, {}
    table, body = match.group(1).lower(), match.group(2)
    indexes = {}
    for part in _split_top_level(body):
        text = part.strip()
        if re.match(r"PRIMARY\s+KEY\s*\(", text, re.I):
            parsed = _index_definition(text, r"PRIMARY\s+KEY\s*")
            if parsed:
                indexes["PRIMARY"] = (True, _index_columns(parsed[1]))
            continue
        if re.match(r"(?:UNIQUE\s+(?:KEY|INDEX)|UNIQUE)\b", text, re.I):
            parsed = _index_definition(text, r"(?:UNIQUE\s+(?:KEY|INDEX)|UNIQUE)\s*`?([a-zA-Z0-9_]*)`?\s*")
            if parsed:
                cols = _index_columns(parsed[1])
                name = parsed[0] or "UNIQUE_" + "_".join(c[0] for c in cols)
                indexes[name] = (True, cols)
            continue
        if re.match(r"(?:KEY|INDEX)\b", text, re.I):
            parsed = _index_definition(text, r"(?:KEY|INDEX)\s+`?([a-zA-Z0-9_]+)`?\s*")
            if parsed:
                indexes[parsed[0]] = (False, _index_columns(parsed[1]))
            continue
        # Column-level PRIMARY KEY / UNIQUE declarations.
        m = re.match(r"`?([a-zA-Z][a-zA-Z0-9_]*)`?\s+.+", text, re.I | re.S)
        if m:
            column = m.group(1)
            if re.search(r"\bPRIMARY\s+KEY\b", text, re.I):
                indexes["PRIMARY"] = (True, ((column, None),))
            elif re.search(r"\bUNIQUE\b", text, re.I):
                indexes[column] = (True, ((column, None),))
    return table, indexes


def _index_columns(raw):
    columns = []
    for item in _split_top_level(raw):
        m = re.match(r"\s*`?([a-zA-Z0-9_]+)`?(?:\s*\(\s*(\d+)\s*\))?", item)
        if m:
            columns.append((m.group(1).lower(), int(m.group(2)) if m.group(2) else None))
    return tuple(columns)

def expected_foreign_keys(statement):
    """Return semantic FK signatures: (local columns, referenced table, referenced columns)."""
    match = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_]+)\s*\((.*)\)\s*ENGINE\s*=", statement, re.I | re.S)
    if not match:
        return None, set()
    table, body = match.group(1).lower(), match.group(2)
    found = set()
    for part in _split_top_level(body):
        text = part.strip()
        fk = re.search(
            r"(?:CONSTRAINT\s+`?[a-zA-Z0-9_]+`?\s+)?FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\s+`?([a-zA-Z0-9_]+)`?\s*\(([^)]*)\)",
            text, re.I | re.S,
        )
        if not fk:
            continue
        local = tuple(col for col, _ in _index_columns(fk.group(1)))
        remote = tuple(col for col, _ in _index_columns(fk.group(3)))
        if not local or not remote or len(local) != len(remote):
            raise SchemaPreflightError(f"Cannot safely parse foreign key in table {table}: {text}")
        found.add((local, fk.group(2).lower(), remote))
    return table, found


def expected_columns(statement):
    table, typed = expected_column_types(statement)
    return table, set(typed)

def _base_type(value):
    if not value: return None
    value = str(value).strip().lower().split()[0]
    return value.split("(", 1)[0]

def _type_signature(value):
    """Normalize MySQL type names while preserving width/precision where data can truncate."""
    if not value:
        return None, None
    normalized = re.sub(r"\s+", "", str(value).strip().lower())
    match = re.fullmatch(r"([a-z]+)(?:\(([^)]*)\))?", normalized)
    if not match:
        return normalized, None
    base, args = match.group(1), match.group(2)
    # Display widths for integer types are not storage capacity and differ by server version.
    if base in {"tinyint", "smallint", "mediumint", "int", "integer", "bigint"}:
        args = None
    return base, args

def _types_compatible(expected, actual):
    expected_base, expected_args = _type_signature(expected)
    actual_base, actual_args = _type_signature(actual)
    if expected_base != actual_base:
        return False
    # Width/precision must match for string and decimal types to prevent silent truncation.
    if expected_base in {"char", "varchar", "binary", "varbinary", "decimal", "numeric"}:
        return expected_args == actual_args
    return True

def ensure_schema(connection, schema_path):
    """Preflight existing table columns before applying any CREATE TABLE statements."""
    path = Path(schema_path)
    if not path.is_file():
        raise SchemaPreflightError("Missing schema file: " + str(path))
    sql_text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    expected = {}
    expected_index_map = {}
    expected_fk_map = {}
    for stmt in statements:
        table, typed_columns = expected_column_types(stmt)
        if table:
            expected[table] = typed_columns
            _, indexes = expected_indexes(stmt)
            expected_index_map[table] = indexes
            _, foreign_keys = expected_foreign_keys(stmt)
            expected_fk_map[table] = foreign_keys
    if not expected:
        raise SchemaPreflightError("No recognized CREATE TABLE statements found in schema file.")

    cur = connection.cursor()
    try:
        cur.execute("SELECT DATABASE()")
        row = cur.fetchone()
        database_name = row[0] if row else None
        if database_name != "salah_archive_test":
            raise SchemaPreflightError("Refusing schema setup: connected database must be exactly salah_archive_test.")
        # First pass: inspect all pre-existing tables. No DDL has run yet.
        conflicts = []
        for table, wanted_types in expected.items():
            cur.execute("SELECT TABLE_NAME FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (table,))
            exists = cur.fetchone()
            if not exists:
                continue
            cur.execute("SHOW COLUMNS FROM `" + table + "`")
            actual_rows = cur.fetchall()
            actual_types = {str(r[0]).lower(): (str(r[1]) if len(r) > 1 and r[1] is not None else None) for r in actual_rows}
            missing = sorted(set(wanted_types) - set(actual_types))
            unexpected = sorted(set(actual_types) - set(wanted_types))
            mismatched = []
            for column, expected_type in wanted_types.items():
                actual_type = actual_types.get(column)
                if actual_type and not _types_compatible(expected_type, actual_type):
                    mismatched.append(f"{column} expected {expected_type}, found {actual_type}")
            if missing:
                conflicts.append(table + " missing columns: " + ", ".join(missing))
            if unexpected:
                conflicts.append(table + " unexpected columns: " + ", ".join(unexpected))
            if mismatched:
                conflicts.append(table + " incompatible column types: " + "; ".join(mismatched))
            # CREATE TABLE IF NOT EXISTS does not repair indexes on an existing table.
            # Validate required indexes before allowing the schema setup to continue.
            cur.execute("SHOW INDEX FROM `" + table + "`")
            index_rows = cur.fetchall()
            actual_indexes = {}
            for index_row in index_rows:
                if len(index_row) < 5:
                    continue
                key_name = str(index_row[2])
                non_unique = int(index_row[1])
                seq = int(index_row[3])
                col_name = str(index_row[4]).lower()
                sub_part = index_row[7] if len(index_row) > 7 else None
                actual_indexes.setdefault(key_name, {"unique": non_unique == 0, "columns": []})["columns"].append((seq, col_name, int(sub_part) if sub_part is not None else None))
            normalized_actual = {name: (value["unique"], tuple((col, prefix) for _, col, prefix in sorted(value["columns"]))) for name, value in actual_indexes.items()}
            wanted_indexes = expected_index_map.get(table, {})
            missing_indexes = []
            wrong_indexes = []
            for index_name, wanted_signature in wanted_indexes.items():
                actual_signature = normalized_actual.get(index_name)
                if actual_signature is None:
                    missing_indexes.append(index_name)
                elif actual_signature != wanted_signature:
                    wrong_indexes.append(f"{index_name} expected {wanted_signature}, found {actual_signature}")
            # Unexpected UNIQUE indexes can reject valid archive rows, so they are unsafe.
            expected_names = set(wanted_indexes)
            unexpected_unique = sorted(name for name, signature in normalized_actual.items() if signature[0] and name not in expected_names)
            if missing_indexes:
                conflicts.append(table + " missing indexes: " + ", ".join(missing_indexes))
            if wrong_indexes:
                conflicts.append(table + " incompatible indexes: " + "; ".join(wrong_indexes))
            if unexpected_unique:
                conflicts.append(table + " unexpected unique indexes: " + ", ".join(unexpected_unique))
            # CREATE TABLE IF NOT EXISTS never repairs missing or incorrect foreign keys.
            cur.execute(
                "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME, ORDINAL_POSITION "
                "FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL "
                "ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION", (table,)
            )
            fk_rows = cur.fetchall()
            actual_fk_parts = {}
            for fk_row in fk_rows:
                if len(fk_row) < 5:
                    continue
                name, local_col, ref_table, ref_col, ordinal = fk_row[:5]
                bucket = actual_fk_parts.setdefault(str(name), [])
                bucket.append((int(ordinal), str(local_col).lower(), str(ref_table).lower(), str(ref_col).lower()))
            actual_fks = set()
            for parts in actual_fk_parts.values():
                parts.sort()
                local_cols = tuple(item[1] for item in parts)
                ref_tables = {item[2] for item in parts}
                ref_cols = tuple(item[3] for item in parts)
                if len(ref_tables) == 1:
                    actual_fks.add((local_cols, next(iter(ref_tables)), ref_cols))
            wanted_fks = expected_fk_map.get(table, set())
            missing_fks = sorted(wanted_fks - actual_fks)
            unexpected_fks = sorted(actual_fks - wanted_fks)
            if missing_fks:
                conflicts.append(table + " missing foreign keys: " + repr(missing_fks))
            if unexpected_fks:
                conflicts.append(table + " unexpected foreign keys: " + repr(unexpected_fks))
        if conflicts:
            raise SchemaPreflightError(
                "Existing test-database tables do not match the candidate schema. No schema statements were run. "
                + " | ".join(conflicts)
                + ". Back up and recreate/repair the TEST database manually before retrying; production is never targeted."
            )
        for stmt in statements:
            cur.execute(stmt)
        connection.commit()
        return sorted(expected)
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        cur.close()
