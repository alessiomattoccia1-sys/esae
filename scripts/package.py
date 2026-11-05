"""Deterministic original-source distribution; explicit allowlist only."""
from pathlib import Path
import hashlib
import json
import zipfile
import shutil
import re

ROOT=Path(__file__).resolve().parents[1]
FILES=['.gitignore','README.md','LICENSE','NOTICE','THIRD_PARTY.md','SECURITY.md','LIMITATIONS.md','STORAGE.json','pyproject.toml','requirements.lock','requirements-macos-arm64-py312.lock','Avvia-ESAE.command']
DIRS=['esae','tests','demo','reports','benchmarks']
SCRIPTS=['scripts/setup.py','scripts/demo_database.py','scripts/package.py']

def members():
    names=set(FILES+SCRIPTS)
    for folder in DIRS:
        for p in (ROOT/folder).rglob('*'):
            rel=p.relative_to(ROOT)
            if p.is_symlink():raise ValueError('Symlink in package source')
            if p.is_file() and not any(x in rel.parts for x in ('__pycache__','.pytest_cache','build')):
                if p.suffix not in ('.pyc','.o'):names.add(rel.as_posix())
    return sorted(names)

def main():
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    files=members();hashes={}
    for name in files:
        p=ROOT/name
        if not p.is_file():raise ValueError('Missing required file '+name)
        data=p.read_bytes()
        if re.search(rb'/(?:Users|Volumes)/[A-Za-z0-9_-]+',data) or re.search(rb'[\w.+-]+@(?:gmail|icloud|yahoo)\.com',data) or (b'-----BEGIN '+b'PRIVATE KEY-----') in data:raise ValueError('Private path/secret marker '+name)
        hashes[name]=hashlib.sha256(data).hexdigest()
    manifest={'name':'Embedded Software Analysis Engine','version':'0.1.1','license':'Apache-2.0','creator':'Codex per Alessio / Mattoccia Labs','classification':'PROJECT','purpose':'Reproducible original source and owned demo distribution','deletion_condition':'Explicit retirement','files':hashes,'third_party_binaries_included':False,'models_included':False,'private_scans_included':False}
    manifest_bytes=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    def build(dest):
        with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name in files+['DISTRIBUTION.json']:
                info=zipfile.ZipInfo('ESAE-0.1.1/'+name,date_time=(2026,11,5,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=(0o100755 if name=='Avvia-ESAE.command' else 0o100644)<<16
                z.writestr(info,manifest_bytes if name=='DISTRIBUTION.json' else (ROOT/name).read_bytes())
    archive=out/'ESAE-0.1.1-source.zip';repeat=out/'ESAE-0.1.1-repro-check.zip'
    for previous in [archive,repeat]:
        if previous.exists():
            oldhash=hashlib.sha256(previous.read_bytes()).hexdigest();saved=out/'archive-history'/oldhash/previous.name
            saved.parent.mkdir(parents=True,exist_ok=True)
            if not saved.exists():shutil.copyfile(previous,saved)
    build(archive);build(repeat)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest();assert digest==hashlib.sha256(repeat.read_bytes()).hexdigest()
    # Both archives are PROJECT, preserved; not automatically deleted as temp.
    (out/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
    (out/'DISTRIBUTION.json').write_bytes(manifest_bytes)
    (ROOT/'evidence/PACKAGE.json').write_text(json.dumps({'creator':'Codex per Alessio','classification':'EVIDENCE','purpose':'Deterministic source package verification','deletion_condition':'Explicit retirement','file':archive.name,'bytes':archive.stat().st_size,'sha256':digest,'reproduced_identically':True,'members':len(files)+1},indent=2)+'\n')
    print(json.dumps({'file':archive.name,'bytes':archive.stat().st_size,'sha256':digest,'files':len(files)}))

if __name__=='__main__':main()
