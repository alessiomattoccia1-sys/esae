#!/usr/bin/env python3
# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Deterministic family source release; no local archive, secrets or binaries."""
from pathlib import Path
import hashlib,json,re,zipfile,shutil,io,sys
from package import members,ROOT
sys.path.insert(0,str(ROOT))

EXTRA=['ARCHITECTURE.md','ARCHITECTURE_REUSE.md','GENOMICS_README.md','GENOMICS_VALIDATION.md','DATA_SOURCES.md','METHODOLOGY.md','THIRD_PARTY_NOTICES.md','requirements-genomics-macos-arm64-py312.lock','scripts/setup_genomics.py','scripts/package_research.py']
def main():
    names=set(members()+EXTRA)
    for folder in ['research_core','genomics']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_symlink():raise ValueError('Symlink in original source')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':names.add(p.relative_to(ROOT).as_posix())
    names=sorted(names);data={};hashes={}
    for name in names:
        p=ROOT/name
        if p.is_symlink() or not p.is_file():raise ValueError('Invalid source member '+name)
        b=p.read_bytes()
        if re.search(rb'/(?:Users|Volumes)/[A-Za-z0-9_-]+',b) or re.search(rb'[\w.+-]+@(?:gmail|icloud|yahoo)\.com',b) or b'-----BEGIN '+b'PRIVATE KEY-----' in b:raise ValueError('Private marker '+name)
        if name.endswith('.gz'):
            import gzip
            from genomics.export import public_check
            public_check(json.loads(gzip.decompress(b)))
        data[name]=b;hashes[name]=hashlib.sha256(b).hexdigest()
    from genomics.replay import replay
    verified=replay(ROOT/'reports/genomics/gee-001-input.json.gz',ROOT/'reports/genomics/report.json')
    if not verified['passed']:raise ValueError('Public experiment replay failed')
    manifest={'name':'Research Engines','version':'0.1.0','components':{'ESAE':'0.1.1 unchanged runtime','GEE':'0.1.0','Shared Research Core':'0.1.0'},'original_software_license':'Apache-2.0','third_party_data_license':'Upstream terms; see DATA_SOURCES.md and reports/genomics/DATA_NOTICE.txt','creator':'Codex per Alessio / Mattoccia Labs','classification':'PROJECT','purpose':'Original family source, owned demo and qualified public normalized GEE evidence','deletion_condition':'Explicit retirement','files':hashes,'models_included':False,'analyzer_binaries_included':False,'raw_source_cache_included':False,'private_scans_included':False,'analysis_sha256':verified['analysis_sha256']}
    data['DISTRIBUTION.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    def build():
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,b in sorted(data.items()):
                info=zipfile.ZipInfo('Research-Engines-0.1.0/'+name,date_time=(2026,11,6,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100755 if name=='Avvia-ESAE.command' else 0o100644)<<16;z.writestr(info,b)
        return out.getvalue()
    b=build();assert b==build(),'Nondeterministic archive';digest=hashlib.sha256(b).hexdigest();out=ROOT/'dist/research-engines-0.1.0';out.mkdir(parents=True,exist_ok=True);dest=out/'Research-Engines-0.1.0-source.zip'
    if dest.exists() and dest.read_bytes()!=b:
        prior=dest.read_bytes();saved=out/'history'/hashlib.sha256(prior).hexdigest()/dest.name;saved.parent.mkdir(parents=True,exist_ok=True)
        if not saved.exists():saved.write_bytes(prior)
    dest.write_bytes(b);(out/'SHA256SUMS').write_text(digest+'  '+dest.name+'\n');(out/'DISTRIBUTION.json').write_bytes(data['DISTRIBUTION.json'])
    result={'creator':'Codex per Alessio','classification':'EVIDENCE','purpose':'Original source release qualification','deletion_condition':'Explicit retirement','file':dest.name,'sha256':digest,'bytes':len(b),'members':len(data),'reproduced_identically':True,'normalized_replay':verified}
    (out/'PACKAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
