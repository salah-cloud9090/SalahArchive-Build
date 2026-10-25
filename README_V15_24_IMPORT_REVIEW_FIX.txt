VERSION 15.24 - IMPORT TO INDEX REVIEW FIX

Changes:
- Importing one PDF/image to a basket now runs the existing OCR/local-AI analysis attempt and then opens the editable book-indexing screen directly.
- Importing a one-file batch does the same.
- If OCR/AI cannot run, the indexing screen should show the stored error and still allow manual indexing; the original file remains in the basket.
- Multi-file batches remain in the basket screen so each item can be reviewed separately.

Important limitations:
- This change fixes the navigation/workflow, not missing OCR engines or a missing/unloaded local AI model.
- If extracted text/fields are still empty, run DIAGNOSTICS.bat and share diagnostics_report.txt. Check that Tesseract and Arabic language data (ara) are installed, and that LM Studio has a model loaded if local AI is expected.
- Python syntax check passed; not tested on the user's Windows computer or actual scanner.
- Keep the older folder and database until the new build is verified.
