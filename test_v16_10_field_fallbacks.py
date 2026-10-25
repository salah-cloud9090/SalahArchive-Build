# Focused regression tests for v16.10 field fallback behavior.
import unittest
import main

class FieldFallbackTests(unittest.TestCase):
    def test_arabic_number_date_subject_and_department(self):
        text='وزارة الصحة\nمديرية الأحوال المدنية والجوازات والإقامة\nالعدد: ٧٦٦\nالتاريخ: 25/10/2026\nالموضوع: أمر إداري\nقسم إدارة الأفراد / شعبة الترقية'
        v=main._normalize_ai_index_values({},text)
        self.assertEqual(v['document_number'],'766')
        self.assertEqual(v['document_date'],'2026-10-25')
        self.assertIn('أمر إداري',v['subject'])
        self.assertIn('قسم إدارة الأفراد',v['department'])
        self.assertIn('مديرية الأحوال المدنية',v['origin_entity'])
        self.assertTrue(v['keywords'])
        self.assertTrue(v['notes'])
        self.assertIn('أمر إداري',v['notes'])
    def test_no_guessing_when_text_empty(self):
        v=main._normalize_ai_index_values({},'')
        self.assertEqual(v.get('document_number',''),'')
        self.assertEqual(v.get('document_date',''),'')
        self.assertEqual(v.get('subject',''),'')
        self.assertEqual(v.get('origin_entity',''),'')
    def test_model_fields_are_preserved(self):
        v=main._normalize_ai_index_values({'document_number':'1234','subject':'طلب معلومات'},'')
        self.assertEqual(v['document_number'],'1234')
        self.assertEqual(v['subject'],'طلب معلومات')

if __name__=='__main__': unittest.main(verbosity=2)
