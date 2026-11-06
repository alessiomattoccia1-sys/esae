#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit source setup for GEE only, no native analyzer/model installation."""
from pathlib import Path
import os,platform,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
def main():
    if sys.version_info[:2]!=(3,12) or platform.system()!='Darwin' or platform.machine()!='arm64':raise SystemExit('Qualified setup: Python 3.12, macOS Apple Silicon. Other platforms unqualified.')
    if shutil.disk_usage(ROOT).free<5_000_000_000:raise SystemExit('Less than 5 GB free; setup stopped')
    os.umask(0o077)
    if not (ROOT/'.venv/bin/python').exists():subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True)
    env=dict(os.environ,PIP_CACHE_DIR=str(ROOT/'.local/setup-cache'),PIP_DISABLE_PIP_VERSION_CHECK='1')
    subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pip','install','--require-hashes','-r',str(ROOT/'requirements-genomics-macos-arm64-py312.lock')],env=env,check=True,timeout=300)
    subprocess.run([str(ROOT/'.venv/bin/python'),'-c','from genomics.service import GenomicsEngine; from genomics.api import create_app; print("GEE imports OK; no data acquired")'],cwd=ROOT,check=True)
    print('Setup complete. Start: .venv/bin/python -m genomics.cli serve\nOpen http://127.0.0.1:4198/ · No service installed, no models downloaded.')
if __name__=='__main__':main()
