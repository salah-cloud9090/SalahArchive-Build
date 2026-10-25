# -*- coding: utf-8 -*-
"""Offline machine-bound activation. Public-key verification only; no network calls."""
import base64, hashlib, json, os, platform, socket, uuid
from pathlib import Path
PRODUCT = 'SALAH-ARCHIVE-FULL'
VERSION = '15.45'
PUBLIC_N_HEX = 'D7E7EDFE85D83856AA64EAF74A3279CB374A4221F2EF48EDB61403686C5E921EEA1BBD3A691C27D007124A7C2E31E50A189969AB9DCA8EA43629E93E68BF0808AD0DCE74CD633D24F40934E8F62B769A6FC5C9148ACD5C3BDDCB88F5E63B6627AD6C33EAD64501E35795467D0F9249C4F24BB2CE5B97D65154EECAD6DA095F73727DECD81D62271E14F65F43ED339DDB91265865B015E853606890F45B57F9A251B941150605A907E138DEBD363D57E5CC429EB2694E068E598391FF52AA4C8A6F1DEEE20A07AC84825D08694D5ABDC391CBED8D84F5D50E536D5B80726996AF1D88E54D81DC1630DD39D5776570449CAB64B3E62A6BFAAE7282D113294F70F3'
PUBLIC_E = 65537

def _b64u(data):
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')
def _unb64u(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
def machine_fingerprint():
    parts=[]
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography') as k:
                parts.append(str(winreg.QueryValueEx(k, 'MachineGuid')[0]).strip().lower())
        except Exception: pass
    if not parts:
        parts=[platform.node().strip().lower(), platform.system().lower(), str(uuid.getnode())]
    return hashlib.sha256(('|'.join(parts)+'|'+PRODUCT).encode('utf-8')).hexdigest()[:24].upper()

def request_code():
    return machine_fingerprint()

def _rsa_verify(message, signature):
    n=int(PUBLIC_N_HEX,16); s=int.from_bytes(signature,'big')
    if s >= n: return False
    em=pow(s,PUBLIC_E,n).to_bytes((n.bit_length()+7)//8,'big')
    digest=hashlib.sha256(message).digest()
    # PKCS#1 v1.5 DigestInfo for SHA-256
    t=bytes.fromhex('3031300d060960864801650304020105000420')+digest
    expected=b'\x00\x01'+b'\xff'*(len(em)-len(t)-3)+b'\x00'+t
    return len(em)>=len(t)+11 and em==expected

def verify_token(token, expected_machine=None):
    try:
        a,b=token.strip().split('.',1)
        payload=_unb64u(a); sig=_unb64u(b)
        if not _rsa_verify(payload,sig): return False, 'التوقيع غير صحيح'
        data=json.loads(payload.decode('utf-8'))
        if data.get('product') != PRODUCT: return False, 'الترخيص ليس لهذا البرنامج'
        if data.get('version') != VERSION: return False, 'الترخيص مخصص لإصدار مختلف'
        if data.get('machine') != (expected_machine or machine_fingerprint()): return False, 'الترخيص مخصص لجهاز آخر'
        return True, data
    except Exception:
        return False, 'رمز التفعيل غير صالح'

def license_path(app_dir):
    return Path(app_dir) / 'license.key'

def is_activated(app_dir):
    p=license_path(app_dir)
    if not p.is_file(): return False
    ok,_=verify_token(p.read_text(encoding='utf-8').strip())
    return ok

def activate(app_dir, token):
    ok, detail=verify_token(token)
    if not ok: return False, detail
    p=license_path(app_dir)
    p.write_text(token.strip()+'\n',encoding='utf-8')
    try: os.chmod(p,0o600)
    except Exception: pass
    return True, 'تم تفعيل النسخة الكاملة على هذا الجهاز'
