# -*- coding: utf-8 -*-
"""Verifies signed package manifest before application startup."""
import base64, hashlib, json
from pathlib import Path
PUBLIC_N_HEX = 'DB4ABD36CBBF4F3D5CFBC5E9F779F8DBD74B6FEDBC1E0C5233F3C39B56F2F48084DCE50F9C2930799614BAB27E3EFD231E4BED108C509EB8CACA87D195488DC7E096B12D8FC1DD88453FF90A5DAFAB08B3A4D86DEE633CB77E795CCCBE698B801F509D0D5A442976C0CA9CB5C00B5E0029784BE4B17A23327BB31530466214DB6B78CA73B01C5366F5EBBF303EC34266D29FA36E767D163271185A017FA7471AFEBE9CC6BC272FA1906E112589CB3DE46D0E8BFD5D13383B887499F6140C074047D6F601946B4C0D822B6348C97A25164052C2207C69F498151BACFB8A1526F66E936676E3B63770C67EA859F75EBA10738B98707F0730B01FD71AFA3BDBBB75'
PUBLIC_E = 65537

def _verify(message, signature):
    n=int(PUBLIC_N_HEX,16); sig=int.from_bytes(signature,'big')
    if sig>=n: return False
    em=pow(sig,PUBLIC_E,n).to_bytes((n.bit_length()+7)//8,'big')
    t=bytes.fromhex('3031300d060960864801650304020105000420')+hashlib.sha256(message).digest()
    expected=b'\x00\x01'+b'\xff'*(len(em)-len(t)-3)+b'\x00'+t
    return len(em)>=len(t)+11 and em==expected

def verify_integrity(app_dir):
    app_dir=Path(app_dir); mf=app_dir/'integrity_manifest.json'; sf=app_dir/'integrity_manifest.sig'
    if not mf.is_file() or not sf.is_file(): return False,'ملفات التحقق غير موجودة'
    try:
        raw=mf.read_bytes(); sig=base64.b64decode(sf.read_text(encoding='ascii').strip())
        if not _verify(raw,sig): return False,'توقيع قائمة الملفات غير صحيح'
        data=json.loads(raw.decode('utf-8'))
        for rel,expected in data.get('files',{}).items():
            p=(app_dir/rel).resolve()
            if app_dir.resolve() not in p.parents: return False,'مسار ملف غير آمن'
            if not p.is_file(): return False,'ملف مفقود: '+rel
            actual=hashlib.sha256(p.read_bytes()).hexdigest()
            if actual != expected: return False,'تم تعديل الملف: '+rel
        return True,'OK'
    except Exception as e: return False,'تعذر فحص سلامة الملفات: '+str(e)
