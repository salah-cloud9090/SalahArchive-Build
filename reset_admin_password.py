# -*- coding: utf-8 -*-
"""آلية آمنة لإعادة تعيين كلمة مرور المدير دون حذف بيانات الأرشيف."""
from pathlib import Path
import hashlib
import secrets
import sqlite3
import getpass
import sys
from datetime import datetime
import shutil

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "docuware_archive.db"

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return salt.hex(), digest.hex()

def main():
    print("=" * 58)
    print("إعادة تعيين كلمة مرور مدير الأرشيف - دون حذف البيانات")
    print("قاعدة البيانات:", DB_PATH)
    print("=" * 58)
    if not DB_PATH.exists():
        print("لم أجد قاعدة البيانات في مجلد البرنامج.")
        print("شغّل START_HERE.bat مرة واحدة أولاً، ثم أعد المحاولة.")
        input("اضغط Enter للخروج...")
        return 2
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as con:
            con.row_factory = sqlite3.Row
            tables = {r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "local_users" not in tables:
                print("جدول المستخدمين غير موجود. لم أغيّر أي شيء.")
                input("اضغط Enter للخروج...")
                return 3
            row = con.execute(
                "SELECT id, username FROM local_users WHERE username='admin'"
            ).fetchone()
            if row is None:
                print("حساب admin غير موجود. لم أغيّر أي شيء.")
                input("اضغط Enter للخروج...")
                return 4
            password = getpass.getpass("اكتب كلمة المرور الجديدة (12 حرفاً على الأقل): ")
            confirm = getpass.getpass("أعد كتابة كلمة المرور: ")
            if password != confirm:
                print("كلمتا المرور غير متطابقتين. لم يتم التغيير.")
                input("اضغط Enter للخروج...")
                return 5
            if len(password) < 12:
                print("كلمة المرور قصيرة؛ استخدم 12 حرفاً على الأقل. لم يتم التغيير.")
                input("اضغط Enter للخروج...")
                return 6
            # Preserve a byte-for-byte backup before changing credentials.
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = APP_DIR / ("docuware_archive.db.backup_before_password_reset_" + stamp)
            shutil.copy2(DB_PATH, backup_path)
            salt, digest = hash_password(password)
            con.execute(
                "UPDATE local_users SET password_salt=?, password_hash=?, is_active=1 WHERE id=?",
                (salt, digest, row["id"])
            )
            con.commit()
        print("تم تحديث كلمة مرور admin فقط. لم تُحذف الكتب أو المجالس أو السلال.")
        print("نسخة احتياطية لقاعدة البيانات:", backup_path)
        print("اسم المستخدم: admin")
        print("استخدم كلمة المرور الجديدة التي كتبتها.")
        input("اضغط Enter للخروج...")
        return 0
    except sqlite3.Error as e:
        print("تعذر تحديث قاعدة البيانات:", e)
        print("أغلق البرنامج وجرّب مجدداً. لم تُحذف أي بيانات.")
        input("اضغط Enter للخروج...")
        return 7

if __name__ == "__main__":
    sys.exit(main())
