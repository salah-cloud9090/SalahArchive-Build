# -*- coding: utf-8 -*-
"""Static audit of main.py for SQLite-to-MySQL migration blockers."""
import argparse, json, re
from pathlib import Path

PATTERNS = {
    "db_call": r"\bdb\s*\(", "execute": r"\.execute\s*\(",
    "executemany": r"\.executemany\s*\(", "executescript": r"\.executescript\s*\(",
    "fetchone": r"\.fetchone\s*\(", "fetchall": r"\.fetchall\s*\(",
    "lastrowid": r"\.lastrowid\b", "sqlite_pragma": r"\bPRAGMA\b",
    "insert_or_replace": r"\bINSERT\s+OR\s+REPLACE\b",
    "insert_or_ignore": r"\bINSERT\s+OR\s+IGNORE\b",
    "autoincrement": r"\bAUTOINCREMENT\b", "sqlite_connect": r"sqlite3\.connect",
    "row_factory": r"\.row_factory\b",
}
def audit_text(source):
    counts = {k: len(re.findall(v, source, re.I)) for k,v in PATTERNS.items()}
    hotkeys = ("executescript","sqlite_pragma","insert_or_replace","insert_or_ignore","autoincrement","lastrowid","sqlite_connect","row_factory")
    hotspots = []
    for n,line in enumerate(source.splitlines(),1):
        if any(re.search(PATTERNS[k],line,re.I) for k in hotkeys):
            hotspots.append({"line":n,"text":line.strip()[:240]})
    blockers=[]
    if counts["sqlite_connect"] or counts["row_factory"]: blockers.append("Connection creation and row mapping are SQLite-specific.")
    if counts["executescript"]: blockers.append("executescript needs statement splitting and transaction review.")
    if counts["sqlite_pragma"]: blockers.append("PRAGMA statements need backend-specific initialization.")
    if counts["insert_or_replace"]: blockers.append("INSERT OR REPLACE semantics require explicit review.")
    if counts["insert_or_ignore"]: blockers.append("INSERT OR IGNORE semantics and constraints require review.")
    if counts["lastrowid"]: blockers.append("Generated-ID behavior needs validation for insert paths.")
    return {"counts":counts,"hotspots":hotspots,"blockers":blockers}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",nargs="?",default="main.py")
    ap.add_argument("--json",dest="json_path")
    a=ap.parse_args()
    report=audit_text(Path(a.source).read_text(encoding="utf-8",errors="replace"))
    rendered=json.dumps(report,ensure_ascii=False,indent=2)
    print(rendered)
    if a.json_path: Path(a.json_path).write_text(rendered+"\n",encoding="utf-8")
if __name__=="__main__": main()


def migration_readiness(source):
    """Return conservative readiness classification based on source markers."""
    report = audit_text(source)
    counts = report["counts"]
    checks = {
        "connection_factory": {
            "status": "BLOCKED" if counts["sqlite_connect"] or counts["row_factory"] else "REVIEW",
            "reason": "SQLite connection creation/row_factory found in source."
        },
        "schema_creation": {
            "status": "BLOCKED" if counts["executescript"] or counts["autoincrement"] else "REVIEW",
            "reason": "SQLite schema initialization patterns require backend-specific handling."
        },
        "duplicate_handling": {
            "status": "BLOCKED" if counts["insert_or_replace"] or counts["insert_or_ignore"] else "REVIEW",
            "reason": "Duplicate handling semantics need explicit review."
        },
        "generated_ids": {
            "status": "REVIEW" if counts["lastrowid"] else "UNKNOWN",
            "reason": "Generated identifiers need insert-path tests."
        },
        "runtime_integration": {
            "status": "NOT_STARTED",
            "reason": "This static audit never modifies main.py."
        },
        "real_mysql_integration": {
            "status": "NOT_TESTED",
            "reason": "No MySQL server is contacted by this tool."
        }
    }
    return {"counts": counts, "checks": checks, "blockers": report["blockers"]}
