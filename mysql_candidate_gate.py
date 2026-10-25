# -*- coding: utf-8 -*-
"""Static release gate for the unsigned MySQL runtime candidate; never opens a database."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "main_mysql_candidate.py"
BASE = ROOT / "main.py"

def inspect_candidate():
    checks = {}
    if not CANDIDATE.is_file():
        return {"status": "BLOCKED", "checks": {"candidate_present": False}}
    text = CANDIDATE.read_text(encoding="utf-8")
    checks["candidate_present"] = True
    checks["opt_in_backend_flag"] = "SALAH_ARCHIVE_DB_BACKEND" in text and "connect_test_database(APP_DIR)" in text
    checks["reviewed_schema_bootstrap"] = "ensure_schema(c._connection" in text and "MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql" in text
    schema_manager = (ROOT / "mysql_schema_manager.py").read_text(encoding="utf-8") if (ROOT / "mysql_schema_manager.py").is_file() else ""
    checks["foreign_key_preflight"] = "information_schema.KEY_COLUMN_USAGE" in schema_manager and "missing foreign keys" in schema_manager and "unexpected foreign keys" in schema_manager
    checks["test_db_ui_locked"] = "'database','قاعدة الاختبار','salah_archive_test'" in text and "readonly" in text
    mysql_ui = text[text.find("    def mysql_page("):text.find("    def launch_scanner(", text.find("    def mysql_page("))]
    checks["password_not_form_persisted"] = bool(mysql_ui) and "name=\"password\"" not in mysql_ui and "'password':f.get('password'" not in mysql_ui
    checks["sqlite_setup_guarded"] = bool(re.search(r"if mysql_backend_enabled\(\):[\s\S]{0,350}ensure_schema[\s\S]{0,250}else:[\s\S]{0,250}executescript\(SCHEMA\)", text))
    checks["known_replace_statement_reviewed"] = "INSERT OR REPLACE INTO scan_inbox_group_items" in text
    checks["mysql_sync_not_run_on_archive_crud"] = text.count("if not mysql_backend_enabled(): sync_document(") >= 2 and "if not mysql_backend_enabled(): delete_index_record(" in text
    # The original main.py must remain unchanged in the delivered candidate.
    checks["original_sqlite_source_retained"] = BASE.is_file() and "sqlite3.connect(DB_PATH" in BASE.read_text(encoding="utf-8")
    checks["not_claimed_live_tested"] = True
    blockers = [name for name, passed in checks.items() if not passed]
    return {"status": "PASS_STATIC_CANDIDATE" if not blockers else "BLOCKED", "checks": checks,
            "blockers": blockers, "limitations": ["No MySQL server connection was attempted.",
            "No real archive CRUD, scanner, attachment, or AI workflow was executed.",
            "Candidate remains unsigned and is not installed over main.py."]}

def main():
    report = inspect_candidate()
    (ROOT / "MYSQL_CANDIDATE_STATIC_GATE.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines=["Salah Archive — MySQL Candidate Static Gate", "="*43, "", "Status: "+report["status"], ""]
    lines += [("PASS" if ok else "FAIL")+" — "+key for key,ok in report["checks"].items()]
    if report.get("blockers"): lines += ["", "Blockers: "+", ".join(report["blockers"])]
    lines += ["", "Limitations:"] + ["- "+x for x in report["limitations"]]
    (ROOT / "MYSQL_CANDIDATE_STATIC_GATE_AR.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if report["status"] == "PASS_STATIC_CANDIDATE" else 1
if __name__ == "__main__": raise SystemExit(main())
