#!/usr/bin/env python3
# Copyright 2026 Alessio Mattoccia
"""Explicit user-run setup. Installs only inside this ESAE directory."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
VERSION='2.22.0'
CPPCHECK_SHA='d74945deb2d50393430e07596b766f8a779512c7f60dac2a30ea64e059ece57b'

def validate_member(member):
    root_entry=member.isdir() and member.name==f'cppcheck-{VERSION}'
    if not (member.isfile() or member.isdir()) or not (root_entry or member.name.startswith(f'cppcheck-{VERSION}/')) or '..' in Path(member.name).parts:
        raise RuntimeError('Unexpected source archive member')

def main():
    if sys.version_info[:2]!=(3,12) or platform.system()!='Darwin' or platform.machine()!='arm64':
        raise SystemExit('Qualified setup requires Python 3.12 on macOS Apple Silicon. See README for other platforms/limits.')
    if shutil.disk_usage(ROOT).free<30_000_000_000:raise SystemExit('Less than 30 GB free; setup stopped before creating dependencies')
    if not Path('/usr/bin/clang++').exists() or subprocess.run(['/usr/bin/xcrun','--find','clang++'],capture_output=True).returncode:
        raise SystemExit('Apple Command Line Tools required. Install personally with xcode-select --install, then retry.')
    os.umask(0o077)
    env=dict(os.environ,PIP_CACHE_DIR=str(ROOT/'.toolchain/pip-cache'),PIP_DISABLE_PIP_VERSION_CHECK='1')
    if not (ROOT/'.venv/bin/python').exists():subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True)
    python=ROOT/'.venv/bin/python'
    subprocess.run([str(python),'-m','pip','install','--require-hashes','-r',str(ROOT/'requirements-macos-arm64-py312.lock')],env=env,check=True,timeout=600)
    archive=ROOT/'.toolchain/downloads'/f'cppcheck-{VERSION}.tar.gz';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        with urllib.request.urlopen(f'https://github.com/cppcheck-opensource/cppcheck/archive/refs/tags/{VERSION}.tar.gz',timeout=40) as r,archive.open('wb') as f:
            total=0
            while chunk:=r.read(131072):
                total+=len(chunk)
                if total>8_000_000:raise RuntimeError('Source archive exceeded size limit')
                f.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=CPPCHECK_SHA:raise SystemExit('Cppcheck archive hash mismatch; retained for inspection, not executed')
    source=ROOT/'.toolchain/src'/f'cppcheck-{VERSION}'
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive) as tar:
            for member in tar:
                validate_member(member)
            tar.extractall(source.parent,filter='data')
    if not (source/'cppcheck').exists():subprocess.run(['/usr/bin/make','-j2','CXX=/usr/bin/clang++'],cwd=source,env=env,check=True,timeout=900)
    subprocess.run([str(python),str(ROOT/'scripts/demo_database.py')],check=True)
    subprocess.run([str(python),'-m','esae.cli','doctor'],cwd=ROOT,check=True)
    print('\nSetup complete. Start: ./Avvia-ESAE.command\nNo service or login item was installed. No source uploaded.')

if __name__=='__main__':main()
