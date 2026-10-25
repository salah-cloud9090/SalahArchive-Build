# -*- coding: utf-8 -*-
"""One-click local test runner. Never opens the production database."""
from __future__ import annotations
import datetime, json, os, pathlib, subprocess, sys, traceback
ROOT = pathlib.Path(__file__).resolve().parent
REPORT_JSON = ROOT / 'FULL_TEST_REPORT.json'
REPORT_TXT = ROOT / 'FULL_TEST_REPORT.txt'
results=[]
def run_step(name, args, timeout=900, live=False):
    print('\n' + '='*72 + '\n' + name + '\n' + '='*72, flush=True)
    try:
        if live:
            p=subprocess.run(args, cwd=ROOT, timeout=timeout)
            output='Live test was run interactively; see MYSQL_LIVE_INTEGRATION_RESULT_LOCAL.json if created.'
        else:
            p=subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            output=(p.stdout or '') + ('\n[STDERR]\n' + p.stderr if p.stderr else '')
            if output: print(output, flush=True)
        status='PASS' if p.returncode==0 else 'FAIL'
        results.append({'name':name,'status':status,'return_code':p.returncode,'output':output[-20000:]})
        return p.returncode==0
    except Exception as e:
        results.append({'name':name,'status':'ERROR','error':repr(e),'traceback':traceback.format_exc()})
        print('ERROR:',e,flush=True)
        return False

def main():
    start=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    print('Salah Archive v15.81 - One Click Diagnostic\nThis runner is restricted to disposable/local checks and the test DB salah_archive_test.\nIt will not run migrations or modify a production database.',flush=True)
    run_step('1. Strict Python syntax compile (candidate + modules; preserved original checked separately)', [sys.executable,'verify_python_compile.py'])
    run_step('2. Unit test suite', [sys.executable,'-m','unittest','discover','-v'], timeout=1800)
    run_step('3. Isolated SQLite smoke test', [sys.executable,'smoke_test_sqlite_isolated.py'], timeout=900)
    integrity_script = "from pathlib import Path; from integrity_guard import verify_integrity; ok,detail=verify_integrity(Path.cwd()); print('Integrity:',ok,detail); raise SystemExit(0 if ok else 1)"
    run_step('4. Package integrity guard', [sys.executable,'-c',integrity_script])
    # Optional real MySQL test: explicit opt-in, always guarded to test database.
    answer=input('\nRun the LIVE MySQL test against the isolated database salah_archive_test now? [y/N]: ').strip().lower()
    if answer in ('y','yes'):
        # Existing runner validates profile and asks for the password without echoing it.
        ok=run_step('5. Live MySQL integration (TEST DB ONLY)', [sys.executable,'run_mysql_integration.py','--profile','local'], timeout=1800, live=True)
        live_report=ROOT/'MYSQL_LIVE_INTEGRATION_RESULT_LOCAL.json'
        if live_report.exists():
            try:
                data=json.loads(live_report.read_text(encoding='utf-8'))
                results.append({'name':'Live MySQL report summary','status':data.get('status','UNKNOWN'),'report_file':live_report.name,'database':data.get('database'),'detail':data.get('detail'),'passed_checks':data.get('passed_checks',[]),'cleanup_errors':data.get('cleanup_errors',[])})
            except Exception as e: results.append({'name':'Live MySQL report summary','status':'ERROR','error':repr(e)})
        elif ok:
            results.append({'name':'Live MySQL report summary','status':'UNKNOWN','detail':'Runner returned success but no JSON result file was found.'})
    else:
        results.append({'name':'Live MySQL integration','status':'NOT RUN','detail':'Skipped by user. No live database claims made.'})
    finished=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    fails=[r for r in results if r['status'] not in ('PASS',)]
    report={'package_version':'15.81','started_local':start,'finished_local':finished,'database_safety':'Live integration runner is restricted to salah_archive_test; static checks use disposable SQLite/temp files. Production database was not intentionally opened.','overall_status':'PASS' if not fails else ('PASS_WITH_LIVE_TEST_SKIPPED' if all(r['status']=='PASS' or r['status']=='NOT RUN' for r in results) else 'NEEDS_ATTENTION'),'results':results,'password_saved':False}
    REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['SALAH ARCHIVE v15.81 - FULL TEST REPORT','Started: '+start,'Finished: '+finished,'Overall: '+report['overall_status'],'','Note: no password is written to this report.']
    for r in results:
        lines += ['',f"[{r['status']}] {r['name']}"]
        if r.get('detail'): lines.append('  '+str(r['detail']))
        if r.get('error'): lines.append('  '+str(r['error']))
        if r.get('return_code') is not None: lines.append('  exit code: '+str(r['return_code']))
        if r.get('passed_checks'): lines.append('  passed checks: '+', '.join(r['passed_checks']))
        if r.get('cleanup_errors'): lines.append('  cleanup errors: '+repr(r['cleanup_errors']))
    REPORT_TXT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'+'='*72+'\nFINISHED: '+report['overall_status']+'\nReports: '+REPORT_TXT.name+' and '+REPORT_JSON.name,flush=True)
    return 0 if report['overall_status'] in ('PASS','PASS_WITH_LIVE_TEST_SKIPPED') else 1
if __name__=='__main__': raise SystemExit(main())
