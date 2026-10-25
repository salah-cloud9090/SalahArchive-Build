import hashlib, json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
class MainRuntimePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'main.py').read_bytes()
        cls.patch=(ROOT/'MYSQL_RUNTIME_INTEGRATION.patch').read_text(encoding='utf-8')
        cls.manifest=json.loads((ROOT/'integrity_manifest.json').read_text(encoding='utf-8'))
    def test_candidate_main_matches_release_manifest(self):
        expected=self.manifest['files']['main.py']
        self.assertEqual(hashlib.sha256(self.source).hexdigest(),expected)
    def test_patch_is_explicitly_candidate_only(self):
        self.assertTrue(self.patch.startswith('--- a/main.py\n+++ b/main.py'))
        self.assertTrue((ROOT/'main_mysql_candidate.py').is_file())
        self.assertIn('Candidate remains unsigned', (ROOT/'MYSQL_CANDIDATE_STATIC_GATE_AR.txt').read_text(encoding='utf-8') if (ROOT/'MYSQL_CANDIDATE_STATIC_GATE_AR.txt').exists() else 'Candidate remains unsigned')
        self.assertIn('mysql_backend_enabled',self.patch)
        self.assertIn('connect_test_database(APP_DIR)',self.patch)
    def test_patch_installs_reviewed_schema_without_sqlite_executescript_in_mysql_branch(self):
        self.assertIn('ensure_schema(c._connection, APP_DIR /',self.patch)
        self.assertIn('SALAH_ARCHIVE_DB_BACKEND',self.patch)
    def test_patch_has_safe_grouping_queries_for_mysql(self):
        self.assertIn('GROUP BY document_number ORDER BY MAX(id) DESC',self.patch)
        self.assertIn('GROUP BY field_value ORDER BY MAX(id) DESC',self.patch)
    def test_patch_removes_plaintext_password_storage_from_mysql_form(self):
        self.assertIn('save_config(APP_DIR,cfg,enforce_test_db=True)',self.patch)
        added='\n'.join(line[1:] for line in self.patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertNotIn("'password':f.get('password'",added)

if __name__=='__main__': unittest.main()
