# SPDX-License-Identifier: Apache-2.0
import argparse,json,os
from pathlib import Path
from .analysis import ScreeningConfig
from .service import MaterialsEngine

def main():
    p=argparse.ArgumentParser(description='MDE0.1 — local public-data photovoltaic screening, not a DFT simulator');p.add_argument('operation',choices=['run','verify','serve']);p.add_argument('--data',type=Path,default=Path('.local/materials'));p.add_argument('--job');p.add_argument('--resume');p.add_argument('--gap-min',type=float,default=.8);p.add_argument('--gap-max',type=float,default=2.2);p.add_argument('--target-gap',type=float,default=1.5);p.add_argument('--hull-max',type=float,default=.1);p.add_argument('--slme-min',type=float,default=10);p.add_argument('--port',type=int,default=4202);p.add_argument('--ollama-url');p.add_argument('--ollama-model');p.add_argument('--exclude-element',action='append',default=[]);p.add_argument('--require-dielectric',action='store_true');a=p.parse_args();os.umask(0o077)
    if not 1024<=a.port<=65535:p.error('Invalid local port')
    engine=MaterialsEngine(a.data,ollama_url=a.ollama_url,ollama_model=a.ollama_model)
    if a.operation=='serve':
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(engine,a.port),host='127.0.0.1',port=a.port,access_log=False)
    elif a.operation=='verify':
        if not a.job:p.error('--job required')
        r=engine.verify(a.job);print(json.dumps(r,indent=2))
        if not r['passed']:raise SystemExit(1)
    else:
        j=engine.run(ScreeningConfig(a.gap_min,a.gap_max,a.target_gap,a.hull_max,a.slme_min,tuple(a.exclude_element),a.require_dielectric),resume=a.resume);print(json.dumps(j,indent=2))
        if j['status']!='completed':raise SystemExit(1)
if __name__=='__main__':main()
