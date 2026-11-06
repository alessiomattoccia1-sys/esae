#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit original family source + qualified CC-BY descriptors; no raw cache."""
from pathlib import Path
import hashlib,io,json,re,sys,zipfile
from package import ROOT,members
sys.path.insert(0,str(ROOT))
from package_research import EXTRA
from genomics.export import public_check
from genomics.replay import replay as gee_replay
from materials.replay import replay as mde_replay

def main():
    names=set(members()+EXTRA+['scripts/setup_materials.py','scripts/package_materials.py','requirements-materials-macos-arm64-py312.lock'])
    for folder in ['research_core','genomics','materials']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_symlink():raise ValueError('Symlink in source')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':names.add(p.relative_to(ROOT).as_posix())
    data={};hashes={}
    for name in sorted(names):
        p=ROOT/name
        if p.is_symlink() or not p.is_file():raise ValueError('Invalid member '+name)
        b=p.read_bytes()
        if re.search(rb'/(?:Users|Volumes)/[A-Za-z0-9_-]+',b) or re.search(rb'[\w.+-]+@(?:gmail|icloud|yahoo)\.com',b) or b'-----BEGIN '+b'PRIVATE KEY-----' in b:raise ValueError('Private marker '+name)
        if name.endswith('.gz'):
            import gzip
            public_check(json.loads(gzip.decompress(b)))
        data[name]=b;hashes[name]=hashlib.sha256(b).hexdigest()
    gee=gee_replay(ROOT/'reports/genomics/gee-001-input.json.gz',ROOT/'reports/genomics/report.json');mde=mde_replay(ROOT/'reports/materials/MDE-001_INPUT.json.gz',ROOT/'reports/materials/MDE-001_RESULTS.json')
    if not gee['passed'] or not mde['passed']:raise ValueError('Scientific public replay failed')
    manifest={'name':'Research Engines','version':'0.2.0','components':{'ESAE':'0.1.1 runtime preserved','GEE':'0.1.0 runtime preserved','MDE':'0.1.0','Shared Research Core':'0.2.0 minimal compatible additions'},'original_software_license':'Apache-2.0','data_licenses':'NIST JARVIS CC BY4.0; ClinVar/Ensembl upstream terms; see per-study DATA_NOTICE and source docs','creator':'Codex per Alessio / Mattoccia Labs','classification':'PROJECT','purpose':'Original family source, owned demo and qualified normalized public scientific evidence','deletion_condition':'Explicit retirement','files':hashes,'raw_cache_included':False,'models_included':False,'third_party_binaries_included':False,'private_scans_included':False,'gee_analysis_sha256':gee['analysis_sha256'],'mde_analysis_sha256':mde['analysis_sha256']}
    data['DISTRIBUTION.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    def build():
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,b in sorted(data.items()):
                info=zipfile.ZipInfo('Research-Engines-0.2.0/'+name,date_time=(2026,11,6,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100755 if name=='Avvia-ESAE.command' else 0o100644)<<16;z.writestr(info,b)
        return out.getvalue()
    b=build();assert b==build();digest=hashlib.sha256(b).hexdigest();out=ROOT/'dist/research-engines-0.2.0';out.mkdir(parents=True,exist_ok=True);dest=out/'Research-Engines-0.2.0-source.zip'
    if dest.exists() and dest.read_bytes()!=b:
        prior=dest.read_bytes();saved=out/'history'/hashlib.sha256(prior).hexdigest()/dest.name;saved.parent.mkdir(parents=True,exist_ok=True)
        if not saved.exists():saved.write_bytes(prior)
    dest.write_bytes(b);(out/'SHA256SUMS').write_text(digest+'  '+dest.name+'\n');(out/'DISTRIBUTION.json').write_bytes(data['DISTRIBUTION.json']);result={'passed':True,'file':dest.name,'sha256':digest,'bytes':len(b),'members':len(data),'identical_repeat':True,'gee_replay':gee,'mde_replay':mde};(out/'PACKAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
