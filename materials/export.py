# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Qualify public CC-BY normalized data and original reports; never raw archives."""
from pathlib import Path
import argparse,gzip,hashlib,json
from genomics.export import public_check
from .service import MaterialsEngine
from .analysis import analyze,ScreeningConfig
from .report import html_report,methodology,candidates_csv

def export(engine,job_id,output):
    job=engine.store.get(job_id)
    if not job or job['status']!='completed':raise ValueError('Only a completed materials study can be exported')
    verified=engine.verify(job_id)
    if not verified['passed']:raise ValueError('Raw source replay failed; publication refused')
    report=engine.report(job_id)
    if report['dataset'].get('license',{}).get('name')!='CC BY 4.0':raise ValueError('Publication requires verified source redistribution terms')
    rows=list(engine.store.iter_analysis(job_id));fresh,ranked=analyze(rows,ScreeningConfig(**report['configuration']),report['ingestion'])
    if fresh['analysis_sha256']!=report['analysis_sha256']:raise ValueError('Database/reported results mismatch')
    payload={'dataset':'MDE-001 normalized public NIST JARVIS-DFT snapshot','data_license':'CC BY 4.0','attribution':report['dataset']['attribution'],'source_doi':report['dataset']['doi'],'source_sha256':report['dataset']['source']['sha256'],'modifications':'Normalized whitelisted scalar properties, composition and crystal descriptors; full atom coordinates/raw arrays excluded','materials':rows}
    public_check(payload);public_check(report)
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode();compressed=gzip.compress(raw,mtime=0)
    manifest=json.loads((engine.root/'jobs'/job_id/'MDE-001_MANIFEST.json').read_text());manifest.update(offline_raw_verification=verified,normalized_input={'filename':'MDE-001_INPUT.json.gz','sha256':hashlib.sha256(compressed).hexdigest(),'bytes':len(compressed),'uncompressed_bytes':len(raw),'materials':len(rows)},publication_source_code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})
    report['verification']=verified
    summary={'status':'QUALIFIED','experiment':'MDE-001','engine_version':'0.1.0','completed_at':report['completed_at'],'analysis_sha256':report['analysis_sha256'],'dataset':report['dataset'],'configuration':report['configuration'],'metrics':report['metrics'],'candidate_examples':report['candidate_lists']['optical'][:6],'robust_across_all12_criteria':report['robust_across_all12_criteria'],'sensitivity':report['sensitivity'],'external_detail_checks':report['external_detail_checks'],'verification':verified,'original_code_license':'Apache-2.0','data_license':'CC BY4.0','ai_used_for_numeric_results':False}
    artifacts={'MDE-001_RESULTS.json':json.dumps(report,indent=2,allow_nan=False).encode()+b'\n','MDE-001_MANIFEST.json':json.dumps(manifest,indent=2,allow_nan=False).encode()+b'\n','MDE-001_REPORT.html':html_report(report).encode(),'MDE-001_CANDIDATES.csv':candidates_csv(ranked).encode(),'MDE-001_METHODOLOGY.md':methodology(report['configuration']).encode(),'MDE-001_INPUT.json.gz':compressed,'summary.json':json.dumps(summary,indent=2,allow_nan=False).encode()+b'\n','DATA_NOTICE.txt':b'NIST JARVIS-DFT / Kamal Choudhary et al. Dataset DOI 10.6084/m9.figshare.6815699.v11, CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. Modified through property normalization, selection, statistical analysis and screening. No NIST endorsement. Scientific data are NOT relicensed as Apache-2.0. Original MDE software: Apache-2.0. Full raw archive, models and atomic coordinates are not redistributed. See materials/DATA_SOURCES.md and SCIENTIFIC_METHODOLOGY.md.\n'}
    out=Path(output);out.mkdir(parents=True,exist_ok=True);hashes={}
    for name,b in artifacts.items():
        dest=out/name
        if dest.exists() and dest.read_bytes()!=b:
            old=dest.read_bytes();saved=engine.root/'export-history'/hashlib.sha256(old).hexdigest()/name;saved.parent.mkdir(parents=True,exist_ok=True)
            if not saved.exists():saved.write_bytes(old)
        dest.write_bytes(b);hashes[name]=hashlib.sha256(b).hexdigest()
    (out/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(hashes.items())))
    return {'passed':True,'materials':len(rows),'analysis_sha256':report['analysis_sha256'],'files':hashes,'normalized_bytes':len(raw),'compressed_bytes':len(compressed),'raw_cache_included':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--job',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(export(MaterialsEngine(a.data),a.job,a.output),indent=2))
if __name__=='__main__':main()
