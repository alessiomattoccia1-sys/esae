import argparse
from pathlib import Path
import json
import os
import shutil
import sys
from .service import Engine
from .report import html_report

def default_tools(root):
    cpp=root/'.toolchain/src/cppcheck-2.22.0/cppcheck'
    clang=root/'.venv/lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages/clang_tidy/data/bin/clang-tidy'
    return (cpp if cpp.exists() else shutil.which('cppcheck'),clang if clang.exists() else shutil.which('clang-tidy'))

def main():
    root=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description='ESAE v0.1 · local experimental C/C++ analysis')
    parser.add_argument('operation',choices=['serve','scan','doctor'])
    parser.add_argument('repository',nargs='?',default=str(root/'demo'))
    parser.add_argument('--allow-root',action='append',type=Path,default=[])
    parser.add_argument('--data',type=Path,default=root/'.local')
    parser.add_argument('--cppcheck',type=Path);parser.add_argument('--clang-tidy',type=Path)
    parser.add_argument('--ollama-url');parser.add_argument('--ollama-model')
    parser.add_argument('--port',type=int,default=4196)
    a=parser.parse_args()
    if not 1024<=a.port<=65535:parser.error('Port must be 1024..65535')
    os.umask(0o077)
    cpp,clang=default_tools(root)
    allowed=tuple(a.allow_root or [root/'demo'])
    engine=Engine(a.data,allowed,Path(a.cppcheck or cpp).resolve() if a.cppcheck or cpp else None,
                  Path(a.clang_tidy or clang).resolve() if a.clang_tidy or clang else None,a.ollama_url,a.ollama_model)
    if a.operation=='doctor':print(json.dumps(engine.analyzers.status,indent=2));return
    if a.operation=='scan':
        r=engine.scan(a.repository)
        print(json.dumps({k:r.get(k) for k in ('id','status','summary','errors','duration_seconds')},indent=2))
        print('Private reports:',a.data/'scans'/r['id'])
        if r['status']=='failed':sys.exit(1)
    else:
        import uvicorn
        from .api import create_app
        print(f'ESAE · http://127.0.0.1:{a.port} · Ctrl+C to stop · local archives persist')
        uvicorn.run(create_app(engine,a.port),host='127.0.0.1',port=a.port,access_log=False)

if __name__=='__main__':main()
