VERSION 15.26 - ARABIC BOOK NUMBER EXTRACTION

Changes:
- Strengthened the local fallback that looks for official book numbers near Arabic labels such as العدد، رقم الكتاب، رقم الصادر، and رقم.
- Handles Arabic-Indic/Persian digits and common number formats containing /, - or .
- Strengthened the local AI prompt to explicitly read Arabic numerals and prioritize the printed number rather than the application record ID.
- Preserved the processing indicator from v15.25.
- Python syntax compilation passed. This does not guarantee OCR quality for every scan: the actual printed number must be legible to OCR or the local vision model. Verify the suggested number before archiving.
