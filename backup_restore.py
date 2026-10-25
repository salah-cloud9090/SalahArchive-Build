# -*- coding: utf-8 -*-
"""Safe timestamped backup and verified restore helper for the local archive."""
from pathlib import Path
from datetime import datetime
import argparse, shutil, sqlite3, zipfile, hashlib, os, tempfile
BASE=Path(__file__).resolve().parent
DB=BASE/'docuware_archive.db'
FILES=BASE/'local_archive_files'
BACKUPS=BASE/'backups'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def backup():
 BACKUPS.mkdir(exist_ok=True)
 stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
 target=BACKUPS/f'archive_backup_{stamp}.zip'
 # SQLite online backup API produces a consistent snapshot even if the app is running.
 with tempfile.TemporaryDirectory() as td:
  snapshot=Path(td)/'docuware_archive.db'
  if DB.exists():
   src=sqlite3.connect(str(DB)); dst=sqlite3.connect(str(snapshot))
   try: src.backup(dst)
   finally: dst.close(); src.close()
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   if snapshot.exists(): z.write(snapshot,'docuware_archive.db')
   if FILES.exists():
    for p in FILES.rglob('*'):
     if p.is_file(): z.write(p,Path('local_archive_files')/p.relative_to(FILES))
   # Include configuration and initial user help, never package transient outputs or secrets outside the app.
   for name in ('requirements.txt','README_AR.txt','admin_initial_password.txt'):
    p=BASE/name
    if p.is_file(): z.write(p,name)
 # verify archive integrity
 with zipfile.ZipFile(target) as z:
  bad=z.testzip()
  if bad: raise RuntimeError('فشل فحص النسخة الاحتياطية: '+bad)
 print('Backup created:',target)
 print('Size:',target.stat().st_size,'bytes')
 return target
def restore(archive):
 archive=Path(archive).resolve()
 if not archive.is_file(): raise FileNotFoundError(archive)
 with zipfile.ZipFile(archive) as z:
  bad=z.testzip()
  if bad: raise RuntimeError('النسخة الاحتياطية تالفة: '+bad)
  if 'docuware_archive.db' not in z.namelist(): raise RuntimeError('لا توجد قاعدة بيانات داخل النسخة.')
 # Never restore over the live database without a backup first.
 if DB.exists():
  BACKUPS.mkdir(exist_ok=True); shutil.copy2(DB,BACKUPS/f'pre_restore_{datetime.now():%Y%m%d_%H%M%S}.db')
 with zipfile.ZipFile(archive) as z:
  z.extract('docuware_archive.db',BASE)
  for name in z.namelist():
   if name.startswith('local_archive_files/') and not name.endswith('/'):
    dest=BASE/name; dest.parent.mkdir(parents=True,exist_ok=True)
    with z.open(name) as src, dest.open('wb') as dst: shutil.copyfileobj(src,dst)
 print('تمت الاستعادة. أعد تشغيل النظام وتحقق من السجلات.')
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('action',choices=['backup','restore']); p.add_argument('archive',nargs='?'); a=p.parse_args()
 if a.action=='backup': backup()
 elif not a.archive: p.error('حدد مسار ملف النسخة الاحتياطية')
 else: restore(a.archive)
