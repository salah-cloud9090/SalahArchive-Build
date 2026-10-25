"""Regression tests for the optional MySQL index screen. No DB connection."""
from mysql_safety import validate_mysql_test_database


def test_test_database_allowed():
    assert validate_mysql_test_database('salah_archive_test') == 'salah_archive_test'


def test_original_database_blocked_case_insensitive():
    for name in ('salah_archive', 'SALAH_ARCHIVE', 'Salah_Archive'):
        try:
            validate_mysql_test_database(name)
        except ValueError as exc:
            assert 'الأصلية محمية' in str(exc)
        else:
            raise AssertionError(f'protected database accepted: {name}')


def test_other_database_blocked():
    for name in ('administrative_archive', 'salah_archive2', '', None):
        try:
            validate_mysql_test_database(name)
        except ValueError:
            pass
        else:
            raise AssertionError(f'non-test database accepted: {name!r}')


if __name__ == '__main__':
    tests = [test_test_database_allowed, test_original_database_blocked_case_insensitive, test_other_database_blocked]
    for test in tests:
        test(); print('PASS', test.__name__)
    print(f'{len(tests)}/{len(tests)} tests passed; no MySQL connection made.')
