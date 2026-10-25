# -*- coding: utf-8 -*-
"""Read-only pre-final integration audit for the SQLite -> MySQL candidate.

No application import, database opening, network access, or schema changes occur.
"""
from __future__ import annotations
import ast
import json
import re
from pathlib import Path


def audit(main_text: str, repository_text: str) -> dict:
    tree = ast.parse(main_text)
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    db_node = functions.get("db")
    db_source = ast.get_source_segment(main_text, db_node) if db_node else ""
    markers = {
        "runtime_sqlite_connect": bool(re.search(r"sqlite3\s*\.\s*connect\s*\(", db_source)),
        "runtime_executescript": bool(re.search(r"\.\s*executescript\s*\(", main_text)),
        "runtime_pragma": bool(re.search(r"\bPRAGMA\b", main_text, re.I)),
        "runtime_sqlite_datetime": bool(re.search(r"datetime\s*\(\s*['\"]now['\"]\s*\)", main_text, re.I)),
        "dynamic_table_ddl": bool(re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS", main_text, re.I)),
        "direct_connection_contexts": bool(re.search(r"with\s+db\s*\(\)\s+as\s+\w+", main_text)),
    }
    api = {
        "context_manager": "def __enter__(" in repository_text and "def __exit__(" in repository_text,
        "commit": bool(re.search(r"def\s+commit\s*\(", repository_text)),
        "rollback": bool(re.search(r"def\s+rollback\s*\(", repository_text)),
        "executescript_fails_closed": "def executescript(" in repository_text and "SQLCompatibilityError" in repository_text,
    }
    blockers = [name for name, active in markers.items() if active]
    blockers += ["main.py is not wired to MySQLRepository"] if "MySQLRepository" not in db_source else []
    return {
        "status": "BLOCKED" if blockers else "REVIEW_REQUIRED",
        "scope": "Static-only pre-final integration audit; no database opened and no network connection attempted.",
        "main_db_function_found": bool(db_node),
        "runtime_markers": markers,
        "adapter_api_coverage": api,
        "blockers": blockers,
        "safe_next_step": "Refactor database initialization and all SQLite-only setup behind a separately tested MySQL bootstrap; then run CRUD and attachment integration tests against salah_archive_test only.",
        "safety": {"original_database_opened": False, "ddl_executed": False, "mysql_contacted": False},
    }


def write_report(main_path="main.py", repository_path="mysql_repository.py"):
    main_text = Path(main_path).read_text(encoding="utf-8", errors="replace")
    repo_text = Path(repository_path).read_text(encoding="utf-8", errors="replace")
    result = audit(main_text, repo_text)
    Path("MYSQL_PRE_FINAL_INTEGRATION_AUDIT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["Salah Archive — Pre-final MySQL Integration Audit", "=" * 49, "", result["scope"], f"Status: {result['status']}", "", "Runtime SQLite markers:"]
    lines += [f"- {key}: {'PRESENT' if value else 'not detected'}" for key, value in result["runtime_markers"].items()]
    lines += ["", "Repository API coverage:"]
    lines += [f"- {key}: {'present' if value else 'missing'}" for key, value in result["adapter_api_coverage"].items()]
    lines += ["", "Blockers:"] + [f"- {item}" for item in result["blockers"]]
    lines += ["", "Safety confirmation:", "- Original database opened: No", "- DDL executed: No", "- MySQL contacted: No", "", "Next safe step:", result["safe_next_step"]]
    Path("MYSQL_PRE_FINAL_INTEGRATION_AUDIT_AR.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result

if __name__ == "__main__":
    r = write_report()
    print(json.dumps({"status": r["status"], "blockers": r["blockers"], "adapter_api_coverage": r["adapter_api_coverage"]}, ensure_ascii=False, indent=2))
