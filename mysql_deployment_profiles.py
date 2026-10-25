# -*- coding: utf-8 -*-
"""Safe local/server MySQL profile management for Salah Archive pre-production.

Profiles intentionally target only salah_archive_test. Passwords are never saved.
Select the profile with SALAH_ARCHIVE_DB_PROFILE=local|server.
"""
from __future__ import annotations
import json, os, re
from pathlib import Path

PROFILES_NAME = "mysql_profiles.json"
ALLOWED_DATABASE = "salah_archive_test"
VALID_PROFILES = {"local", "server"}
class DeploymentProfileError(ValueError):
    pass

def _validate_entry(name, item, *, allow_incomplete=False):
    if name not in VALID_PROFILES or not isinstance(item, dict):
        raise DeploymentProfileError("ملف إعدادات الوضع المحلي/السيرفر غير صالح")
    host = str(item.get("host", "")).strip()
    user = str(item.get("user", "")).strip()
    database = str(item.get("database", ALLOWED_DATABASE)).strip()
    try: port = int(item.get("port", 3306))
    except (TypeError, ValueError) as exc: raise DeploymentProfileError("منفذ MySQL غير صالح") from exc
    if not host or not user:
        if allow_incomplete:
            return {"host": host, "port": port, "database": database, "user": user}
        raise DeploymentProfileError(f"أكمل عنوان الخادم واسم المستخدم لوضع {name}")
    if host.lower() in {"server-ip-here", "set-server-ip", "your-server"}:
        raise DeploymentProfileError("يجب كتابة عنوان السيرفر الحقيقي داخل الشبكة")
    if not 1 <= port <= 65535: raise DeploymentProfileError("منفذ MySQL خارج النطاق الصحيح")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database): raise DeploymentProfileError("اسم قاعدة البيانات غير صالح")
    if database != ALLOWED_DATABASE:
        raise DeploymentProfileError("مرحلة ما قبل الإنتاج تسمح بقاعدة salah_archive_test فقط؛ قاعدة الإنتاج محمية")
    return {"host": host, "port": port, "database": database, "user": user}

def save_profiles(app_dir, profiles, active_profile="local"):
    if active_profile not in VALID_PROFILES: raise DeploymentProfileError("الوضع يجب أن يكون local أو server")
    if not isinstance(profiles, dict) or set(profiles) != VALID_PROFILES:
        raise DeploymentProfileError("يجب توفير إعدادات local وserver معاً")
    clean = {name: _validate_entry(name, profiles[name], allow_incomplete=(name != active_profile)) for name in sorted(VALID_PROFILES)}
    # The active profile must always be complete; the inactive one may be filled later.
    _validate_entry(active_profile, clean[active_profile])
    path = Path(app_dir) / PROFILES_NAME
    path.write_text(json.dumps({"active_profile": active_profile, "profiles": clean}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try: os.chmod(path, 0o600)
    except OSError: pass
    return path

def load_profile(app_dir, profile=None, *, respect_environment=True):
    path = Path(app_dir) / PROFILES_NAME
    if not path.is_file(): raise DeploymentProfileError("لم يتم العثور على mysql_profiles.json")
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise DeploymentProfileError("ملف mysql_profiles.json غير صالح") from exc
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise DeploymentProfileError("بنية ملف ملفات الاتصال غير صحيحة")
    environment_profile = os.environ.get("SALAH_ARCHIVE_DB_PROFILE") if respect_environment else None
    chosen = (profile or environment_profile or data.get("active_profile") or "local").strip().lower()
    if chosen not in VALID_PROFILES: raise DeploymentProfileError("اختر local أو server في SALAH_ARCHIVE_DB_PROFILE")
    item = data["profiles"].get(chosen)
    return chosen, _validate_entry(chosen, item)
