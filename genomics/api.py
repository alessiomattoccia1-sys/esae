# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,uuid
from typing import Literal
from fastapi import FastAPI,HTTPException,Query
from fastapi.responses import FileResponse,Response
from pydantic import BaseModel,Field,ConfigDict
from research_core.web import local_boundary
from .analysis import variant_evidence
from .ai import explain_variant
from esae.scanner import read_regular

class JobRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    genes:list[Literal['BRCA1','BRCA2']]=Field(default_factory=lambda:['BRCA1','BRCA2'],min_length=1,max_length=2)
    per_gene:int=Field(default=40,ge=1,le=100)
    ensembl_limit:int=Field(default=12,ge=0,le=30)
    detail_limit:int=Field(default=6,ge=0,le=12)

def create_app(engine,port=4198):
    app=FastAPI(title='Research Engines / Genomics Evidence Engine',version='0.1.0',docs_url=None,redoc_url=None,openapi_url=None)
    local_boundary(app,port);static=Path(__file__).parent/'static';shared=Path(__file__).resolve().parents[1]/'esae/static'
    @app.exception_handler(ValueError)
    async def invalid(request,exc):return Response(json.dumps({'detail':str(exc)}),status_code=400,media_type='application/json')
    @app.get('/')
    def index():return FileResponse(static/'index.html')
    @app.get('/shared/style.css')
    def shared_style():return FileResponse(shared/'style.css')
    @app.get('/static/{name}')
    def asset(name:str):
        if name not in ('genomics.css','app.js'):raise HTTPException(404)
        return FileResponse(static/name)
    @app.get('/api/status')
    def status():return {'engine':'Genomics Evidence Engine','version':'0.1.0','public_only':True,'busy':engine.lock.locked(),'providers':['NCBI ClinVar','Ensembl REST / VEP'],'future_connectors':{'dbSNP':'not implemented','NCBI Gene':'not implemented','GEO':'not implemented'},'ollama':{'configured':bool(engine.ollama_url and engine.ollama_model),'model':engine.ollama_model},'personal_genetic_data_accepted':False,'diagnostic_use':False}
    @app.get('/api/jobs')
    def jobs():return [{k:j.get(k) for k in ('id','created_at','completed_at','status','phase','progress','summary','duration_seconds','errors')} for j in engine.store.list()]
    @app.post('/api/jobs',status_code=202)
    def run(body:JobRequest):return engine.run(**body.model_dump(),asynchronous=True)
    def get(job_id):
        value=engine.store.get(str(job_id))
        if not value:raise HTTPException(404,'Unknown research job')
        return value
    @app.get('/api/jobs/{job_id}')
    def job(job_id:uuid.UUID):return get(job_id)
    @app.post('/api/jobs/{job_id}/resume',status_code=202)
    def resume(job_id:uuid.UUID):get(job_id);return engine.run(resume=str(job_id),asynchronous=True)
    @app.get('/api/jobs/{job_id}/report')
    def report(job_id:uuid.UUID):get(job_id);return engine.report(str(job_id))
    @app.get('/api/jobs/{job_id}/variants')
    def variants(job_id:uuid.UUID,gene:str=Query('',max_length=20),classification:str=Query('',max_length=200),review:str=Query('',max_length=200),condition:str=Query('',max_length=200),variant:str=Query('',max_length=200),source:Literal['','clinvar','ensembl']=''):
        get(job_id);values=engine.store.variants(str(job_id),gene=gene,classification=classification,review=review,condition=condition,limit=200)
        if variant:values=[v for v in values if variant.lower() in (v['variation_id']+' '+v['vcv']+' '+v['name']).lower()]
        if source=='ensembl':values=[v for v in values if v.get('ensembl',{}).get('status')=='matched']
        return [{'variation_id':v['variation_id'],'vcv':v['vcv'],'name':v['name'],'genes':v['genes'],'germline':v['germline'],'rcv_count':len(v['rcvs']),'scv_count':len(v['submissions']),'conditions':[c for r in v['rcvs'] for c in r['conditions']],'url':v['url'],'ensembl':{'status':v.get('ensembl',{}).get('status'),'most_severe_consequence':v.get('ensembl',{}).get('most_severe_consequence')},'analysis':variant_evidence(v)} for v in values]
    @app.get('/api/jobs/{job_id}/variants/{variation_id}')
    def detail(job_id:uuid.UUID,variation_id:str):
        get(job_id)
        if not variation_id.isdigit() or len(variation_id)>12:raise ValueError('Invalid Variation ID')
        v=engine.store.get_variant(str(job_id),variation_id)
        if not v:raise HTTPException(404,'Unknown variant')
        return {**v,'analysis':variant_evidence(v)}
    @app.get('/api/jobs/{job_id}/sources')
    def sources(job_id:uuid.UUID):get(job_id);return engine.store.sources(str(job_id))
    @app.get('/api/jobs/{job_id}/export/{format}')
    def export(job_id:uuid.UUID,format:Literal['json','html','manifest']):
        get(job_id);folder=engine.root/'jobs'/str(job_id);name='manifest.json' if format=='manifest' else 'report.'+format;p=folder/name
        if not p.is_file():raise HTTPException(404,'Export not ready')
        return FileResponse(p,media_type='text/html' if format=='html' else 'application/json',filename='gee-001-'+str(job_id)+'-'+name)
    @app.post('/api/jobs/{job_id}/verify')
    def verify(job_id:uuid.UUID):get(job_id);return engine.verify(str(job_id))
    @app.post('/api/jobs/{job_id}/variants/{variation_id}/explain')
    def explain(job_id:uuid.UUID,variation_id:str):
        get(job_id)
        if not engine.ollama_url or not engine.ollama_model:raise ValueError('Ollama not configured; deterministic analysis remains available')
        v=engine.store.get_variant(str(job_id),variation_id)
        if not v:raise HTTPException(404)
        if not engine.lock.acquire(False):raise ValueError('A research operation is already active')
        try:
            value=explain_variant(v,engine.ollama_url,engine.ollama_model)
            folder=engine.root/'jobs'/str(job_id)/'ai';folder.mkdir(exist_ok=True);dest=folder/(v['variation_id']+'.json')
            if dest.exists():
                import hashlib
                old=read_regular(dest,128000);history=folder/'history';history.mkdir(exist_ok=True);saved=history/(hashlib.sha256(old).hexdigest()+'.json')
                if not saved.exists():saved.write_bytes(old)
            dest.write_text(json.dumps(value,indent=2)+'\n');return value
        finally:engine.lock.release()
    @app.get('/api/jobs/{job_id}/insights')
    def insights(job_id:uuid.UUID):
        get(job_id);folder=engine.root/'jobs'/str(job_id)/'ai'
        if not folder.exists():return []
        return [json.loads(read_regular(p,128000)) for p in sorted(folder.glob('*.json'))[:200] if p.stem.isdigit()]
    return app
