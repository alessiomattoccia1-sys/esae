#!/usr/bin/env python3
# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Qualified MDE environment, separate from existing ESAE/GEE runtimes."""
from pathlib import Path
import os,platform,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    if sys.version_info[:2]!=(3,12) or platform.system()!='Darwin' or platform.machine()!='arm64':raise SystemExit('Qualified setup: Python3.12, macOS Apple Silicon. Other platforms unqualified.')
    if shutil.disk_usage(ROOT).free<5_000_000_000:raise SystemExit('At least5GB free required')
    os.umask(0o077);python=ROOT/'.venv-mde/bin/python'
    if not python.exists():subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv-mde')],check=True)
    subprocess.run([str(python),'-m','pip','install','--require-hashes','-r',str(ROOT/'requirements-materials-macos-arm64-py312.lock')],env=dict(os.environ,PIP_CACHE_DIR=str(ROOT/'.local/setup-cache'),PIP_DISABLE_PIP_VERSION_CHECK='1'),check=True,timeout=600)
    subprocess.run([str(python),'-c','from materials.service import MaterialsEngine; from materials.api import create_app; print("MDE imports OK; no dataset or model acquired")'],cwd=ROOT,check=True)
    print('Start: .venv-mde/bin/python -m materials.cli serve\nOpen http://127.0.0.1:4202/ · No service installed; no model downloaded.')
if __name__=='__main__':main()
