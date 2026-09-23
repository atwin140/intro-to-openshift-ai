#!/usr/bin/env python3
"""Offline structural review (oc kustomize only; no apply, exec, or deletion)."""
import ast
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
failures=[]
roots=sorted({p.parent for folder in ['platform','deploy','chatbot','checks','image-generation'] for p in (ROOT/folder).rglob('kustomization.yaml')})
for path in roots:
    result=subprocess.run(['oc','kustomize',str(path)],capture_output=True,text=True)
    if result.returncode:failures.append(f'{path.relative_to(ROOT)}: {result.stderr.strip()}')
for folder in ['checks','chatbot','deploy','image-generation','scripts']:
    for path in (ROOT/folder).rglob('*.py'):
        try:ast.parse(path.read_text(),filename=str(path))
        except SyntaxError as e:failures.append(str(e))
for path in (ROOT/'checks').glob('*.sh'):
    result=subprocess.run(['bash','-n',str(path)],capture_output=True,text=True)
    if result.returncode:failures.append(result.stderr.strip())
candidates=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
markdown=[ROOT/name for name in sorted(set(candidates)) if name.endswith('.md')]
for path in markdown:
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
        target=target.strip('<>').split('#')[0]
        if not target or '://' in target or target.startswith('mailto:'):continue
        if (not (path.parent/target).exists() or any(part in {'notes','inventory'} for part in Path(target).parts)):failures.append(f'Broken local link in {path.relative_to(ROOT)}: {target}')
print(f'Rendered {len(roots)} Kustomize roots; checked Python/shell syntax and local guide links.')
if failures:
    print('\n'.join(failures));sys.exit(1)
print('PASS: structural checks. This does not prove cluster readiness, inference quality, or fresh-install reproducibility.')
