# -*- coding: utf-8 -*-
"""Launch the isolated, unsigned pre-production candidate without a PowerShell wrapper."""
from __future__ import annotations
import argparse
import getpass
from pathlib import Path
from mysql_test_runner_common import TestLauncherError, ensure_mysql_connector, resolve_profile, run_child_script

ROOT = Path(__file__).resolve().parent

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Start the pre-production MySQL test candidate.")
    parser.add_argument("--profile", choices=("local", "server"), default=None)
    parser.add_argument("--no-gui", action="store_true")
    args = parser.parse_args(argv)
    try:
        profile, cfg = resolve_profile(ROOT, args.profile)
        print(f"Salah Archive pre-production | profile={profile} | database={cfg['database']}")
        print(f"Target: {cfg['user']}@{cfg['host']}:{cfg['port']}")
        print("This candidate is restricted to salah_archive_test.")
        if not ensure_mysql_connector():
            return 2
        password = getpass.getpass("Enter the password for this TEST user (input hidden): ")
        if not password:
            print("No password entered; launch cancelled.")
            return 2
        extra = ("--network",) if profile == "server" else ()
        if args.no_gui:
            extra += ("--no-gui",)
        return run_child_script(ROOT, "main_mysql_candidate_v15_81.py", profile, password, extra_args=extra)
    except (TestLauncherError, OSError) as exc:
        print("PREFLIGHT BLOCKED:", exc)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
