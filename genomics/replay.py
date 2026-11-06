# SPDX-License-Identifier: Apache-2.0
"""Replay the published normalized snapshot without network or private cache."""
import argparse,gzip,json
from pathlib import Path
from .analysis import analyze
from .export import public_check

def replay(input_path,report_path):
    with gzip.open(input_path,'rb') as stream:
        raw=stream.read(20_000_001)
    if len(raw)>20_000_000:raise ValueError('Normalized input size limit exceeded')
    payload=json.loads(raw);report=json.loads(Path(report_path).read_text());public_check(payload)
    if not isinstance(payload['variants'],list) or len(payload['variants'])>200:raise ValueError('Study variant limit exceeded')
    result=analyze(payload['variants'],payload['selection'],report['errors'])
    return {'passed':result['analysis_sha256']==report['analysis_sha256'],'analysis_sha256':result['analysis_sha256'],'expected':report['analysis_sha256'],'variants':len(payload['variants']),'network_used':False,'scope':'Numeric/scientific replay from public normalized metadata. Raw-source verification requires original complete source cache or independently acquired versioned VCVs.'}
def main():
    p=argparse.ArgumentParser(description='Reproduce published GEE-001 numeric results without network');p.add_argument('--input',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();result=replay(a.input,a.report);print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
