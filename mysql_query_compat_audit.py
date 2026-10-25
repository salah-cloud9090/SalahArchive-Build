# -*- coding: utf-8 -*-
"""Static audit of literal SQL passed to execute/executemany calls in main.py."""
from __future__ import annotations
import ast, json
from pathlib import Path
from collections import Counter
from mysql_sql_compat import translate_sql, SQLCompatibilityError

SQL_PREFIXES = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "PRAGMA", "REPLACE", "WITH", "BEGIN", "COMMIT", "ROLLBACK")

def audit_source(source: str) -> dict:
    tree = ast.parse(source)
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr.lower() not in {"execute", "executemany", "executescript"} or not node.args:
            continue
        arg = node.args[0]
        if node.func.attr.lower() == "executescript":
            script_text = ast.get_source_segment(source, arg) or ast.dump(arg, include_attributes=False)
            findings.append({"line": node.lineno, "method": "executescript", "status": "blocked", "reason": "executescript must be replaced by the reviewed MySQL schema manager", "sql": " ".join(script_text.split())[:500]})
            continue
        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
            # Dynamic SQL cannot be translated safely without evaluating runtime values.
            # Preserve it as an explicit manual-review item rather than silently omitting it.
            dynamic_text = ast.get_source_segment(source, arg) or ast.dump(arg, include_attributes=False)
            if isinstance(arg, (ast.JoinedStr, ast.Name, ast.Call, ast.BinOp)):
                findings.append({"line": node.lineno, "method": node.func.attr.lower(), "status": "dynamic_review_required", "reason": "SQL expression is not a literal constant; inspect the constructed query at runtime", "sql": " ".join(dynamic_text.split())[:500]})
            continue
        sql = arg.value.strip()
        if not sql or not sql.lstrip().upper().startswith(SQL_PREFIXES):
            continue
        item = {"line": node.lineno, "method": node.func.attr.lower(), "sql": " ".join(sql.split())[:500]}
        if node.func.attr.lower() == "executescript":
            item.update(status="blocked", reason="executescript requires reviewed schema migration")
        else:
            try:
                translated = translate_sql(sql)
                item.update(status="translated_candidate", translated=" ".join(translated.split())[:500])
            except SQLCompatibilityError as exc:
                item.update(status="blocked", reason=str(exc))
        findings.append(item)
    counts = Counter(x["status"] for x in findings)
    return {"scope": "Static literal-string audit only; dynamic SQL, runtime parameter values, and database behavior are not tested.", "statement_count": len(findings), "status_counts": dict(counts), "blocked_count": counts.get("blocked", 0), "findings": sorted(findings, key=lambda x: x["line"])}

def write_report(main_path="main.py"):
    source = Path(main_path).read_text(encoding="utf-8", errors="replace")
    report = audit_source(source)
    Path("MYSQL_QUERY_COMPAT_AUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["Salah Archive — Literal SQL Compatibility Audit", "=" * 47, "", report["scope"], f"Literal SQL statements found: {report['statement_count']}", f"Blocked by current translator: {report['blocked_count']}", "", "Status counts:"]
    lines += [f"- {key}: {value}" for key, value in sorted(report["status_counts"].items())]
    lines += ["", "Blocked statements:"]
    blocked = [x for x in report["findings"] if x["status"] == "blocked"]
    lines += [f"- L{x['line']} [{x['method']}] {x['reason']}: {x['sql']}" for x in blocked] or ["- None"]
    lines += ["", "Dynamic SQL requiring manual review:"]
    dynamic = [x for x in report["findings"] if x["status"] == "dynamic_review_required"]
    lines += [f"- L{x['line']} [{x['method']}] {x['reason']}: {x['sql']}" for x in dynamic] or ["- None"]
    lines += ["", "All findings:"]
    lines += [f"- L{x['line']} [{x['method']}] {x['status']}: {x.get('reason', '')} {x['sql']}" for x in report["findings"]]
    Path("MYSQL_QUERY_COMPAT_AUDIT_AR.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    report = write_report()
    print(json.dumps({k: report[k] for k in ("statement_count", "status_counts", "blocked_count")}, ensure_ascii=False, indent=2))
