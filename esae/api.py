# Copyright 2026 Alessio Mattoccia
from pathlib import Path
from typing import Annotated
import json
import uuid
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from . import __version__
from .scanner import InputError, DEFAULT_EXCLUDES
from .report import html_report

class ScanRequest(BaseModel):
    path: str = Field(min_length=1,max_length=4096)
    excludes: list[str] = Field(default_factory=lambda:list(DEFAULT_EXCLUDES),max_length=50)
    timeout: int = Field(default=30,ge=1,le=120)

def create_app(engine, port=4196):
    app = FastAPI(title='ESAE local engine', version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost','[::1]'])
    @app.middleware('http')
    async def local_boundary(request:Request, call_next):
        if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
            return Response('Local connections only',status_code=403)
        origin=request.headers.get('origin')
        allowed={f'http://127.0.0.1:{port}',f'http://localhost:{port}',f'http://[::1]:{port}'}
        if origin and origin not in allowed:
            return Response('Cross-origin access denied',status_code=403)
        if request.method not in ('GET','HEAD'):
            if request.headers.get('x-esae-request')!='1': return Response('Same-origin request header required',status_code=403)
            try:
                if int(request.headers.get('content-length','0'))>16000:return Response('Request too large',status_code=413)
            except ValueError:return Response('Invalid length',status_code=400)
            body=b''
            async for chunk in request.stream():
                body+=chunk
                if len(body)>16000:return Response('Request too large',status_code=413)
            request._body=body
        response=await call_next(request)
        response.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';response.headers['Cache-Control']='no-store'
        return response
    @app.exception_handler(InputError)
    async def invalid(request, exc):return Response(json.dumps({'detail':str(exc)}),status_code=400,media_type='application/json')
    static=Path(__file__).parent/'static'
    @app.get('/')
    def index():return FileResponse(static/'index.html')
    @app.get('/static/{name}')
    def asset(name:str):
        if name not in ('app.js','style.css'):raise HTTPException(404)
        return FileResponse(static/name)
    @app.get('/api/status')
    def status():return {'version':__version__,'tools':engine.analyzers.status,'allowed_roots':[str(p) for p in engine.allowed],
                         'ollama':{'configured':bool(engine.ollama_url and engine.ollama_model),'model':engine.ollama_model},'busy':engine.lock.locked()}
    @app.get('/api/scans')
    def scans():return engine.store.list()
    @app.post('/api/scans',status_code=202)
    def scan(body:ScanRequest):
        if any(not x or len(x)>200 or '\0' in x for x in body.excludes):raise InputError('Invalid exclusion pattern')
        return engine.scan(body.path,tuple(body.excludes),body.timeout,asynchronous=True)
    def get(scan_id:uuid.UUID):
        report=engine.store.get(str(scan_id))
        if not report:raise HTTPException(404,'Unknown scan')
        return report
    @app.get('/api/scans/{scan_id}')
    def report(scan_id:uuid.UUID):return get(scan_id)
    @app.get('/api/scans/{scan_id}/source')
    def source(scan_id:uuid.UUID,file:Annotated[str,Query(max_length=4096)]):
        get(scan_id);return {'file':file,'text':engine.source(str(scan_id),file)}
    @app.get('/api/scans/{scan_id}/export/{format}')
    def export(scan_id:uuid.UUID,format:str):
        result=get(scan_id)
        if format=='json': data=json.dumps(result,ensure_ascii=False,indent=2);media='application/json'
        elif format=='html':data=html_report(result);media='text/html'
        else:raise HTTPException(404)
        return Response(data,media_type=media,headers={'Content-Disposition':f'attachment; filename="esae-{scan_id}.{format}"'})
    @app.post('/api/scans/{scan_id}/findings/{finding_id}/explain')
    def ai(scan_id:uuid.UUID,finding_id:str):
        get(scan_id)
        if len(finding_id)!=24:raise InputError('Invalid finding id')
        return engine.explain(str(scan_id),finding_id)
    return app
