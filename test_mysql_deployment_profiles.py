# -*- coding: utf-8 -*-
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from mysql_deployment_profiles import save_profiles, load_profile, DeploymentProfileError
from mysql_secure_config import load_config, MySQLConfigError, PASSWORD_ENV

class DeploymentProfilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.app=Path(self.tmp.name)
        os.environ.pop('SALAH_ARCHIVE_DB_PROFILE',None); os.environ.pop(PASSWORD_ENV,None); os.environ.pop(PASSWORD_ENV+'_LOCAL',None); os.environ.pop(PASSWORD_ENV+'_SERVER',None)
    def tearDown(self):
        os.environ.pop('SALAH_ARCHIVE_DB_PROFILE',None); os.environ.pop(PASSWORD_ENV,None); os.environ.pop(PASSWORD_ENV+'_LOCAL',None); os.environ.pop(PASSWORD_ENV+'_SERVER',None); self.tmp.cleanup()
    def good(self):
        return {'local':{'host':'127.0.0.1','port':3306,'database':'salah_archive_test','user':'test_app'},
                'server':{'host':'192.168.10.20','port':3306,'database':'salah_archive_test','user':'test_app'}}
    def test_saves_both_profiles_without_passwords(self):
        p=save_profiles(self.app,self.good()); data=json.loads(p.read_text())
        self.assertEqual(set(data['profiles']),{'local','server'}); self.assertNotIn('password',p.read_text().lower())
    def test_loads_local_profile_by_default(self):
        save_profiles(self.app,self.good()); name,cfg=load_profile(self.app)
        self.assertEqual(name,'local'); self.assertEqual(cfg['host'],'127.0.0.1')
    def test_selects_server_by_environment(self):
        save_profiles(self.app,self.good())
        with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'server'}):
            name,cfg=load_profile(self.app)
        self.assertEqual(name,'server'); self.assertEqual(cfg['host'],'192.168.10.20')
    def test_explicit_profile_overrides_active(self):
        save_profiles(self.app,self.good(),active_profile='server')
        name,cfg=load_profile(self.app,'local'); self.assertEqual(name,'local')
    def test_allows_unconfigured_inactive_server_while_local_is_active(self):
        profiles=self.good(); profiles['server']['host']=''; profiles['server']['user']=''
        save_profiles(self.app,profiles,active_profile='local')
        name,cfg=load_profile(self.app)
        self.assertEqual(name,'local'); self.assertEqual(cfg['host'],'127.0.0.1')
        with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'server'}):
            with self.assertRaises(DeploymentProfileError): load_profile(self.app)
    def test_requires_selected_server_profile_to_be_complete(self):
        profiles=self.good(); profiles['server']['host']=''; profiles['server']['user']=''
        with self.assertRaises(DeploymentProfileError): save_profiles(self.app,profiles,active_profile='server')
    def test_rejects_production_database(self):
        bad=self.good(); bad['local']['database']='salah_archive'
        with self.assertRaises(DeploymentProfileError): save_profiles(self.app,bad)
    def test_rejects_invalid_profile_name(self):
        save_profiles(self.app,self.good())
        with self.assertRaises(DeploymentProfileError): load_profile(self.app,'remote')
    def test_load_config_uses_selected_profile_and_keeps_test_guard(self):
        save_profiles(self.app,self.good())
        with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'server',PASSWORD_ENV:'test-secret'}):
            cfg=load_config(self.app,require_password=True,enforce_test_db=True)
        self.assertEqual(cfg['host'],'192.168.10.20'); self.assertEqual(cfg['database'],'salah_archive_test'); self.assertEqual(cfg['password'],'test-secret')
    def test_profile_selection_does_not_persist_password(self):
        save_profiles(self.app,self.good())
        with patch.dict(os.environ,{PASSWORD_ENV:'not-to-save'}): load_config(self.app)
        self.assertNotIn('not-to-save',(self.app/'mysql_profiles.json').read_text())
    def test_profile_specific_password_wins_over_shared_password(self):
        save_profiles(self.app,self.good())
        with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'server',PASSWORD_ENV:'shared-secret',PASSWORD_ENV+'_SERVER':'server-secret'}):
            cfg=load_config(self.app,require_password=True,enforce_test_db=True)
        self.assertEqual(cfg['password'],'server-secret')
    def test_local_and_server_can_have_distinct_passwords(self):
        save_profiles(self.app,self.good())
        with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'local',PASSWORD_ENV+'_LOCAL':'local-secret'}):
            local=load_config(self.app,require_password=True,enforce_test_db=True)
        with patch.dict(os.environ,{'SALAH_ARCHIVE_DB_PROFILE':'server',PASSWORD_ENV+'_SERVER':'server-secret'}):
            server=load_config(self.app,require_password=True,enforce_test_db=True)
        self.assertEqual(local['password'],'local-secret'); self.assertEqual(server['password'],'server-secret')
    def test_profile_file_missing_is_clear_error(self):
        with self.assertRaises(DeploymentProfileError): load_profile(self.app)

if __name__=='__main__': unittest.main(verbosity=2)
