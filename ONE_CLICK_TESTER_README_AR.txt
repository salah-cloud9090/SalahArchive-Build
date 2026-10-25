SALAH ARCHIVE v15.81 — ONE CLICK TESTER

1) Extract this ZIP into a NEW folder. Do not overwrite the current application.
2) Double-click RUN_FULL_TESTS.bat.
3) It runs syntax checks, unit tests, isolated SQLite smoke test and integrity check.
4) When asked, enter y only if you want a live connection test. It asks for the password without showing it and is guarded to the test database `salah_archive_test` only.
5) Read FULL_TEST_REPORT.txt or FULL_TEST_REPORT.json in this folder.

Important: the live MySQL test requires the local MySQL test profile and mysql-connector-python. A failed login (1045) means MySQL rejected the test credentials; the report will show this. Do not change any production database settings to make the test pass. No password is saved in the report.
This is a Windows batch test launcher, not a signed standalone EXE. It does not claim that a live MySQL test passed unless the test actually ran.
