# SPDX-License-Identifier: Apache-2.0
import json,hashlib,io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from genomics.service import GenomicsEngine
from genomics.api import create_app
from genomics.connectors import Ensembl
from research_core.http import PublicCache
from research_core.locking import OperationLock
from research_core import EmbeddedAdapter,now
from test_genomics import vcv_fixture

@pytest.fixture
def completed_fixture(tmp_path,vcv_fixture,monkeypatch):
    import genomics.service as service
    class FixtureClinVar:
        def __init__(self,cache):self.cache=cache
        def cache_source(self,url,data):
            key=hashlib.sha256(url.encode()).hexdigest();root=self.cache.root
            source={'id':key,'url':url,'organization':'NCBI ClinVar / synthetic fixture test only','acquired_at':now(),'release_date':None,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'parser_version':'gee-0.1.0','errors':[]}
            (root/(key+'.data')).write_bytes(data);(root/(key+'.json')).write_text(json.dumps(source));return data,source
        def search(self,gene):
            _,s=self.cache_source('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?fixture=BRCA1',b'fixture index')
            return [1],{'gene':gene,'query':'synthetic fixture','count':1,'source':s}
        def vcv(self,vid):return self.cache_source('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?fixture=1',vcv_fixture)
    monkeypatch.setattr(service,'ClinVar',FixtureClinVar)
    engine=GenomicsEngine(tmp_path/'fixture-archive');job=engine.run(genes=['BRCA1'],per_gene=1,ensembl_limit=0,detail_limit=0)
    assert job['status']=='completed',job
    return engine,job

def test_fixture_full_local_pipeline_replays_from_raw_cache(completed_fixture):
    engine,job=completed_fixture;r=engine.verify(job['id'])
    assert r['passed'] and r['network_used'] is False and r['variants_reparsed']==1
    assert engine.report(job['id'])['metrics']['current_germline_scv_records']==3

def test_api_dashboard_filters_exports_and_integrity(completed_fixture):
    engine,job=completed_fixture
    with TestClient(create_app(engine),base_url='http://127.0.0.1:4198') as client:
        assert 'GENOMICS EVIDENCE ENGINE' in client.get('/').text
        assert client.get('/shared/style.css').status_code==200
        assert client.get('/api/status').json()['personal_genetic_data_accepted'] is False
        rows=client.get('/api/jobs/'+job['id']+'/variants?gene=BRCA1').json();assert len(rows)==1
        assert 'submissions' not in rows[0]
        detail=client.get('/api/jobs/'+job['id']+'/variants/1').json();assert len(detail['submissions'])==3
        assert client.get('/api/jobs/'+job['id']+'/variants?gene=BRCA2').json()==[]
        for kind in ('json','html','manifest'):assert client.get('/api/jobs/'+job['id']+'/export/'+kind).status_code==200
        assert client.post('/api/jobs/'+job['id']+'/verify',headers={'x-research-request':'1'}).json()['passed']
        assert client.post('/api/jobs/'+job['id']+'/variants/1/explain',headers={'x-research-request':'1'}).status_code==400

def test_local_boundary_and_personal_input_rejected(tmp_path):
    with TestClient(create_app(GenomicsEngine(tmp_path/'archive')),base_url='http://127.0.0.1:4198') as client:
        assert client.post('/api/jobs',json={}).status_code==403
        assert client.post('/api/jobs',json={},headers={'x-research-request':'1','origin':'https://evil.example'}).status_code==403
        assert client.get('/api/status',headers={'host':'evil.example'}).status_code==400
        assert client.post('/api/jobs',json={'personal_dna':'not accepted'},headers={'x-research-request':'1'}).status_code==422
        assert client.post('/api/jobs',json={'per_gene':101},headers={'x-research-request':'1'}).status_code==422
        assert client.get('/api/jobs/not-a-uuid').status_code==422
        assert client.get('/static/anything').status_code==404
        assert client.get('/').headers['content-security-policy'].startswith("default-src 'self'")

def test_cache_change_breaks_frozen_reproduction(completed_fixture):
    engine,job=completed_fixture
    cache=engine.root/'jobs'/job['id']/'cache';next(cache.glob('*.data')).write_bytes(b'corrupt')
    with pytest.raises(ValueError):engine.verify(job['id'])

def test_cross_process_operation_lease_and_running_job_not_recovered(tmp_path):
    from genomics.storage import GenomicStore
    s=GenomicStore(tmp_path/'store');lease=OperationLock(s.root/'active.lock');assert lease.acquire(False)
    j=s.create('genomics',{});other=GenomicStore(tmp_path/'store')
    assert other.get(j['id'])['status']=='running'
    second=OperationLock(s.root/'active.lock');assert not second.acquire(False)
    lease.release();assert second.acquire(False);second.release()

def test_ensembl_rejects_gene_only_and_assembly_reference_mismatches():
    class Cache:
        def fetch(self,url):return json.dumps([{'assembly_name':'GRCh37','seq_region_name':'17','start':100,'end':100,'strand':1,'allele_string':'A/G'}]).encode(),{}
    e=Ensembl(Cache())
    with pytest.raises(ValueError):e.vep_snv({'assembly':'GRCh37'})
    with pytest.raises(ValueError):e.vep_snv({'assembly':'GRCh38','chromosome':'17','position':100,'reference':'A','alternate':'G'})

def test_download_streaming_path_and_hash(tmp_path):
    data=b'x'*200000
    class Response(io.BytesIO):
        status=200;headers={'Content-Length':str(len(data)),'ETag':'"fixture-v1"'}
    class Opener:
        def open(self,req,timeout):return Response(data)
    cache=PublicCache(tmp_path,max_response_bytes=300000);cache.opener=Opener()
    path,meta=cache.fetch('https://rest.ensembl.org/info/data',as_path=True)
    assert isinstance(path,Path) and path.stat().st_size==200000 and meta['sha256']==hashlib.sha256(data).hexdigest()
    assert cache.fetch(meta['url'],offline=True,as_path=True)[0]==path

def test_download_resume_requires_matching_validator(tmp_path):
    data=b'abcdef';url='https://rest.ensembl.org/info/data';key=hashlib.sha256(url.encode()).hexdigest()
    (tmp_path/(key+'.part')).write_bytes(data[:3]);(tmp_path/(key+'.partial.json')).write_text(json.dumps({'validator':'"v1"'}))
    class Response(io.BytesIO):
        status=206;headers={'Content-Length':'3','Content-Range':'bytes 3-5/6','ETag':'"v1"'}
    class Opener:
        def open(self,req,timeout):
            assert req.get_header('Range')=='bytes=3-'
            assert req.get_header('If-range')=='"v1"'
            return Response(data[3:])
    cache=PublicCache(tmp_path);cache.opener=Opener();assert cache.fetch(url)[0]==data

def test_embedded_adapter_uses_original_engine_without_mutation(native_report):
    engine,report=native_report;before=json.dumps(engine.store.get(report['id']),sort_keys=True)
    adapter=EmbeddedAdapter(engine);assert adapter.result(report['id'])['evidence_kind']=='computational_result'
    assert adapter.list_jobs()[0]['id']==report['id']
    assert json.dumps(engine.store.get(report['id']),sort_keys=True)==before
