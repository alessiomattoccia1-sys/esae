"""Explicit local reproduction of a pinned third-party benchmark, no build scripts.

Run with: .venv/bin/python -m benchmarks.reproduce_cppcheck --output .local/cppcheck-benchmark
Original code Apache-2.0. Downloaded Cppcheck source remains GPL-3.0-or-later.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import platform
import resource
import tarfile
import time
import urllib.request
from esae import __version__
from esae.cli import default_tools
from esae.scanner import read_regular, no_symlink
from esae.service import Engine


def digest(data):return hashlib.sha256(data).hexdigest()


def validate_checkpoint(saved, fingerprint, tools):
    if saved['profile_sha256']!=fingerprint or saved['tools']!=tools:
        raise ValueError('Profile, engine or toolchain changed: choose a new output directory')


def prepare_units(root, profile, archive):
    """Extract only exact hash-allowlisted sources into own read-only work units."""
    files={x['file']:x for x in profile['files']}
    raw={}
    with tarfile.open(archive) as tar:
        for member in tar:
            parts=Path(member.name).parts
            if Path(member.name).is_absolute() or '..' in parts:raise ValueError('Unsafe archive path')
            name=Path(*parts[1:]).as_posix() if len(parts)>1 else ''
            if name not in files:continue
            if not member.isfile() or member.size>2_000_000:raise ValueError('Unexpected source member')
            data=tar.extractfile(member).read(2_000_001)
            if digest(data)!=files[name]['sha256']:raise ValueError('Source hash mismatch: '+name)
            raw[name]=data
    if set(raw)!=set(files):raise ValueError('Incomplete source archive')
    headers=[name for name in raw if name.endswith(('.h','.hpp'))]
    jobs=[]
    for i,entry in enumerate(profile['units']):
        unit=root/'units'/f'{i:03d}';unit.mkdir(parents=True,exist_ok=True,mode=0o700)
        for name in [*headers,entry['file']]:
            p=unit/name;p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():
                if digest(read_regular(p,2_000_000))!=files[name]['sha256']:raise ValueError('Existing work source changed: '+name)
            else:p.write_bytes(raw[name]);p.chmod(0o400)
        db=unit/'compile_commands.json';content=json.dumps([entry],indent=2)+'\n'
        if db.exists() and db.read_text()!=content:raise ValueError('Existing compilation context changed')
        if not db.exists():db.write_text(content)
        jobs.append((i,entry['file'],unit))
    return jobs


def main():
    ap=argparse.ArgumentParser(description='Run a real serial Cppcheck CLI/core source benchmark locally')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--max-new-units',type=int,default=85,help='Stop at a checkpoint; rerun to resume')
    a=ap.parse_args()
    if platform.system()!='Darwin' or platform.machine()!='arm64':ap.error('Profile qualified only on macOS arm64')
    if not 1<=a.max_new_units<=85:ap.error('max-new-units must be 1..85')
    root=no_symlink(a.output).resolve();root.mkdir(parents=True,exist_ok=True,mode=0o700)
    project=Path(__file__).resolve().parents[1];profile_path=Path(__file__).with_name('cppcheck-2.22.0-macos-arm64.json')
    profile=json.loads(profile_path.read_text());os.umask(0o077)
    archive=root/'cppcheck-2.22.0.tar.gz'
    if not archive.exists():
        # This explicit CLI operation downloads public source, never user code.
        with urllib.request.urlopen(profile['source_archive_url'],timeout=40) as r,archive.open('xb') as out:
            total=0
            while chunk:=r.read(131072):
                total+=len(chunk)
                if total>8_000_000:raise ValueError('Archive size exceeded')
                out.write(chunk)
    if digest(archive.read_bytes())!=profile['source_archive_sha256']:raise ValueError('Archive checksum mismatch; no code executed')
    jobs=prepare_units(root,profile,archive);cpp,clang=default_tools(project)
    if not cpp or not clang:ap.error('Install the two native analyzers first; see README setup')
    engine=Engine(root/'engine',tuple(j[2] for j in jobs),Path(cpp).resolve(),Path(clang).resolve())
    if not all(t['available'] for t in engine.analyzers.status.values()):ap.error('Analyzer startup verification failed')
    source_hashes={p.name:digest(p.read_bytes()) for p in (project/'esae').glob('*.py')}
    fingerprint=digest(json.dumps({'profile':profile,'engine_sources':source_hashes,'version':__version__},sort_keys=True).encode())
    checkpoint=root/'checkpoint.json'
    if checkpoint.exists():
        saved=json.loads(checkpoint.read_text());validate_checkpoint(saved,fingerprint,engine.analyzers.status)
    else:saved={'creator':'ESAE owner-triggered benchmark','classification':'EVIDENCE','purpose':profile['name'],'deletion_condition':'Explicit owner retirement','profile_sha256':fingerprint,'tools':engine.analyzers.status,'engine_version':__version__,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':[]}
    completed={x['index'] for x in saved['runs'] if x['status']=='completed'};new=0
    for index,name,unit in jobs:
        if index in completed:continue
        if new>=a.max_new_units:break
        print(f'{index+1}/85 · {name}',flush=True);started=time.monotonic()
        report=engine.scan(str(unit),timeout=120)
        record={'index':index,'file':name,'scan_id':report['id'],'status':report['status'],'seconds':round(time.monotonic()-started,3),'errors':report['errors'],'executed':report['executed'],'source_integrity':report.get('source_integrity'),'summary':report['summary'],'memory':{'parent_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'child_peak_rss_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}}
        saved['runs']=[x for x in saved['runs'] if x['index']!=index]+[record]
        saved['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();tmp=root/'checkpoint.new.json';tmp.write_text(json.dumps(saved,indent=2)+'\n');tmp.replace(checkpoint);new+=1
        print(record['status'],record['seconds'],'seconds',flush=True)
        if report['status']!='completed':
            print('Coverage incomplete. Inspect errors before proceeding; checkpoint retained.',flush=True);break
    print('Completed:',sum(x['status']=='completed' for x in saved['runs']),'/ 85. No whole-program cross-unit verification or certified defect count.')

if __name__=='__main__':main()
