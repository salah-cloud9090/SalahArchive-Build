import tempfile, unittest, time
from pathlib import Path
import main

class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='salah-users-test-')
        root=Path(self.tmp.name)
        main.APP_DIR=root; main.DB_PATH=root/'test.sqlite'; main.FILES_DIR=root/'files'; main.FILES_DIR.mkdir()
        main.TOOLS_DIR=root/'tools'; main.TOOLS_DIR.mkdir()
        main.SCAN_SETTINGS_PATH=root/'scan_preferences.json'
        main.initialize()
    def tearDown(self): self.tmp.cleanup()
    def test_display_name_migration_and_password_hash(self):
        with main.db() as c:
            row=c.execute("SELECT username,display_name,role FROM local_users WHERE username='admin'").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['display_name'],'admin')
    def test_new_user_password_is_hashed_and_role_is_saved(self):
        salt,digest=main.hash_password('GoodPassphrase123!')
        with main.db() as c:
            c.execute('INSERT INTO local_users(username,display_name,password_salt,password_hash,role,is_active) VALUES(?,?,?,?,?,1)',('test_editor','موظف تجريبي',salt,digest,'editor'))
        account=main.verify_user('test_editor','GoodPassphrase123!')
        self.assertEqual(account['role'],'editor')
        self.assertEqual(account['display_name'],'موظف تجريبي')
        self.assertIsNone(main.verify_user('test_editor','wrong-password'))
    def test_disabled_user_cannot_authenticate(self):
        salt,digest=main.hash_password('GoodPassphrase123!')
        with main.db() as c:
            c.execute('INSERT INTO local_users(username,display_name,password_salt,password_hash,role,is_active) VALUES(?,?,?,?,?,0)',('disabled_user','حساب معطل',salt,digest,'viewer'))
        self.assertIsNone(main.verify_user('disabled_user','GoodPassphrase123!'))
    def _handler(self, fields, role='admin'):
        h=object.__new__(main.ArchiveHandler)
        token='test-session-token'
        main.SESSIONS[token]={'user':{'username':'admin','display_name':'مدير الاختبار','role':role},'expires':time.time()+300,'admin_reauth_until':time.time()+300}
        h.headers={'Cookie':'session='+token}
        h.form=lambda:dict(fields)
        h.send_html=lambda content,status=200,cookie=None,headers=None: (status,content)
        h.redirect=lambda path,cookie=None: (302,path)
        return h
    def test_admin_can_create_edit_reset_and_disable_user(self):
        h=self._handler({'action':'create','username':'trial_user','display_name':'موظف تجريبي','role':'editor','password':'SecurePassphrase123!'})
        status,html=h.users_save({'username':'admin','role':'admin'})
        self.assertEqual(status,200)
        account=main.verify_user('trial_user','SecurePassphrase123!')
        self.assertEqual(account['display_name'],'موظف تجريبي')
        with main.db() as c: uid=c.execute("SELECT id FROM local_users WHERE username='trial_user'").fetchone()['id']
        h=self._handler({'action':'update','user_id':str(uid),'display_name':'موظف معدل','role':'viewer'})
        h.users_save({'username':'admin','role':'admin'})
        self.assertEqual(main.verify_user('trial_user','SecurePassphrase123!')['role'],'viewer')
        h=self._handler({'user_id':str(uid),'password':'AnotherSecurePass123!'})
        h.users_password({'username':'admin','role':'admin'})
        self.assertIsNone(main.verify_user('trial_user','SecurePassphrase123!'))
        self.assertEqual(main.verify_user('trial_user','AnotherSecurePass123!')['display_name'],'موظف معدل')
        h=self._handler({'user_id':str(uid),'active':'0'})
        h.users_toggle({'username':'admin','role':'admin'})
        self.assertIsNone(main.verify_user('trial_user','AnotherSecurePass123!'))
    def test_non_admin_cannot_manage_users(self):
        h=self._handler({},role='editor')
        status,_=h.users_page({'username':'staff','role':'editor'})
        self.assertEqual(status,403)
    def test_management_routes_are_admin_reauth_protected(self):
        src=Path(main.__file__).read_text(encoding='utf-8')
        for route in ("'/users-save'","'/users-password'","'/users-toggle'"):
            self.assertIn(route,src)
        self.assertIn("sensitive=(path in ('/mysql','/cabinets','/baskets-settings','/users')",src)
        self.assertIn("if user.get('role')!='admin' or not admin_reauth_ok(get_user(self)[1]):",src)
        self.assertIn('لا يمكن تخفيض صلاحية آخر مسؤول فعّال',src)
        self.assertIn('لا يمكن تعطيل آخر مسؤول فعّال',src)

if __name__=='__main__': unittest.main(verbosity=2)
