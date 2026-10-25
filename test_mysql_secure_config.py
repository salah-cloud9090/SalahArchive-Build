# -*- coding: utf-8 -*-
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from mysql_secure_config import save_config, load_config, MySQLConfigError, PASSWORD_ENV, CONFIG_NAME

class SecureConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=Path(self.tmp.name)
        os.environ.pop(PASSWORD_ENV,None); os.environ.pop(PASSWORD_ENV+'_LOCAL',None); os.environ.pop(PASSWORD_ENV+'_SERVER',None)
    def tearDown(self):
        os.environ.pop(PASSWORD_ENV,None); os.environ.pop(PASSWORD_ENV+'_LOCAL',None); os.environ.pop(PASSWORD_ENV+'_SERVER',None)
        self.tmp.cleanup()
    def test_save_never_persists_password(self):
        save_config(self.app, {'host':'127.0.0.1','port':3306,'database':'salah_archive_test','user':'archive_app','password':'SECRET'})
        raw=(self.app/CONFIG_NAME).read_text(encoding='utf-8')
        self.assertNotIn('SECRET',raw)
        self.assertNotIn('password',json.loads(raw))
    def test_rejects_original_database(self):
        with self.assertRaises(MySQLConfigError):
            save_config(self.app, {'host':'127.0.0.1','port':3306,'database':'salah_archive','user':'archive_app'})
    def test_rejects_other_database(self):
        with self.assertRaises(MySQLConfigError):
            save_config(self.app, {'host':'127.0.0.1','port':3306,'database':'archive_prod','user':'archive_app'})
    def test_requires_environment_password(self):
        save_config(self.app, {'host':'127.0.0.1','port':3306,'database':'salah_archive_test','user':'archive_app'})
        with self.assertRaises(MySQLConfigError):
            load_config(self.app,require_password=True)
    def test_uses_environment_password_not_legacy_json(self):
        (self.app/CONFIG_NAME).write_text(json.dumps({'host':'127.0.0.1','port':3306,'database':'salah_archive_test','user':'archive_app','password':'OLD_SECRET'}),encoding='utf-8')
        os.environ[PASSWORD_ENV]='ENV_SECRET'
        cfg=load_config(self.app,require_password=True)
        self.assertEqual(cfg['password'],'ENV_SECRET')
        self.assertNotEqual(cfg['password'],'OLD_SECRET')
    def test_rejects_invalid_port(self):
        with self.assertRaises(MySQLConfigError):
            save_config(self.app, {'host':'127.0.0.1','port':70000,'database':'salah_archive_test','user':'archive_app'})
    def test_rejects_unsafe_db_name(self):
        with self.assertRaises(MySQLConfigError):
            save_config(self.app, {'host':'127.0.0.1','port':3306,'database':'salah_archive_test;DROP','user':'archive_app'})
if __name__=='__main__': unittest.main(verbosity=2)
