import unittest
from pathlib import Path
import main

class V1613LayoutAndAutofillTests(unittest.TestCase):
    def test_council_metadata_panel_closes_before_workspace(self):
        s=Path(main.__file__).read_text(encoding='utf-8')
        self.assertIn('<textarea name="notes" rows="3"></textarea></div></div><hr><h3>اختر الكتب ورتّبها',s)
        self.assertIn('class="case-ai-panel"',s)
        self.assertIn('home-bottom-actions',s)
        self.assertIn('/dashboard-hero.svg',s)
        self.assertIn('grid-template-columns:minmax(170px,.78fr) minmax(290px,1.3fr) minmax(245px,1fr) minmax(175px,.7fr)!important',s)
    def test_scan_form_does_not_invent_today_as_document_date(self):
        s=Path(main.__file__).read_text(encoding='utf-8')
        self.assertIn('ai_values.get("document_date") or (today if not scan_row else "")',s)
    def test_first_pass_suggestion_normalized_and_bounded_retry_exists(self):
        s=Path(main.__file__).read_text(encoding='utf-8')
        self.assertIn('self._normalize_scan_suggestion(raw_suggestion, extracted_for_index)',s)
        self.assertIn('One bounded retry: background processing can race with the form opening.',s)
    def test_no_fabricated_date_or_number_on_empty_text(self):
        v=main._normalize_ai_index_values({},'')
        self.assertEqual(v.get('document_number',''),'')
        self.assertEqual(v.get('document_date',''),'')
    def test_realistic_arabic_fields_fallback(self):
        text='وزارة الصحة\nالعدد: ٧٦٦\nالتاريخ: 25/10/2026\nالموضوع: طلب معلومات\nقسم إدارة الأفراد'
        v=main._normalize_ai_index_values({},text)
        self.assertEqual(v['document_number'],'766')
        self.assertEqual(v['document_date'],'2026-10-25')
        self.assertIn('طلب معلومات',v['subject'])
        self.assertTrue(v['keywords'])

if __name__=='__main__': unittest.main(verbosity=2)
