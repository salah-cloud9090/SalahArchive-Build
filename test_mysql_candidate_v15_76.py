import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class MySQLCandidateV1576Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / 'main.py').read_bytes()
        cls.candidate = (ROOT / 'main_mysql_candidate_v15_76.py').read_text(encoding='utf-8')
        cls.manifest = json.loads((ROOT / 'integrity_manifest.json').read_text(encoding='utf-8'))
        cls.patch = (ROOT / 'MYSQL_RUNTIME_INTEGRATION.patch').read_text(encoding='utf-8')

    def test_current_main_matches_signed_manifest_hash(self):
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), self.manifest['files']['main.py'])

    def test_legacy_mysql_candidate_is_kept_separate_from_updated_application(self):
        # The signed application source is updated for the UI/attachment/council workflow;
        # the experimental MySQL patch candidate remains a separate, explicitly uninstalled file.
        self.assertIn('def mysql_backend_enabled():', self.candidate)
        self.assertIn('aiAttachmentInfo', self.original.decode('utf-8'))
        self.assertNotEqual(hashlib.sha256(self.original).hexdigest(), hashlib.sha256(self.candidate.encode()).hexdigest())

    def test_mysql_mode_is_opt_in(self):
        self.assertIn("os.environ.get('SALAH_ARCHIVE_DB_BACKEND', '').strip().lower() == 'mysql'", self.candidate)

    def test_test_database_connector_is_used(self):
        self.assertIn('connect_test_database(APP_DIR)', self.candidate)
        self.assertIn('ensure_schema(c._connection, APP_DIR /', self.candidate)

    def test_candidate_patch_applies_to_the_preserved_main_source(self):
        self.assertTrue(self.patch.startswith('--- a/main.py\n+++ b/main.py'))
        self.assertIn('@@ -99,13 +99,27 @@', self.patch)

    def test_candidate_does_not_claim_live_mysql_validation(self):
        gate = json.loads((ROOT / 'MYSQL_CANDIDATE_STATIC_GATE.json').read_text(encoding='utf-8'))
        self.assertIn('No MySQL server connection was attempted.', gate['limitations'])
        self.assertIn('Candidate remains unsigned and is not installed over main.py.', gate['limitations'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
