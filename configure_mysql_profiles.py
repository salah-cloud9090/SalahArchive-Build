# -*- coding: utf-8 -*-
"""Interactive, password-free setup for local and central MySQL TEST profiles."""
from pathlib import Path
from mysql_deployment_profiles import save_profiles

APP_DIR = Path(__file__).resolve().parent

def ask(label, default=''):
    suffix = f' [{default}]' if default else ''
    value = input(f'{label}{suffix}: ').strip()
    return value or default

def main():
    print('Salah Archive v15.81 — إعداد اتصالات MySQL التجريبية')
    print('سيتم حفظ العناوين وأسماء المستخدمين فقط. كلمات المرور لا تُحفظ هنا.')
    print('قاعدة البيانات مقفلة على salah_archive_test في هذا المرشح.\n')
    local_host = ask('عنوان MySQL المحلي', '127.0.0.1')
    local_user = ask('مستخدم الاختبار المحلي', 'archive_test_app')
    print('\nإعداد السيرفر المركزي (يمكن ترك العنوان فارغاً إلى أن تعرف IP السيرفر).')
    server_host = ask('عنوان السيرفر الداخلي', '')
    server_user = ask('مستخدم الاختبار على السيرفر', 'archive_test_app')
    profiles = {
        'local': {'host': local_host, 'port': 3306, 'database': 'salah_archive_test', 'user': local_user},
        'server': {'host': server_host, 'port': 3306, 'database': 'salah_archive_test', 'user': server_user},
    }
    path = save_profiles(APP_DIR, profiles, active_profile='local')
    print(f'\nتم حفظ الإعدادات غير السرية: {path}')
    print('الوضع الفعال: local. لا يوجد اتصال بخادم أو إنشاء جداول أثناء هذا الإعداد.')
    print('في وضع server تعمل واجهة البرنامج على حاسبة السيرفر، وتدخل بقية الحاسبات عبر المتصفح والمنفذ 8765؛ لا يلزم فتح MySQL 3306 للمستخدمين.')
    print('شغّل START_MYSQL_TEST.bat بعد تجهيز المستخدم والصلاحيات في MySQL Workbench.')

if __name__ == '__main__':
    main()
