# -*- coding: utf-8 -*-
"""Offline-first diagnostic report; does not upload data or contact external sites."""
from pathlib import Path
import sys, os, importlib.util, sqlite3, socket, urllib.request, urllib.error, shutil, platform, datetime
BASE=Path(__file__).resolve().parent
lines=[]
def check(label, ok, detail=''):
 lines.append(('[OK] ' if ok else '[FAIL] ')+label+((': '+str(detail)) if detail else ''))
def main():
 lines.append('Administrative Archive Diagnostics')
 lines.append('Time: '+datetime.datetime.now().isoformat(timespec='seconds'))
 lines.append('OS: '+platform.platform()); lines.append('Python: '+sys.version.replace('\n',' '))
 for mod in ['requests','docx','openpyxl','pypdf','PIL','fitz','pytesseract','pdfplumber','win32com.client']:
  try: ok=importlib.util.find_spec(mod) is not None
  except Exception: ok=False
  check('Python module '+mod,ok)
 check('main.py exists',(BASE/'main.py').is_file())
 check('requirements.txt exists',(BASE/'requirements.txt').is_file())
 check('Database exists',(BASE/'docuware_archive.db').is_file(),(BASE/'docuware_archive.db').stat().st_size if (BASE/'docuware_archive.db').is_file() else 'not created yet')
 check('Document storage exists',(BASE/'local_archive_files').is_dir())
 check('Tesseract executable',bool(shutil.which('tesseract')),shutil.which('tesseract') or 'not found in PATH; OCR image/PDF may not work')
 check('Tesseract Arabic data', bool(shutil.which('tesseract')) and 'ara' in _langs(), 'available languages: '+(', '.join(_langs()) if _langs() else 'unavailable'))
 try:
  with socket.create_connection(('127.0.0.1',8765),timeout=1): running=True
 except OSError: running=False
 check('Local app port 8765',not running,'port appears free' if not running else 'port is already in use; check whether another copy is running')
 try:
  with urllib.request.urlopen('http://127.0.0.1:1234/v1/models',timeout=1) as r: lm=r.status==200
 except Exception: lm=False
 check('LM Studio local API',lm,'available on 127.0.0.1:1234' if lm else 'not responding; optional for AI, not required for manual indexing')
 report='\n'.join(lines)+'\n'
 (BASE/'diagnostics_report.txt').write_text(report,encoding='utf-8')
 print(report)
 print('Report saved:',BASE/'diagnostics_report.txt')
def _langs():
 exe=shutil.which('tesseract')
 if not exe:return []
 import subprocess
 try:
  r=subprocess.run([exe,'--list-langs'],capture_output=True,text=True,timeout=4,errors='replace')
  return [x.strip() for x in (r.stdout+'\n'+r.stderr).splitlines() if x.strip() and not x.lower().startswith('list of available')]
 except Exception:return []
if __name__=='__main__': main()
