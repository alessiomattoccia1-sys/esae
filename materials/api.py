# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,uuid,math,hashlib
from typing import Literal
from dataclasses import asdict
from fastapi import FastAPI,HTTPException,Query
from fastapi.responses import FileResponse,Response
from pydantic import BaseModel,ConfigDict,Field
from research_core.web import local_boundary
from research_core.local_ai import hypothesis
from .analysis import ScreeningConfig
from .connectors import FUTURE_CONNECTORS
from esae.scanner import read_regular
class RunRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    gap_min:float=Field(default=.8,ge=0,le=20);gap_max:float=Field(default=2.2,gt=0,le=20);target_gap:float=Field(default=1.5,ge=0,le=20);hull_max:float=Field(default=.1,ge=0,le=5);slme_min:float=Field(default=10,ge=0,le=100);exclude_elements:list[str]=Field(default_factory=list,max_length=20);require_dielectric:bool=False

def create_app(engine,port=4202):
    app=FastAPI(title='Research Engines / Materials Discovery Engine',version='0.1.0',docs_url=None,redoc_url=None,openapi_url=None);local_boundary(app,port);static=Path(__file__).parent/'static'
    @app.exception_handler(ValueError)
    async def bad(request,exc):return Response(json.dumps({'detail':str(exc)}),status_code=400,media_type='application/json')
    @app.get('/')
    def index():return FileResponse(static/'index.html')
    @app.get('/shared/style.css')
    def shared():return FileResponse(Path(__file__).resolve().parents[1]/'esae/static/style.css')
    @app.get('/static/{name}')
    def asset(name:str):
        if name not in ('app.js','materials.css'):raise HTTPException(404)
        return FileResponse(static/name)
    @app.get('/api/status')
    def status():return {'engine':'Materials Discovery Engine','version':'0.1.0','public_only':True,'busy':engine.lock.locked(),'providers':['NIST JARVIS-DFT / Figshare'],'optional_or_future':FUTURE_CONNECTORS,'ollama':{'configured':bool(engine.ollama_url and engine.ollama_model),'model':engine.ollama_model},'dft_simulator':False,'cloud_ai':False}
    @app.get('/api/jobs')
    def jobs():return [{k:j.get(k) for k in ['id','created_at','completed_at','status','phase','progress','summary','duration_seconds','errors']} for j in engine.store.list()]
    @app.post('/api/jobs',status_code=202)
    def run(body:RunRequest):return engine.run(ScreeningConfig(**body.model_dump()),asynchronous=True)
    def get(j):
        value=engine.store.get(str(j))
        if not value:raise HTTPException(404,'Unknown materials study')
        return value
    @app.get('/api/jobs/{job_id}')
    def job(job_id:uuid.UUID):return get(job_id)
    @app.post('/api/jobs/{job_id}/resume',status_code=202)
    def resume(job_id:uuid.UUID):get(job_id);return engine.run(resume=str(job_id),asynchronous=True)
    @app.get('/api/jobs/{job_id}/report')
    def report(job_id:uuid.UUID):get(job_id);return engine.report(str(job_id))
    @app.get('/api/jobs/{job_id}/materials')
    def explorer(job_id:uuid.UUID,query:str=Query('',max_length=120),element:str=Query('',max_length=2),gap_min:float|None=Query(None,ge=0,le=20),gap_max:float|None=Query(None,ge=0,le=20),hull_max:float|None=Query(None,ge=0,le=5),slme_min:float|None=Query(None,ge=0,le=100),sort:Literal['jid','gap','hull','slme','formula']='jid',offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500)):
        get(job_id);return engine.store.explorer(str(job_id),query,element,gap_min,gap_max,hull_max,slme_min,sort,offset,limit)
    @app.get('/api/jobs/{job_id}/materials/{jid}')
    def detail(job_id:uuid.UUID,jid:str):
        get(job_id)
        import re
        if not re.fullmatch(r'JVASP-[1-9]\d{0,8}',jid):raise ValueError('Invalid JARVIS ID')
        r=engine.store.get_material(str(job_id),jid)
        if not r:raise HTTPException(404)
        return r
    @app.get('/api/jobs/{job_id}/points')
    def points(job_id:uuid.UUID):
        get(job_id);out=[]
        for r in engine.store.iter_analysis(str(job_id)):
            p=r['properties']
            if p['gap_mbj'] is not None and p['slme_percent'] is not None:out.append({'jid':r['jid'],'gap':p['gap_mbj'],'slme':p['slme_percent']})
            if len(out)==300:break
        return {'selection':'First300 JIDs with both properties, display-only subset; statistics use all complete pairs','points':out}
    @app.get('/api/jobs/{job_id}/export/{kind}')
    def export(job_id:uuid.UUID,kind:Literal['json','html','csv','manifest','method']):
        get(job_id);name={'json':'MDE-001_RESULTS.json','html':'MDE-001_REPORT.html','csv':'MDE-001_CANDIDATES.csv','manifest':'MDE-001_MANIFEST.json','method':'MDE-001_METHODOLOGY.md'}[kind];file=engine.root/'jobs'/str(job_id)/name
        if not file.is_file():raise HTTPException(404,'Export not ready')
        return FileResponse(file,filename=name)
    @app.post('/api/jobs/{job_id}/verify')
    def verify(job_id:uuid.UUID):get(job_id);return engine.verify(str(job_id))
    @app.post('/api/jobs/{job_id}/materials/{jid}/explain')
    def explain(job_id:uuid.UUID,jid:str):
        get(job_id)
        if not engine.ollama_url or not engine.ollama_model:raise ValueError('Ollama not configured; deterministic analysis remains available')
        r=detail(job_id,jid)
        if not engine.lock.acquire(False):raise ValueError('A materials operation is active')
        try:
            observed={k:r[k] for k in ['jid','formula','properties','methods','optical_conditions','url']};observed['official_page_comparison']=[{k:c.get(k) for k in ['jid','status','formula_equivalent','reported_slme_differs','scope']} for c in engine.report(str(job_id)).get('external_detail_checks',[]) if c['jid']==r['jid']];computed={'configuration':engine.report(str(job_id))['configuration'],'scope':'Observed material properties and configured screening criteria; no additional physical calculation'}
            value=hypothesis(observed,computed,[r['jid']],engine.ollama_url,engine.ollama_model,[r['formula']]);folder=engine.root/'jobs'/str(job_id)/'ai';folder.mkdir(exist_ok=True);dest=folder/(r['jid']+'.json')
            if dest.exists():
                old=read_regular(dest,128000);history=folder/'history';history.mkdir(exist_ok=True);target=history/(hashlib.sha256(old).hexdigest()+'.json')
                if not target.exists():target.write_bytes(old)
            dest.write_text(json.dumps(value,indent=2)+'\n');return value
        finally:engine.lock.release()
    @app.get('/api/jobs/{job_id}/insights')
    def insights(job_id:uuid.UUID):
        get(job_id);folder=engine.root/'jobs'/str(job_id)/'ai'
        return [json.loads(read_regular(p,128000)) for p in sorted(folder.glob('JVASP-*.json'))[:100]] if folder.exists() else []
    return app
