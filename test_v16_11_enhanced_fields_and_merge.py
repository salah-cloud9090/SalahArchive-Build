import hashlib, tempfile, unittest
from pathlib import Path
import fitz
from PIL import Image
import main

class V1611EnhancedFieldsAndMergeTests(unittest.TestCase):
    def test_incoming_fields_summary_keywords_and_names(self):
        text='وزارة الصحة\nالعدد: ٧٦٦\nالتاريخ: 25/10/2026\nالموضوع: طلب معلومات\nقسم إدارة الأفراد\nالأسماء:\n١- أحمد علي\n٢- محمد حسن'
        v=main._normalize_ai_index_values({'doc_type':'incoming'},text)
        self.assertEqual(v['document_number'],'766')
        self.assertEqual(v['document_date'],'2026-10-25')
        self.assertEqual(v['destination_entity'],'مديرية الجنسية والمعلومات المدنية')
        self.assertIn('طلب معلومات',v['keywords'])
        self.assertIn('أحمد علي / محمد حسن',v['employee_name'])
        self.assertIn('رقم الكتاب: 766',v['notes'])

    def test_outgoing_issuer_is_local_directorate_and_recipient_is_preserved(self):
        v=main._normalize_ai_index_values({'doc_type':'outgoing','destination_entity':'وزارة الصحة'},'مخاطبة إلى وزارة الصحة بتاريخ 25/10/2026')
        self.assertEqual(v['origin_entity'],'مديرية الجنسية والمعلومات المدنية')
        self.assertEqual(v['destination_entity'],'وزارة الصحة')
        self.assertNotIn('وزارة الصحة بتاريخ',v['origin_entity'])

    def test_empty_text_does_not_invent_number_or_date(self):
        v=main._normalize_ai_index_values({},'')
        self.assertEqual(v['document_number'],'')
        self.assertEqual(v['document_date'],'')
        self.assertEqual(v['keywords'],'')
        self.assertEqual(v['notes'],'')

    def test_pdf_plus_image_merge_is_four_pages_and_preserves_sources(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); pdf=root/'three_pages.pdf'; img=root/'image.png'; out=root/'merged.pdf'
            d=fitz.open()
            for i in range(3):
                page=d.new_page(); page.insert_text((72,72),f'Test page {i+1}')
            d.save(pdf); d.close()
            Image.new('RGB',(160,120),'white').save(img)
            hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (pdf,img)}
            count=main.merge_pdf_and_images([('three_pages.pdf',pdf,'.pdf'),('image.png',img,'.png')],out)
            self.assertEqual(count,4)
            with fitz.open(out) as merged: self.assertEqual(merged.page_count,4)
            self.assertEqual(hashes[str(pdf)],hashlib.sha256(pdf.read_bytes()).hexdigest())
            self.assertEqual(hashes[str(img)],hashlib.sha256(img.read_bytes()).hexdigest())

    def test_council_preview_controls_and_compact_save_present(self):
        source=Path(main.__file__).read_text(encoding='utf-8')
        for token in ('data-preview-action="zoom-in"','data-preview-action="zoom-out"','data-preview-action="rotate"','data-preview-action="print"','case-workspace-layout','class="case-save-button">حفظ المجلس'):
            self.assertIn(token,source)

if __name__=='__main__': unittest.main(verbosity=2)
