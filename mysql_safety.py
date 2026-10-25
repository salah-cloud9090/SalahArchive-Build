# -*- coding: utf-8 -*-
"""Safety gate for the experimental MySQL index screen.

This does not switch the application's primary SQLite backend. It only prevents
its optional MySQL index test/sync screen from touching a non-test database.
"""
PROTECTED_DATABASE = 'salah_archive'
TEST_DATABASE = 'salah_archive_test'


def validate_mysql_test_database(database):
    name = str(database or '').strip()
    if not name:
        raise ValueError('اسم قاعدة البيانات مطلوب.')
    if name.casefold() == PROTECTED_DATABASE.casefold():
        raise ValueError('إيقاف أمان: قاعدة salah_archive الأصلية محمية ولا يسمح هذا الإصدار بالاتصال بها للكتابة.')
    if name != TEST_DATABASE:
        raise ValueError('إيقاف أمان: هذا الإصدار التجريبي يسمح فقط بقاعدة salah_archive_test.')
    return name
