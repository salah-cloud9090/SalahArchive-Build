# -*- coding: utf-8 -*-
"""Offline activation smoke tests; uses temporary folders only."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('license_core', ROOT / 'license_core.py')
license_core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(license_core)
ISSUER = ROOT / 'ADMIN_ONLY_KEEP_PRIVATE' / 'issue_activation_key.py'

class ActivationFlowTests(unittest.TestCase):
    def issue(self, machine):
        return subprocess.check_output([sys.executable, str(ISSUER), machine], text=True).strip()

    @unittest.skipUnless(ISSUER.is_file(), 'Offline private activation issuer is intentionally excluded from distributable package')
    def test_issued_key_verifies_for_correct_product_version_and_machine(self):
        machine = 'TESTMACHINE-ONLY-0001'
        token = self.issue(machine)
        ok, details = license_core.verify_token(token, expected_machine=machine)
        self.assertTrue(ok, details)
        self.assertEqual(details['product'], license_core.PRODUCT)
        self.assertEqual(details['version'], license_core.VERSION)
        self.assertEqual(details['machine'], machine)

    @unittest.skipUnless(ISSUER.is_file(), 'Offline private activation issuer is intentionally excluded from distributable package')
    def test_key_is_rejected_for_another_machine(self):
        token = self.issue('TESTMACHINE-ONLY-0002')
        ok, reason = license_core.verify_token(token, expected_machine='OTHER-MACHINE')
        self.assertFalse(ok)
        self.assertEqual(reason, 'الترخيص مخصص لجهاز آخر')

    @unittest.skipUnless(ISSUER.is_file(), 'Offline private activation issuer is intentionally excluded from distributable package')
    def test_activation_saves_and_reloads_only_in_temporary_folder(self):
        machine = license_core.machine_fingerprint
        token = self.issue(machine())
        with tempfile.TemporaryDirectory(prefix='salah-activation-test-') as td:
            self.assertFalse(license_core.is_activated(td))
            ok, message = license_core.activate(td, token)
            self.assertTrue(ok, message)
            self.assertTrue(license_core.is_activated(td))
            self.assertTrue((Path(td) / 'license.key').is_file())

    def test_bad_token_is_rejected(self):
        ok, reason = license_core.verify_token('not-a-license-token')
        self.assertFalse(ok)
        self.assertEqual(reason, 'رمز التفعيل غير صالح')

if __name__ == '__main__':
    unittest.main(verbosity=2)
