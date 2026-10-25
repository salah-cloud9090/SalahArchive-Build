# V11 — Smart Archive / macOS-like UI / automatic local AI

## Main changes
- Navigation label is now «أرشفة الكتب».
- After OCR/text extraction on the file-processing page, the app automatically attempts to analyze the extracted text with LM Studio. If the local model is not running, a clear error is shown and the extracted text remains available.
- Scan-basket files can be previewed as rendered PNG page images using PyMuPDF instead of relying only on the browser's PDF iframe, which may display a blank area on some setups.
- Scan page now shows resizable basket panels side-by-side; each panel lists its own files and provides quick actions for preview/archive and AI reading.
- UI styles are closer to macOS/iOS: neutral background, dark translucent navigation, rounded cards, blue actions.
- Existing SQLite database and archived originals remain in place; do not overwrite them during installation.

## Install/test safely
1. Stop the app.
2. Backup `docuware_archive.db` and `local_archive_files`.
3. Extract this package into a NEW folder.
4. Run `install_dependencies.bat`, then `run_local_archive.bat`.
5. Open «أرشفة الكتب» and test with a small PDF.
6. For automatic AI analysis, LM Studio must have a loaded Arabic-capable model and Local Server enabled at `127.0.0.1:1234`.

## Notes and limitations
- The automatic AI step analyzes OCR-extracted text; it does not send page images directly to a vision model. That is intentional for faster, lower-compute processing and because vision-capable model availability differs by LM Studio model. If OCR is poor, the AI may also be wrong.
- Rendering PDF previews requires PyMuPDF. It is listed in `requirements.txt`.
- Basket panel resizing is browser-based and temporary; panel layout is not persisted between restarts.
- OCR/AI quality and Canon WIA scan need testing on the user's actual machine and sample books. Python syntax checks are not a substitute for that runtime test.
