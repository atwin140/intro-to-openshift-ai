#!/usr/bin/env python3
"""Inspect Git candidates without printing potentially sensitive matches."""
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
names = sorted(set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'], cwd=ROOT).decode().split('\0')) - {''})
patterns = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'JWT-like credential': re.compile(r'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'AWS key': re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    'embedded kubeconfig credential': re.compile(r'^\s*(?:client-key-data|client-certificate-data|token):\s*[A-Za-z0-9/+_.=-]{30,}', re.M),
    'workstation path': re.compile(r'/(?:Users|home)/[A-Za-z0-9._-]+/'),
}
issues=[]
for name in names:
    path=ROOT/name
    if not path.is_file(): continue
    if path.is_symlink(): issues.append((name,'symlink requires review'));continue
    if any(p in {'inventory','notes','sources','.DS_Store','__pycache__','.env','secrets'} for p in path.relative_to(ROOT).parts):
        issues.append((name,'private/generated path'))
    if path.stat().st_size > 2_000_000: issues.append((name,'large file requires review'))
    try: data=path.read_text()
    except UnicodeDecodeError:
        issues.append((name,'binary file requires review'));continue
    for label, pattern in patterns.items():
        if pattern.search(data): issues.append((name,label))
for name,label in issues: print(f'REVIEW: {name}: {label}')
print(f'Checked {len(names)} Git candidates; {len(issues)} flagged. Pattern scan is not a guarantee that every secret is detected.')
sys.exit(bool(issues))
