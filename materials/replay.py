# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Network-free deterministic replay of the qualified public normalized snapshot."""
import argparse,gzip,json
from pathlib import Path
from genomics.export import public_check
from .analysis import analyze,ScreeningConfig

def replay(input_path,report_path):
    with gzip.open(input_path,'rb') as stream:raw=stream.read(250_000_001)
    if len(raw)>250_000_000:raise ValueError('Normalized input size limit exceeded')
    payload=json.loads(raw);report=json.loads(Path(report_path).read_text());public_check(payload)
    rows=payload['materials']
    if not isinstance(rows,list) or len(rows)>150_000:raise ValueError('Material count limit exceeded')
    if payload['source_sha256']!=report['dataset']['source']['sha256']:raise ValueError('Input/report source mismatch')
    fresh,_=analyze(rows,ScreeningConfig(**report['configuration']),report['ingestion']);passed=fresh['analysis_sha256']==report['analysis_sha256']
    return {'passed':passed,'materials':len(rows),'analysis_sha256':fresh['analysis_sha256'],'expected':report['analysis_sha256'],'network_used':False,'scope':'Numeric replay from normalized public descriptors. Raw parsing, atom-coordinate validation and source acquisition require the original frozen archive/cache and materials.cli verify.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=replay(a.input,a.report);print(json.dumps(r,indent=2))
    if not r['passed']:raise SystemExit(1)
if __name__=='__main__':main()
