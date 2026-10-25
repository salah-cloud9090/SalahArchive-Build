from pathlib import Path
import unittest

ROOT = Path(__file__).parent
SRC = (ROOT / 'main.py').read_text(encoding='utf-8')

class AdminSecurityPatchTests(unittest.TestCase):
    def test_logout_is_post_and_get_does_not_destroy_session(self):
        get_source = SRC.split('def do_GET(self):',1)[1].split('def do_POST(self):',1)[0]
        get_route = get_source.split("if path == '/logout':", 1)[1].split("if path == '/admin-confirm':", 1)[0]
        self.assertIn('تأكيد تسجيل الخروج', get_route)
        self.assertNotIn('SESSIONS.pop(token, None)', get_route)
        self.assertIn("if path == '/logout-confirm':", SRC)
        self.assertIn("if path == '/logout-confirm':", SRC.split('def do_POST',1)[1])

    def test_admin_reauthentication_exists_and_has_timeout(self):
        self.assertIn('def admin_reauth_ok(token):', SRC)
        self.assertIn("if path == '/admin-confirm':", SRC)
        self.assertIn("verify_user(user['username'],f.get('admin_password',''))", SRC)
        self.assertIn("item['admin_reauth_until']=time.time()+600", SRC)

    def test_sensitive_routes_have_server_side_role_and_reauth_checks(self):
        self.assertIn("sensitive=(path in ('/mysql','/cabinets','/baskets-settings','/users')", SRC)
        self.assertIn("sensitive_post=path in ('/mysql-save','/mysql-test','/add-cabinet','/basket-settings-save','/basket-settings-delete','/users-save','/users-password','/users-toggle')", SRC)
        self.assertIn("user['role']!='admin' or not admin_reauth_ok(token)", SRC)

    def test_menu_uses_admin_settings_link_and_post_logout(self):
        self.assertIn('href="/admin-settings"', SRC)
        self.assertIn('action="/logout-confirm"', SRC)
        self.assertNotIn('href="/logout" class="logout-link"', SRC)

if __name__ == '__main__':
    unittest.main(verbosity=2)
