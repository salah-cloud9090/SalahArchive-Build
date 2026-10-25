# -*- coding: utf-8 -*-
"""Reliable local/server live-integration test launcher; no PowerShell parsing required."""
from __future__ import annotations
import argparse
import getpass
from pathlib import Path
from mysql_test_runner_common import TestLauncherError, ensure_mysql_connector, resolve_profile, run_child_script

ROOT = Path(__file__).resolve().parent

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the guarded Salah Archive MySQL TEST database integration test.")
    parser.add_argument("--profile", choices=("local", "server"), default=None)
    args = parser.parse_args(argv)
    try:
        profile, cfg = resolve_profile(ROOT, args.profile)
        print(f"Salah Archive v15.81 test integration | profile={profile} | database={cfg['database']}")
        print(f"Target: {cfg['user']}@{cfg['host']}:{cfg['port']}")
        if not ensure_mysql_connector():
            return 2
        password = getpass.getpass("Enter the password for this TEST user (input hidden): ")
        if not password:
            print("No password entered; test cancelled.")
            return 2
        return run_child_script(ROOT, "mysql_live_integration_test.py", profile, password)
    except (TestLauncherError, OSError) as exc:
        print("PREFLIGHT BLOCKED:", exc)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
