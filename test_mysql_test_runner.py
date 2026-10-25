# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from mysql_test_runner_common import (
    TestLauncherError, build_child_environment, resolve_profile, run_child_script,
)

class TestLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        profiles = {
            "active_profile": "local",
            "profiles": {
                "local": {"host": "127.0.0.1", "port": 3306, "database": "salah_archive_test", "user": "archive_test_app"},
                "server": {"host": "", "port": 3306, "database": "salah_archive_test", "user": "archive_test_app"},
            },
        }
        (self.root / "mysql_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
        (self.root / "fake_target.py").write_text("pass\n", encoding="utf-8")
    def tearDown(self): self.tmp.cleanup()

    def test_resolves_only_test_database(self):
        profile, cfg = resolve_profile(self.root, "local")
        self.assertEqual(profile, "local")
        self.assertEqual(cfg["database"], "salah_archive_test")

    def test_rejects_production_database(self):
        data = json.loads((self.root / "mysql_profiles.json").read_text(encoding="utf-8"))
        data["profiles"]["local"]["database"] = "salah_archive"
        (self.root / "mysql_profiles.json").write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(TestLauncherError): resolve_profile(self.root, "local")

    def test_password_only_enters_selected_child_environment(self):
        env = build_child_environment("local", "dummy-secret", {"PATH": "x", "SALAH_MYSQL_PASSWORD": "old", "SALAH_MYSQL_PASSWORD_SERVER": "other"})
        self.assertEqual(env["SALAH_MYSQL_PASSWORD_LOCAL"], "dummy-secret")
        self.assertNotIn("SALAH_MYSQL_PASSWORD_SERVER", env)
        self.assertNotIn("SALAH_MYSQL_PASSWORD", env)

    def test_launcher_runs_python_target_with_guarded_profile(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0))
        result = run_child_script(self.root, "fake_target.py", "local", "dummy-secret", runner=runner, base_env={"PATH":"x"})
        self.assertEqual(result, 0)
        args, kwargs = runner.call_args
        self.assertEqual(Path(args[0][1]), self.root / "fake_target.py")
        self.assertEqual(kwargs["env"]["SALAH_ARCHIVE_DB_PROFILE"], "local")
        self.assertEqual(kwargs["env"]["SALAH_MYSQL_PASSWORD_LOCAL"], "dummy-secret")

    def test_rejects_missing_launch_target(self):
        with self.assertRaises(TestLauncherError): run_child_script(self.root, "missing.py", "local", "secret")

if __name__ == "__main__": unittest.main()
