VERSION 15.29 — NAME SEPARATOR AND DATE INPUT FIX

- AI extraction prompt asks to separate the first and last listed people using " / " and remove duplicates.
- Date segments: Tab moves day -> month -> year; Shift+Tab moves backwards.
- Pasting or entering 8 digits such as 23102026 in a date segment normalizes to day/month/year if valid.
- Selecting a date in the calendar synchronizes the visible segments and stored date field.
- Python syntax compilation passed. Test the UI and review extracted names/dates before saving; OCR quality depends on source scan.
