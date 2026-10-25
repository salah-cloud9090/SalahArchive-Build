# -*- coding: utf-8 -*-
import ast, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
class MySQLProfileUITests(unittest.TestCase):
    def test_candidate_has_both_profile_forms(self):
        src=(ROOT/'main_mysql_candidate_v15_81.py').read_text(encoding='utf-8')
        self.assertIn("('local','اتصال محلي — البرنامج وقاعدة الاختبار على نفس الحاسبة')",src)
        self.assertIn("('server','اتصال السيرفر المركزي — شغّل البرنامج على حاسبة السيرفر')",src)
        self.assertIn("name=\"active_profile\"",src)
        self.assertIn("--profile",(ROOT/'run_mysql_application.py').read_text(encoding='utf-8'))
        self.assertIn("local_archive_files",(ROOT/'README_V15_81_LOCAL_SERVER_INTEGRATION_AR.txt').read_text(encoding='utf-8'))
    def test_ui_never_accepts_database_name_from_form(self):
        src=(ROOT/'main_mysql_candidate_v15_81.py').read_text(encoding='utf-8')
        self.assertIn("'database':'salah_archive_test'",src)
        self.assertNotIn("f.get('database'",src)
    def test_candidate_compiles(self):
        ast.parse((ROOT/'main_mysql_candidate_v15_81.py').read_text(encoding='utf-8'))

if __name__=='__main__': unittest.main(verbosity=2)

class LiveIntegrationGuardTests(unittest.TestCase):
    def test_live_test_uses_test_db_guard_and_real_application_initialize(self):
        src=(ROOT/'mysql_live_integration_test.py').read_text(encoding='utf-8')
        self.assertIn("load_config(ROOT, require_password=True, enforce_test_db=True)",src)
        self.assertIn('app.initialize()',src)
        self.assertIn("'__V1581_TEST_DOC_'",src)
        self.assertIn('finally:',src)
        self.assertIn('file_path.unlink(missing_ok=True)',src)
    def test_live_test_launcher_uses_hidden_python_password_prompt(self):
        src=(ROOT/'run_mysql_integration.py').read_text(encoding='utf-8')
        common=(ROOT/'mysql_test_runner_common.py').read_text(encoding='utf-8')
        wrapper=(ROOT/'Test-SalahArchiveMySQL.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('getpass.getpass',src)
        self.assertIn('build_child_environment',common)
        self.assertIn('SALAH_MYSQL_PASSWORD_',common)
        self.assertNotIn('WriteAllText',common)
        self.assertIn('run_mysql_integration.py',wrapper)

    def test_test_bat_launchers_no_longer_depend_on_powershell(self):
        for name in ('TEST_MYSQL_INTEGRATION.bat','TEST_MYSQL_INTEGRATION_LOCAL.bat','TEST_MYSQL_INTEGRATION_SERVER.bat'):
            src=(ROOT/name).read_text(encoding='ascii')
            self.assertIn('run_mysql_integration.py',src)
            self.assertNotIn('powershell ',src.lower())
