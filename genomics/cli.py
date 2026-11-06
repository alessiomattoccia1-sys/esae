# SPDX-License-Identifier: Apache-2.0
"""Explicit operator entry points. Serves only loopback; no startup service."""
import argparse,json,os
from pathlib import Path
from .service import GenomicsEngine

def main():
    parser=argparse.ArgumentParser(description='Research Engines / GEE 0.1 · public evidence, research only')
    parser.add_argument('operation',choices=['run','serve','verify'])
    parser.add_argument('--data',type=Path,default=Path('.local/genomics'))
    parser.add_argument('--per-gene',type=int,default=40)
    parser.add_argument('--ensembl-limit',type=int,default=12)
    parser.add_argument('--detail-limit',type=int,default=6)
    parser.add_argument('--job');parser.add_argument('--resume')
    parser.add_argument('--max-download-bytes',type=int,default=200_000_000)
    parser.add_argument('--port',type=int,default=4198)
    parser.add_argument('--ollama-url');parser.add_argument('--ollama-model')
    args=parser.parse_args();os.umask(0o077)
    if not 1024<=args.port<=65535 or not 1_000_000<=args.max_download_bytes<=2_000_000_000:parser.error('Port or download limit out of bounds')
    engine=GenomicsEngine(args.data,ollama_url=args.ollama_url,ollama_model=args.ollama_model,max_download_bytes=args.max_download_bytes)
    if args.operation=='serve':
        import uvicorn
        from .api import create_app
        print('Research Engines / GEE · http://127.0.0.1:'+str(args.port)+' · public sources only; Ctrl+C stops; archives persist')
        uvicorn.run(create_app(engine,args.port),host='127.0.0.1',port=args.port,access_log=False)
    elif args.operation=='verify':
        if not args.job:parser.error('--job required')
        value=engine.verify(args.job);print(json.dumps(value,indent=2))
        if not value['passed']:raise SystemExit(1)
    else:
        job=engine.run(per_gene=args.per_gene,ensembl_limit=args.ensembl_limit,detail_limit=args.detail_limit,resume=args.resume)
        print(json.dumps({k:job.get(k) for k in ('id','status','summary','errors','exclusions','duration_seconds')},indent=2))
        if job['status']!='completed':raise SystemExit(1)

if __name__=='__main__':main()
