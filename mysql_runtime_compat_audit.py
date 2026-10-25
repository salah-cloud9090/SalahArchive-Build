# -*- coding: utf-8 -*-
"""Static compatibility audit; never connects to a database or edits user data."""
from pathlib import Path
import re, json

ROOT=Path(__file__).resolve().parent
MAIN=ROOT/"main.py"
SCHEMA=ROOT/"MYSQL_CORE_SCHEMA_V15_62_CANDIDATE.sql"

def audit():
    source=MAIN.read_text(encoding="utf-8",errors="replace")
    schema=SCHEMA.read_text(encoding="utf-8",errors="replace")
    findings=[]
    def add(code, severity, count, detail):
        findings.append({"code":code,"severity":severity,"count":count,"detail":detail})
    add("sqlite_connect", "BLOCKER", len(re.findall(r"sqlite3\.connect\s*\(",source)),
        "db() opens SQLite connections; runtime is not switched to MySQL.")
    add("sqlite_pragma", "BLOCKER", len(re.findall(r"\bPRAGMA\b",source,re.I)),
        "PRAGMA calls require SQLite-specific branches.")
    add("sqlite_executescript", "BLOCKER", len(re.findall(r"\.executescript\s*\(",source)),
        "SCHEMA bootstrap uses executescript and needs a backend-specific initializer.")
    add("autoincrement_ddl", "BLOCKER", len(re.findall(r"\bAUTOINCREMENT\b",source,re.I)),
        "Runtime DDL uses SQLite AUTOINCREMENT.")
    add("lastrowid", "REVIEW", len(re.findall(r"\.lastrowid\b",source)),
        "Generated IDs must be verified for the selected MySQL connector and transaction.")
    add("insert_or_replace", "BLOCKER", len(re.findall(r"INSERT\s+OR\s+REPLACE",source,re.I)),
        "SQLite replacement semantics differ from MySQL upsert semantics; requires explicit rewrite.")
    add("dynamic_schema_ddl", "BLOCKER", len(re.findall(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS",source,re.I))-12,
        "Additional runtime-created scan grouping tables must be routed through the backend schema manager.")
    table_names=set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]\w*)",schema,re.I))
    expected={"local_cabinets","local_documents","local_document_fields","local_users","local_audit",
              "local_cases","local_case_events","local_case_inbox_links","local_case_documents",
              "local_case_attachments","scan_baskets","scan_inbox","scan_inbox_groups",
              "scan_inbox_group_items","archive_index","archive_index_fields"}
    add("candidate_schema_coverage", "INFO", len(table_names),
        "Candidate schema covers "+str(len(table_names))+" named tables; missing="+", ".join(sorted(expected-table_names))+"; unexpected="+", ".join(sorted(table_names-expected)))
    return findings

if __name__=="__main__":
    results=audit()
    print(json.dumps(results,ensure_ascii=False,indent=2))
