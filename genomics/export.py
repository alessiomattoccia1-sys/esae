# SPDX-License-Identifier: Apache-2.0
"""Qualified static public artifacts; never copies raw cache or local paths."""
from pathlib import Path
import argparse,json,gzip,hashlib,re
from .service import GenomicsEngine
from .report import html_report

FORBIDDEN_KEYS={'Sample','ObservedIn','ObservedData','clinical_comment','patient_id','email','password','token'}
def public_check(value):
    if isinstance(value,dict):
        if set(value)&FORBIDDEN_KEYS:raise ValueError('Nonpublic/sample field in export')
        for item in value.values():public_check(item)
    elif isinstance(value,list):
        for item in value:public_check(item)
    elif isinstance(value,str) and re.search(r'/Users/|/Volumes/|192\.168\.|-----BEGIN .*PRIVATE KEY',value):raise ValueError('Local/private marker in export')
def export(engine,job_id,output):
    job=engine.store.get(job_id)
    if not job or job['status']!='completed':raise ValueError('Only a genuinely completed study may be published')
    verification=engine.verify(job_id)
    if not verification['passed']:raise ValueError('Scientific replay failed; no publication')
    report=engine.report(job_id);variants=engine.store.variants(job_id,limit=500);public_check(report);public_check(variants)
    m=report['metrics']
    assert m['variants']==len(variants)==len({v['variation_id'] for v in variants})
    assert sum(m['classification_distribution'].values())==len(variants)
    assert sum(m['review_status_distribution'].values())==len(variants)
    assert sum(m['submitter_categories_unique_organizations'].values())==m['unique_submitters']
    manifest=json.loads((engine.root/'jobs'/job_id/'manifest.json').read_text())
    manifest['offline_verification']=verification
    manifest['final_verification_source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    manifest['published_input']='gee-001-input.json.gz: normalized public variant/organization metadata; no raw Sample/ObservedData or clinical narratives'
    report['verification']=verification
    payload={'dataset':'GEE-001 normalized public evidence snapshot','sources':'NCBI ClinVar and Ensembl; see DATA_SOURCES.md, not relicensed as Apache-2.0 data','selection':report['selection'],'variants':variants}
    raw=(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();compressed=gzip.compress(raw,mtime=0)
    summary={'status':'QUALIFIED','experiment':'GEE-001','job_id':job_id,'completed_at':report['completed_at'],'analysis_sha256':report['analysis_sha256'],'metrics':m,'selection':report['selection'],'examples':report['examples'],'ensembl_summary':report['ensembl_summary'],'exclusions':report['exclusions'],'sources_count':len(report['sources']),'verification':verification,'license':'Apache-2.0 original software only','data_attribution':['NCBI ClinVar','Ensembl / EMBL-EBI'],'ai_used_for_numeric_results':False}
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    artifacts={'report.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),'report.html':html_report(report).encode(),'manifest.json':(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode(),'summary.json':(json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode(),'gee-001-input.json.gz':compressed,'DATA_NOTICE.txt':b'GEE-001 normalized public variant evidence. Sources: NCBI ClinVar / Ensembl EMBL-EBI. Original software Apache-2.0; data retain upstream terms. Attribution and methods: DATA_SOURCES.md, METHODOLOGY.md, THIRD_PARTY_NOTICES.md. No patient observations, full clinical narratives, restricted colocated annotations or scientific articles included. Research only, no diagnostic use.\n'}
    hashes={}
    for name,content in artifacts.items():
        dest=out/name
        if dest.exists() and dest.read_bytes()!=content:
            old=dest.read_bytes();history=Path(__file__).resolve().parents[1]/'.local/export-history'/hashlib.sha256(old).hexdigest();history.mkdir(parents=True,exist_ok=True)
            if not (history/name).exists():(history/name).write_bytes(old)
        dest.write_bytes(content);hashes[name]=hashlib.sha256(content).hexdigest()
    (out/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(hashes.items())))
    return {'passed':True,'analysis_sha256':report['analysis_sha256'],'files':hashes,'normalized_input_uncompressed_bytes':len(raw),'normalized_input_compressed_bytes':len(compressed),'raw_sources_copied':False}

def main():
    p=argparse.ArgumentParser(description='Export only verified public GEE evidence to static JSON/HTML')
    p.add_argument('--data',type=Path,required=True);p.add_argument('--job',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(export(GenomicsEngine(a.data),a.job,a.output),indent=2))
if __name__=='__main__':main()
