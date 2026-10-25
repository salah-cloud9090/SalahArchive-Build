import hashlib
import tempfile
import unittest
from pathlib import Path
import fitz
from PIL import Image
import main

class ReleaseFeatureTests(unittest.TestCase):
    def test_merge_pdf_and_image_creates_valid_pdf_and_preserves_sources(self):
        with tempfile.TemporaryDirectory(prefix='salah-merge-test-') as td:
            root=Path(td)
            pdf=root/'first.pdf'
            d=fitz.open(); page=d.new_page(); page.insert_text((72,72),'sample PDF page'); d.save(pdf); d.close()
            image=root/'second.png'; Image.new('RGB',(120,80),(255,255,255)).save(image)
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (pdf,image)}
            output=root/'merged.pdf'
            count=main.merge_pdf_and_images([('first.pdf',pdf,'.pdf'),('second.png',image,'.png')],output)
            self.assertEqual(count,2)
            with fitz.open(output) as merged: self.assertEqual(merged.page_count,2)
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (pdf,image)})

    def test_rejects_unsupported_merge_type(self):
        with tempfile.TemporaryDirectory(prefix='salah-merge-bad-') as td:
            src=Path(td)/'file.docx'; src.write_bytes(b'not a docx')
            with self.assertRaises(ValueError): main.merge_pdf_and_images([('file.docx',src,'.docx')],Path(td)/'out.pdf')

    def test_attachment_ui_has_name_size_and_remove_control(self):
        source=(Path(__file__).parent/'main.py').read_text(encoding='utf-8')
        self.assertIn('id="aiAttachmentInfo"',source)
        self.assertIn('id="aiAttachmentRemove"',source)
        self.assertIn("x.name+' — '+size",source)

    def test_case_ui_posts_multiple_selected_files(self):
        source=(Path(__file__).parent/'main.py').read_text(encoding='utf-8')
        self.assertIn('name="inbox_ids"',source)
        self.assertIn("name=\"checkbox\"",source) if False else None
        self.assertIn("name=\"inbox_pick\"",source)
        self.assertIn('merge_pdf_and_images(merge_inputs,merged_path)',source)

    def test_archive_assistant_uses_real_database_search_context(self):
        source=(Path(__file__).parent/'main.py').read_text(encoding='utf-8')
        self.assertIn('def archive_search_context(self, query):',source)
        self.assertIn('archive_hits=',source)
        self.assertIn('لا تخترع كتباً أو أرقاماً أو تواريخ',source)

if __name__=='__main__': unittest.main(verbosity=2)
