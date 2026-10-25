# -*- coding: utf-8 -*-
"""Read-only structural gate for the SQLite-to-MySQL candidate.

This tool parses schema declarations and source markers without importing main.py,
opening SQLite, or connecting to MySQL. It is a preflight report, not a migrator.
"""
from __future__ import annotations
import ast
import json
import re
from pathlib import Path

CONSTRAINT_WORDS = {"primary", "unique", "foreign", "constraint", "check", "key", "index", "fulltext", "spatial"}


def split_top_level(text: str) -> list[str]:
    parts, current = [], []
    depth, quote, i = 0, None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            current.append(ch)
            if ch == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    current.append(text[i + 1]); i += 1
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
    if current and "".join(current).strip():
        parts.append("".join(current).strip())
    return parts


def extract_create_tables(text: str) -> dict[str, set[str]]:
    """Extract table columns from CREATE TABLE ... (...) using balanced parentheses."""
    tables: dict[str, set[str]] = {}
    pattern = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([A-Za-z_][A-Za-z0-9_]*)`?\s*\(", re.I)
    for match in pattern.finditer(text):
        name = match.group(1).lower()
        start, i, depth, quote = match.end(), match.end(), 1, None
        while i < len(text) and depth:
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
            i += 1
        if depth:
            continue
        columns = set()
        for part in split_top_level(text[start:i - 1]):
            col_match = re.match(r"\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s+(.+)", part, re.S)
            if not col_match:
                continue
            col = col_match.group(1).lower()
            if col in CONSTRAINT_WORDS:
                continue
            columns.add(col)
        # Prefer the first declaration; repeated conditional DDL should not hide a conflict.
        tables.setdefault(name, columns)
    return tables


def extract_schema_assignment(source: str, name: str = "SCHEMA") -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except Exception as exc:
                raise ValueError(f"{name} must be a literal string for safe static audit") from exc
            if not isinstance(value, str):
                raise ValueError(f"{name} is not a string")
            return value
    raise ValueError(f"Could not find literal assignment for {name}")


def build_report(main_text: str, mysql_text: str) -> dict:
    sqlite_schema = extract_schema_assignment(main_text)
    source_tables = extract_create_tables(sqlite_schema)
    # Include dynamic CREATE TABLE statements embedded in functions as well.
    dynamic_tables = extract_create_tables(main_text)
    for table, columns in dynamic_tables.items():
        source_tables.setdefault(table, columns)
    mysql_tables = extract_create_tables(mysql_text)
    missing_tables = sorted(set(source_tables) - set(mysql_tables))
    extra_tables = sorted(set(mysql_tables) - set(source_tables))
    missing_columns = {
        table: sorted(columns - mysql_tables.get(table, set()))
        for table, columns in source_tables.items()
        if table in mysql_tables and columns - mysql_tables[table]
    }
    sqlite_markers = {
        "sqlite_connect": r"sqlite3\s*\.\s*connect\s*\(",
        "pragma": r"\bPRAGMA\b",
        "executescript": r"\.\s*executescript\s*\(",
        "insert_or_ignore": r"\bINSERT\s+OR\s+IGNORE\b",
        "insert_or_replace": r"\bINSERT\s+OR\s+REPLACE\b",
        "lastrowid": r"\.\s*lastrowid\b",
        "datetime_now": r"datetime\s*\(\s*['\"]now['\"]\s*\)",
        "table_info": r"PRAGMA\s+table_info",
        "autoincrement": r"\bAUTOINCREMENT\b",
    }
    marker_lines = []
    for lineno, line in enumerate(main_text.splitlines(), 1):
        hits = [key for key, pattern in sqlite_markers.items() if re.search(pattern, line, re.I)]
        if hits:
            marker_lines.append({"line": lineno, "markers": hits, "source": line.strip()[:200]})
    return {
        "status": "BLOCKED" if missing_tables or missing_columns or any(x["markers"] for x in marker_lines) else "REVIEW_REQUIRED",
        "scope": "Static-only check; no database opened and no schema applied.",
        "sqlite_schema_tables": len(source_tables),
        "mysql_candidate_tables": len(mysql_tables),
        "missing_tables": missing_tables,
        "extra_mysql_tables": extra_tables,
        "missing_columns": missing_columns,
        "sqlite_marker_counts": {key: sum(key in item["markers"] for item in marker_lines) for key in sqlite_markers},
        "marker_line_count": len(marker_lines),
        "marker_lines": marker_lines,
        "gate_reasons": (["Missing MySQL tables"] if missing_tables else []) + (["Missing columns in candidate tables"] if missing_columns else []) + (["SQLite-only/runtime constructs remain in main.py"] if marker_lines else []),
    }


def write_report(main_path="main.py", mysql_path="MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql"):
    main_text = Path(main_path).read_text(encoding="utf-8", errors="replace")
    mysql_text = Path(mysql_path).read_text(encoding="utf-8", errors="replace")
    report = build_report(main_text, mysql_text)
    Path("MYSQL_FINAL_MIGRATION_GATE.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["Salah Archive — Final MySQL Migration Gate", "=" * 44, "", report["scope"], f"Status: {report['status']}", f"Source tables: {report['sqlite_schema_tables']}", f"Candidate tables: {report['mysql_candidate_tables']}", f"SQLite marker lines: {report['marker_line_count']}", "", "Gate reasons:"]
    lines += ["- " + reason for reason in report["gate_reasons"]] or ["- No static blockers found; runtime validation is still required."]
    lines += ["", "Missing tables:"] + ["- " + x for x in report["missing_tables"] or ["None"]]
    lines += ["", "Extra MySQL candidate tables:"] + ["- " + x for x in report["extra_mysql_tables"] or ["None"]]
    lines += ["", "Missing columns:"] + [f"- {table}: {', '.join(cols)}" for table, cols in report["missing_columns"].items()] or ["- None"]
    lines += ["", "SQLite marker counts:"] + [f"- {key}: {count}" for key, count in report["sqlite_marker_counts"].items()]
    lines += ["", "Interpretation: this gate intentionally does not claim migration readiness while SQLite runtime constructs remain."]
    Path("MYSQL_FINAL_MIGRATION_GATE_AR.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    result = write_report()
    print(json.dumps({k: result[k] for k in ("status", "sqlite_schema_tables", "mysql_candidate_tables", "missing_tables", "missing_columns", "marker_line_count")}, ensure_ascii=False, indent=2))
