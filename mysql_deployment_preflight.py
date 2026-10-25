# -*- coding: utf-8 -*-
"""One-command, read-only pre-deployment gate for Salah Archive.

This tool does not import main.py, open SQLite, contact MySQL, or execute DDL.
It runs local unit tests, compiles Python sources, regenerates static migration
reports, and exits non-zero while the SQLite runtime is still present.
"""
from __future__ import annotations
import compileall
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main() -> int:
    report = {
        "package": "Salah Archive v15.79 Warning Cleanup and Integration Preflight",
        "checks": {},
        "safety": {
            "opened_original_database": False,
            "executed_ddl": False,
            "contacted_mysql": False,
            "modified_main_py": False,
        },
    }
    test = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-v"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    (ROOT / "FINAL_GATE_UNIT_TESTS.txt").write_text(test.stdout, encoding="utf-8")
    report["checks"]["unit_tests"] = {"returncode": test.returncode, "passed": test.returncode == 0}

    compile_ok = compileall.compile_dir(str(ROOT), quiet=1, force=True)
    report["checks"]["python_compile"] = {"passed": bool(compile_ok)}
    candidate_compile = subprocess.run(
        [sys.executable, "-Werror::SyntaxWarning", "-m", "py_compile", "main_mysql_candidate_v15_79.py"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    report["checks"]["mysql_candidate_strict_compile"] = {
        "returncode": candidate_compile.returncode,
        "passed": candidate_compile.returncode == 0,
        "output": candidate_compile.stdout[-2000:],
    }

    # Generate current reports only; these scripts are static parsers.
    reports = {}
    for module in ("mysql_migration_gate.py", "mysql_pre_final_audit.py", "mysql_query_compat_audit.py", "mysql_candidate_gate.py"):
        proc = subprocess.run([sys.executable, module], cwd=ROOT, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        reports[module] = {"returncode": proc.returncode, "passed": proc.returncode == 0,
                           "output": proc.stdout[-4000:]}
    report["checks"]["static_audits"] = reports

    try:
        gate = json.loads((ROOT / "MYSQL_FINAL_MIGRATION_GATE.json").read_text(encoding="utf-8"))
    except Exception as exc:
        gate = {"status": "ERROR", "error": str(exc)}
    try:
        integration = json.loads((ROOT / "MYSQL_PRE_FINAL_INTEGRATION_AUDIT.json").read_text(encoding="utf-8"))
    except Exception as exc:
        integration = {"status": "ERROR", "error": str(exc)}
    report["migration_gate"] = gate.get("status", "UNKNOWN")
    report["integration_gate"] = integration.get("status", "UNKNOWN")
    try:
        candidate_gate = json.loads((ROOT / "MYSQL_CANDIDATE_STATIC_GATE.json").read_text(encoding="utf-8"))
    except Exception as exc:
        candidate_gate = {"status": "ERROR", "error": str(exc)}
    report["candidate_static_gate"] = candidate_gate.get("status", "UNKNOWN")
    report["checks"]["deployment_ready"] = {
        "passed": bool(test.returncode == 0 and compile_ok and gate.get("status") == "READY"
                        and integration.get("status") == "READY"),
        "reason": "The production main.py remains SQLite-based; the MySQL candidate is unsigned and live CRUD/attachment verification has not been performed.",
    }
    (ROOT / "FINAL_DEPLOYMENT_PREFLIGHT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "Salah Archive v15.79 — Final Deployment Preflight",
        "=" * 52, "",
        f"Unit tests: {'PASS' if test.returncode == 0 else 'FAIL'}",
        f"Python compile: {'PASS' if compile_ok else 'FAIL'}",
        f"Static migration gate: {report['migration_gate']}",
        f"Integration gate: {report['integration_gate']}",
        f"Candidate static gate: {report['candidate_static_gate']}",
        f"MySQL candidate strict compile: {'PASS' if candidate_compile.returncode == 0 else 'FAIL'}",
        f"Deployment ready: {'YES' if report['checks']['deployment_ready']['passed'] else 'NO'}",
        "", "Safety: no production database opened; no DDL run; no MySQL server contacted.",
        "", "Reason deployment is not declared ready:",
        report['checks']['deployment_ready']['reason'],
        "", "See FINAL_DEPLOYMENT_PREFLIGHT.json and FINAL_GATE_UNIT_TESTS.txt for details.",
    ]
    (ROOT / "FINAL_DEPLOYMENT_PREFLIGHT_AR.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if test.returncode == 0 and compile_ok and candidate_compile.returncode == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
