# -*- coding: utf-8 -*-
"""Static, read-only map of SQLite-sensitive code paths in main.py.
Does not import or execute main.py and never opens a database.
"""
from __future__ import annotations
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

MARKERS = {
    "sqlite_connect": re.compile(r"sqlite3\s*\.\s*connect\s*\(" , re.I),
    "pragma": re.compile(r"\bPRAGMA\b", re.I),
    "executescript": re.compile(r"\.\s*executescript\s*\(", re.I),
    "insert_or_ignore": re.compile(r"\bINSERT\s+OR\s+IGNORE\b", re.I),
    "insert_or_replace": re.compile(r"\bINSERT\s+OR\s+REPLACE\b", re.I),
    "lastrowid": re.compile(r"\.\s*lastrowid\b", re.I),
    "datetime_now": re.compile(r"datetime\s*\(\s*['\"]now['\"]\s*\)", re.I),
    "table_info": re.compile(r"PRAGMA\s+table_info", re.I),
    "autoincrement": re.compile(r"\bAUTOINCREMENT\b", re.I),
}

def _function_ranges(tree):
    ranges=[]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end=max([getattr(n, "end_lineno", n.lineno) for n in ast.walk(node) if hasattr(n, "lineno")] or [node.lineno])
            ranges.append((node.lineno, end, node.name))
    return ranges

def build_map(source: str):
    tree=ast.parse(source)
    ranges=_function_ranges(tree)
    by_function=defaultdict(Counter)
    findings=[]
    for lineno,line in enumerate(source.splitlines(),1):
        hits=[name for name,pattern in MARKERS.items() if pattern.search(line)]
        if not hits: continue
        candidates=[r for r in ranges if r[0] <= lineno <= r[1]]
        fn=min(candidates, key=lambda r:r[1]-r[0])[2] if candidates else "<module-level>"
        # Broad workflow grouping is intentionally heuristic and labeled as such.
        lower=fn.lower()
        if any(x in lower for x in ("scan", "basket", "inbox", "upload")): area="scan_and_baskets"
        elif any(x in lower for x in ("case", "event", "attachment")): area="local_cases_and_attachments"
        elif any(x in lower for x in ("document", "archive", "search", "incoming", "outgoing")): area="documents_and_archive"
        elif any(x in lower for x in ("db", "init", "schema", "startup")): area="database_startup_and_schema"
        else: area="other_or_shared"
        for hit in hits: by_function[fn][hit] += 1
        findings.append({"line":lineno,"function":fn,"area_heuristic":area,"markers":hits,"source":line.strip()[:220]})
    return {
        "purpose":"Static source map only; workflow area labels are heuristic and no database was accessed.",
        "total_findings":len(findings),
        "marker_counts":dict(Counter(m for item in findings for m in item["markers"])),
        "function_counts":{fn:dict(counts) for fn,counts in sorted(by_function.items())},
        "findings":findings,
    }

def main():
    source=Path("main.py").read_text(encoding="utf-8", errors="replace")
    report=build_map(source)
    Path("MYSQL_MIGRATION_PATH_MAP_V15_70.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["Salah Archive v15.70 — SQLite Migration Path Map", "="*49, "", report["purpose"], f"Total source-line findings: {report['total_findings']}", "", "Marker counts:"]
    lines += [f"- {k}: {v}" for k,v in sorted(report["marker_counts"].items())]
    lines += ["", "Findings by function:"]
    for fn, counts in sorted(report["function_counts"].items()):
        lines.append(f"- {fn}: " + ", ".join(f"{k}={v}" for k,v in sorted(counts.items())))
    lines += ["", "Detailed line map:"]
    lines += [f"- L{x['line']} [{x['area_heuristic']}/{x['function']}] {','.join(x['markers'])}: {x['source']}" for x in report["findings"]]
    Path("MYSQL_MIGRATION_PATH_MAP_V15_70_AR.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote path map: {report['total_findings']} source-line findings")

if __name__ == "__main__": main()
