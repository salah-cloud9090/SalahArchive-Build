# -*- coding: utf-8 -*-
"""Windows-friendly, password-safe launcher helpers for the isolated MySQL test DB."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping

ALLOWED_DATABASE = "salah_archive_test"
VALID_PROFILES = {"local", "server"}

class TestLauncherError(RuntimeError):
    pass


def resolve_profile(app_dir: Path, profile: str | None = None) -> tuple[str, dict]:
    """Load a deployment profile and refuse every database except the isolated test DB."""
    app_dir = Path(app_dir).resolve()
    path = app_dir / "mysql_profiles.json"
    if not path.is_file():
        raise TestLauncherError(
            "Missing mysql_profiles.json. This repair package includes a default local TEST profile; "
            "if this file was removed, run CONFIGURE_MYSQL_PROFILES.bat."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TestLauncherError("mysql_profiles.json is unreadable or invalid JSON.") from exc
    selected = (profile or raw.get("active_profile") or "local").strip().lower()
    if selected not in VALID_PROFILES:
        raise TestLauncherError("Profile must be local or server.")
    try:
        from mysql_deployment_profiles import load_profile
        actual_profile, cfg = load_profile(app_dir, profile=selected, respect_environment=False)
    except Exception as exc:
        raise TestLauncherError(str(exc)) from exc
    if actual_profile != selected:
        raise TestLauncherError("Selected MySQL profile did not match requested profile.")
    if cfg.get("database") != ALLOWED_DATABASE:
        raise TestLauncherError("Launcher refuses any database except salah_archive_test.")
    return actual_profile, cfg


def build_child_environment(profile: str, password: str, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Put the secret only in the child process environment, never in a file or CLI argument."""
    if profile not in VALID_PROFILES:
        raise TestLauncherError("Profile must be local or server.")
    if not password:
        raise TestLauncherError("A non-empty MySQL password is required.")
    env = dict(os.environ if base_env is None else base_env)
    env["SALAH_ARCHIVE_DB_BACKEND"] = "mysql"
    env["SALAH_ARCHIVE_DB_PROFILE"] = profile
    env.pop("SALAH_MYSQL_PASSWORD", None)
    for name in VALID_PROFILES:
        env.pop("SALAH_MYSQL_PASSWORD_" + name.upper(), None)
    env["SALAH_MYSQL_PASSWORD_" + profile.upper()] = password
    return env


def run_child_script(
    app_dir: Path,
    script_name: str,
    profile: str,
    password: str,
    extra_args: tuple[str, ...] = (),
    runner: Callable = subprocess.run,
    base_env: Mapping[str, str] | None = None,
) -> int:
    """Launch only a known package script after strict test-profile validation."""
    root = Path(app_dir).resolve()
    profile, cfg = resolve_profile(root, profile)
    if cfg.get("database") != ALLOWED_DATABASE:
        raise TestLauncherError("Refusing to run against a non-test database.")
    script = root / script_name
    if not script.is_file() or script.parent != root:
        raise TestLauncherError("Required launcher target is missing: " + script_name)
    env = build_child_environment(profile, password, base_env)
    proc = runner([sys.executable, str(script), *extra_args], cwd=str(root), env=env)
    return int(proc.returncode)


def ensure_mysql_connector(prompt: Callable[[str], str] = input, runner: Callable = subprocess.run) -> bool:
    """Check connector dependency; offer a single explicit, scoped pip installation."""
    try:
        import mysql.connector  # noqa: F401
        return True
    except Exception:
        print("MySQL Connector/Python is not installed in this Python environment.")
        answer = prompt('Install the required mysql-connector-python package now? [Y/n]: ').strip().lower()
        if answer not in {"", "y", "yes"}:
            print('Install it later with: py -m pip install "mysql-connector-python>=8.3.0"')
            return False
        proc = runner(
            [sys.executable, "-m", "pip", "install", "mysql-connector-python>=8.3.0"],
            cwd=str(Path(__file__).resolve().parent),
        )
        if proc.returncode != 0:
            print('Dependency installation failed. Check internet access and Python/pip, then retry.')
            return False
        try:
            import mysql.connector  # noqa: F401
            return True
        except Exception:
            print('The connector still cannot be imported after installation. Check which Python was updated.')
            return False
