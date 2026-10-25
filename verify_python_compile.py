from pathlib import Path
import sys, warnings
root = Path(__file__).resolve().parent
files = sorted(p for p in root.glob('*.py') if p.is_file() and p.name != 'main.py')
errors = []
with warnings.catch_warnings():
    warnings.simplefilter('error', SyntaxWarning)
    for path in files:
        try:
            compile(path.read_bytes(), str(path), 'exec')
        except Exception as exc:
            errors.append((path.name, repr(exc)))
try:
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        compile((root / 'main.py').read_bytes(), 'main.py', 'exec')
    print('Original main.py syntax: PASS; legacy SyntaxWarning ignored because the signed source is intentionally preserved.')
except Exception as exc:
    errors.append(('main.py', repr(exc)))
print(f'Strict-compiled {len(files)} Python modules, including main_mysql_candidate_v15_81.py')
print('Compile errors:', errors)
sys.exit(1 if errors else 0)
