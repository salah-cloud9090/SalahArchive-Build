import unittest
from pathlib import Path
import main

class V1614ReferenceUITests(unittest.TestCase):
    def setUp(self):
        self.source = Path(main.__file__).read_text(encoding='utf-8')

    def test_four_zone_council_layout_is_explicit_and_left_to_right(self):
        self.assertIn('direction:ltr!important;display:grid!important;grid-template-columns:minmax(170px,.78fr) minmax(285px,1.28fr) minmax(245px,1fr) minmax(155px,.68fr)!important', self.source)
        self.assertIn('.case-create-layout:not(.case-workspace-layout) .case-files-panel{{grid-column:1!important;grid-row:1!important', self.source)
        self.assertIn('.case-create-layout:not(.case-workspace-layout) .case-preview-panel{{grid-column:2!important;grid-row:1!important', self.source)
        self.assertIn('.case-create-layout:not(.case-workspace-layout)>.case-meta-panel{{grid-column:3!important;grid-row:1!important', self.source)
        self.assertIn('.case-create-layout:not(.case-workspace-layout)>.case-ai-panel{{grid-column:4!important;grid-row:1!important', self.source)

    def test_responsive_layout_rules_exist(self):
        self.assertIn('@media(max-width:1120px)', self.source)
        self.assertIn('@media(max-width:850px)', self.source)

    def test_dashboard_uses_database_counts_not_static_mock_values(self):
        self.assertIn('SELECT COUNT(*) n FROM local_documents', self.source)
        self.assertIn('stats.get(\'incoming\',0)', self.source)
        self.assertIn('stats.get(\'outgoing\',0)', self.source)
        self.assertIn('home-bottom-actions', self.source)

    def test_navigation_and_admin_menu_are_real_routes(self):
        self.assertIn('href="/cases"', self.source)
        self.assertIn('href="/users"', self.source)
        self.assertIn('href="/admin-settings"', self.source)

    def test_existing_autofill_fallbacks_are_preserved(self):
        values = main._normalize_ai_index_values({}, 'وزارة الصحة\nالعدد: ٧٦٦\nالتاريخ: 25/10/2026\nالموضوع: طلب معلومات')
        self.assertEqual(values['document_number'], '766')
        self.assertEqual(values['document_date'], '2026-10-25')
        self.assertTrue(values['subject'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
