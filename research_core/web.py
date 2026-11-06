# SPDX-License-Identifier: Apache-2.0
"""Local-only API boundary adapted from ESAE, without changing ESAE's API."""
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

def local_boundary(app,port,request_header='x-research-request'):
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','[::1]'])
    @app.middleware('http')
    async def boundary(request:Request,call_next):
        if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):return Response('Local connections only',status_code=403)
        origin=request.headers.get('origin');allowed={f'http://127.0.0.1:{port}',f'http://localhost:{port}',f'http://[::1]:{port}'}
        if origin and origin not in allowed:return Response('Cross-origin access denied',status_code=403)
        if request.method not in ('GET','HEAD'):
            if request.headers.get(request_header)!='1':return Response('Same-origin header required',status_code=403)
            try:
                if int(request.headers.get('content-length','0'))>16000:return Response('Request too large',status_code=413)
            except ValueError:return Response('Invalid length',status_code=400)
            body=b''
            async for chunk in request.stream():
                body+=chunk
                if len(body)>16000:return Response('Request too large',status_code=413)
            request._body=body
        response=await call_next(request)
        response.headers.update({'Content-Security-Policy':"default-src 'self'; connect-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
        return response
