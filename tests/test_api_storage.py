# Copyright 2026 Alessio Mattoccia
import json
import pytest
from fastapi.testclient import TestClient
from esae.api import create_app
from esae.storage import Store
from esae.report import html_report

def client(engine):return TestClient(create_app(engine),base_url='http://127.0.0.1:4196')

def test_missing_analyzers_still_save_result(engine,repo):
    r=engine.scan(str(repo));assert r['status']=='partial'
    assert len(r['errors'])>=2 and r['inventory']['file_count']==1
    assert engine.store.get(r['id'])['id']==r['id']
    reopened=Store(engine.root);assert reopened.list()[0]['id']==r['id']

def test_api_scan_export_and_source(engine,repo):
    c=client(engine)
    assert c.get('/').status_code==200
    assert c.get('/api/status').json()['version']=='0.1.1'
    r=engine.scan(str(repo));scan=r['id']
    assert c.get('/api/scans').json()[0]['id']==scan
    assert c.get(f'/api/scans/{scan}').json()['inventory']['file_count']==1
    for fmt in ('json','html'):
        response=c.get(f'/api/scans/{scan}/export/{fmt}');assert response.status_code==200 and 'attachment' in response.headers['content-disposition']
    assert c.get(f'/api/scans/{scan}/source',params={'file':'main.c'}).json()['text']==(repo/'main.c').read_text()
    assert c.get(f'/api/scans/{scan}/source',params={'file':'../../secret'}).status_code==400
    assert c.get('/api/scans/not-a-uuid').status_code==422

def test_boundary_csrf_host_origin(engine,repo):
    c=client(engine)
    assert c.post('/api/scans',json={'path':str(repo)}).status_code==403
    assert c.post('/api/scans',json={'path':str(repo)},headers={'x-esae-request':'1','origin':'https://evil.invalid'}).status_code==403
    assert c.get('/api/status',headers={'host':'evil.invalid'}).status_code==400
    assert c.get('/api/status',headers={'origin':'https://evil.invalid'}).status_code==403
    assert c.post('/api/scans',content='x'*16001,headers={'x-esae-request':'1'}).status_code==413
    assert c.get('/static/README.md').status_code==404

def test_post_outside_allowlist_rejected(engine,tmp_path):
    c=client(engine)
    assert c.post('/api/scans',json={'path':str(tmp_path)},headers={'x-esae-request':'1'}).status_code==400

def test_xss_report_escaped(engine,repo):
    r=engine.scan(str(repo));r['repository']='<script>alert(1)</script>'
    html=html_report(r);assert '<script>' not in html and '&lt;script&gt;' in html

def test_busy_scan_does_not_start(engine,repo):
    engine.lock.acquire()
    try:
        c=client(engine);assert c.post('/api/scans',json={'path':str(repo)},headers={'x-esae-request':'1'}).status_code==400
    finally:engine.lock.release()
