# -*- coding: utf-8 -*-
"""Centralized MySQL configuration for Salah Archive.

Security policy for this candidate:
- database writes are allowed only to the isolated salah_archive_test database.
- passwords are read only from SALAH_MYSQL_PASSWORD; never from JSON.
- mysql_config.json stores non-secret connection metadata only.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

CONFIG_NAME = "mysql_config.json"
PASSWORD_ENV = "SALAH_MYSQL_PASSWORD"
ALLOWED_TEST_DATABASE = "salah_archive_test"

class MySQLConfigError(ValueError):
    pass

def load_config(app_dir, *, require_password=False, enforce_test_db=True, profile=None):
    app_dir = Path(app_dir)
    profiles_path = app_dir / "mysql_profiles.json"
    profile_name = None
    if profiles_path.is_file():
        # When profiles are configured, use the selected local/server endpoint.
        # Both profiles remain restricted to the isolated test database here.
        try:
            from mysql_deployment_profiles import load_profile
            profile_name, cfg = load_profile(app_dir, profile=profile)
        except Exception as exc:
            raise MySQLConfigError(str(exc)) from exc
    else:
        path = app_dir / CONFIG_NAME
        if not path.is_file():
            raise MySQLConfigError("لم يتم العثور على mysql_config.json أو mysql_profiles.json")
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise MySQLConfigError("ملف إعداد MySQL غير صالح") from exc
    if not isinstance(cfg, dict):
        raise MySQLConfigError("بنية إعداد MySQL غير صحيحة")
    host = str(cfg.get("host", "127.0.0.1")).strip()
    user = str(cfg.get("user", "")).strip()
    database = str(cfg.get("database", "")).strip()
    try:
        port = int(cfg.get("port", 3306))
    except (TypeError, ValueError) as exc:
        raise MySQLConfigError("منفذ MySQL غير صالح") from exc
    if not host or not user or not database:
        raise MySQLConfigError("الخادم واسم المستخدم وقاعدة البيانات مطلوبة")
    if not 1 <= port <= 65535:
        raise MySQLConfigError("منفذ MySQL خارج النطاق الصحيح")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise MySQLConfigError("اسم قاعدة البيانات يحتوي على رموز غير مسموحة")
    if enforce_test_db and database != ALLOWED_TEST_DATABASE:
        raise MySQLConfigError("هذا الإصدار المرشح يسمح بالاختبار على salah_archive_test فقط")
    # Prefer a profile-specific secret; retain the shared variable for backward compatibility.
    # Passwords are never stored in JSON.
    profile_password_env = f"{PASSWORD_ENV}_{str(profile_name).upper()}" if profile_name else ""
    password = (os.environ.get(profile_password_env, "") if profile_password_env else "") or os.environ.get(PASSWORD_ENV, "")
    if require_password and not password:
        raise MySQLConfigError(
            "كلمة مرور MySQL غير موجودة. عيّن متغير البيئة SALAH_MYSQL_PASSWORD ثم أعد تشغيل التطبيق."
        )
    return {
        "host": host, "port": port, "database": database,
        "user": user, "password": password
    }

def save_config(app_dir, cfg, *, enforce_test_db=True):
    app_dir = Path(app_dir)
    database = str(cfg.get("database", "")).strip()
    if enforce_test_db and database != ALLOWED_TEST_DATABASE:
        raise MySQLConfigError("اسم قاعدة الهدف يجب أن يكون salah_archive_test")
    safe = {
        "host": str(cfg.get("host", "127.0.0.1")).strip(),
        "port": int(cfg.get("port", 3306)),
        "database": database,
        "user": str(cfg.get("user", "")).strip()
    }
    if not safe["host"] or not safe["user"] or not safe["database"]:
        raise MySQLConfigError("الخادم واسم المستخدم وقاعدة البيانات مطلوبة")
    if not 1 <= safe["port"] <= 65535:
        raise MySQLConfigError("منفذ MySQL خارج النطاق الصحيح")
    path = app_dir / CONFIG_NAME
    path.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path
