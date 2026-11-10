# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Known synthetic cases, distinct from live JARVIS qualification."""
from pathlib import Path
import io,json,math,zipfile,hashlib
from dataclasses import asdict
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from materials.parser import normalize,quantity,records,json_array
from materials.analysis import ScreeningConfig,screen,analyze,correlation
from materials.connectors import MEMBER,source_policy
from materials.service import MaterialsEngine
from materials.api import create_app

def source(i=1,gap=1.5,hull=.05,slme=20):return {'jid':f'JVASP-{i}','formula':'Si','func':'OptB88vdW','atoms':{'lattice_mat':[[2,0,0],[0,2,0],[0,0,2]],'coords':[[0,0,0]],'cartesian':False,'elements':['Si'],'props':['']},'mbj_bandgap':gap,'optb88vdw_bandgap':1.,'formation_energy_peratom':-1.,'ehull':hull,'slme':slme,'mepsx':10.,'mepsy':11.,'mepsz':12.,'crys':'cubic'}
@pytest.fixture
def sources():return [source(1,1.5,.2,25),source(2,1.4,.05,15),source(3,1.6,0,None),source(4,None,0,30),source(5,0,0,0),source(6,2.5,0,20),source(7,1.1,None,30)]
@pytest.fixture
def rows(sources):return [normalize(r) for r in sources]
def ingest_counts(n):return {'records_seen':n,'valid_unique':n,'invalid_records':0,'duplicates':0,'invalid_reasons':{},'property_anomalies':{}}

def test_known_filters_and_rankings_preserve_missingness(rows):
    r,reasons=screen(rows,ScreeningConfig());assert [v['jid'] for v in r['gap_only']]==['JVASP-1','JVASP-2','JVASP-3','JVASP-7'];assert [v['jid'] for v in r['stability']]==['JVASP-3','JVASP-2'];assert [v['jid'] for v in r['optical']]==['JVASP-2'];assert reasons=={'above_hull_threshold':1,'missing_slme_after_stability':1,'missing_tbmbj_gap':1,'outside_gap_interval':2,'missing_hull_after_gap_filter':1}

def test_expected_counts_and_explicit_denominators(rows):
    r,_=analyze(rows,ScreeningConfig(),ingest_counts(7));m=r['metrics'];assert m['valid_unique_materials']==7;assert m['screen_counts']['optical']=={'numerator':1,'denominator':7,'percent':14.285714};assert m['availability']['gap_mbj']['numerator']==6;assert sum(b['count'] for b in r['bandgap_distributions']['gap_mbj']['bins'])==6;assert len(r['sensitivity'])==12;assert len(r['findings'])==3

def test_ranking_is_independent_of_input_order(rows):
    a,_=analyze(rows,ScreeningConfig(),ingest_counts(7));b,_=analyze(list(reversed(rows)),ScreeningConfig(),ingest_counts(7));assert a['analysis_sha256']==b['analysis_sha256']

def test_formation_energy_cannot_replace_missing_hull():
    r=normalize(source(hull=None));assert r['properties']['formation_ev_atom']==-1 and r['properties']['hull_ev_atom'] is None;rank,_=screen([r],ScreeningConfig());assert not rank['stability']
@pytest.mark.parametrize('value',[None,'na','NaN',float('nan'),float('inf'),''])
def test_missing_numeric_fields_are_never_zero(value):assert quantity(value,'eV','bandgap') is None
@pytest.mark.parametrize('kind,unit',[('bandgap','eV'),('hull','eV/atom'),('slme','%')])
def test_zero_values_are_valid(kind,unit):assert quantity(0,unit,kind)==0
@pytest.mark.parametrize('value,unit,kind,expected',[(1500,'meV','bandgap',1.5),(50,'meV/atom','hull',.05),(.2,'fraction','slme',20),(1,'nm','lattice',10)])
def test_known_unit_conversions(value,unit,kind,expected):assert quantity(value,unit,kind)==expected
@pytest.mark.parametrize('value,unit,kind',[(True,'eV','bandgap'),(-1,'eV/atom','hull'),(120,'%','slme'),(1,'eV/atom','bandgap')])
def test_invalid_or_incompatible_quantities_rejected(value,unit,kind):
    with pytest.raises(ValueError):quantity(value,unit,kind)

def test_crystal_cartesian_fractional_and_formula_identity():
    r=source();r['atoms']['coords']=[[1,1,1]];r['atoms']['cartesian']=True;n=normalize(r);assert n['structure']['fractional_coordinates']==[[.5,.5,.5]];assert n['structure']['volume_angstrom3']==pytest.approx(8);r['formula']='GaAs'
    with pytest.raises(ValueError):normalize(r)

def test_polymorphs_not_deduplicated_by_formula(rows):
    assert rows[0]['formula']==rows[1]['formula'] and rows[0]['jid']!=rows[1]['jid']

def test_source_nan_constants_streaming_and_truncated_or_malformed_arrays():
    assert list(json_array(io.BytesIO(b'[{"jid":"JVASP-1","value":NaN,"infinite":Infinity}]')))==[{'jid':'JVASP-1','value':None,'infinite':None}]
    for raw in [b'[{"a":1}',b'[{} {}]',b'[{},]',b'[{}] trailing']:
        with pytest.raises(ValueError):list(json_array(io.BytesIO(raw)))

def test_compressed_stream_and_archive_limits(tmp_path):
    p=tmp_path/'source.zip'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(MEMBER,json.dumps([source()]))
    assert len(list(records(p)))==1
    with pytest.raises(ValueError):list(records(p,max_expanded=10))

def test_statistical_reference_cases_and_constant_data():
    assert correlation([1,2,3,None],[2,4,6,7])['pearson']==1
    assert correlation([1,2,3],[6,4,2])['spearman']==-1
    assert correlation([1,1,1],[2,4,6])['status']=='not_determinable'
    assert correlation([1,1,2],[1,2,3])['spearman']==pytest.approx(.866025403784)
@pytest.mark.parametrize('config',[ScreeningConfig(gap_min=3),ScreeningConfig(hull_max=-1),ScreeningConfig(slme_min=101),ScreeningConfig(target_gap=float('nan'))])
def test_invalid_configuration_rejected(config):
    with pytest.raises(ValueError):config.validate()
@pytest.mark.parametrize('url',['http://api.figshare.com/v2/articles/6815699','https://evil.example/file','https://api.figshare.com/v2/articles/1','https://ndownloader.figshare.com/files/1','https://127.0.0.1/source','https://rest.ensembl.org/info/data'])
def test_materials_source_policy_separate_and_restrictive(url):
    with pytest.raises(ValueError):source_policy(url)

@pytest.fixture
def fixture_engine(tmp_path,sources,monkeypatch):
    import materials.service as module
    path=tmp_path/'fixture.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(MEMBER,json.dumps(sources))
    class Connector:
        def __init__(self,cache):pass
        def acquire(self,offline=False):return path,{'dataset':'Synthetic test only','snapshot':'fixture.zip','doi':'synthetic-fixture','source':{'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},'license':{'name':'original synthetic fixture'}}
    monkeypatch.setattr(module,'JarvisConnector',Connector);engine=MaterialsEngine(tmp_path/'archive');job=engine.run();assert job['status']=='completed',job
    return engine,job,path

def test_complete_fixture_pipeline_reports_persistence_and_raw_replay(fixture_engine):
    engine,job,path=fixture_engine;assert engine.verify(job['id'])['passed'];assert engine.report(job['id'])['metrics']['screen_counts']['optical']['numerator']==1;assert engine.store.explorer(job['id'],slme_min=20)['total']==4

def test_duplicate_import_is_idempotent_and_conflicts_fail(tmp_path):
    path=tmp_path/'d.zip';r=source()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(MEMBER,json.dumps([r,r]))
    engine=MaterialsEngine(tmp_path/'archive');c,_=engine.ingest(path);assert c['valid_unique']==1 and c['duplicates']==1
    r2=deepcopy(r);r2['slme']=21
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(MEMBER,json.dumps([r,r2]))
    with pytest.raises(ValueError):engine.ingest(path)

def test_api_real_fixture_explorer_detail_exports_and_no_ollama(fixture_engine):
    engine,j,path=fixture_engine
    with TestClient(create_app(engine),base_url='http://127.0.0.1:4202') as c:
        base='/api/jobs/'+j['id'];assert c.get('/').status_code==200;assert c.get('/api/status').json()['dft_simulator'] is False
        assert c.get(base+'/materials?gap_min=1&gap_max=2').json()['total']==4
        detail=c.get(base+'/materials/JVASP-2').json();assert detail['formula']=='Si' and detail['properties']['gap_mbj']==1.4
        for kind in ['json','html','csv','manifest','method']:assert c.get(base+'/export/'+kind).status_code==200
        assert c.post(base+'/materials/JVASP-2/explain',headers={'x-research-request':'1'}).status_code==400
        assert c.get(base+'/insights').json()==[]
        assert c.post(base+'/verify',headers={'x-research-request':'1'}).json()['passed']
        assert c.post('/api/jobs',json={'private_file':'forbidden'},headers={'x-research-request':'1'}).status_code==422
        assert c.post('/api/jobs',json={}).status_code==403
        assert c.get('/api/status',headers={'origin':'https://evil.example'}).status_code==403
        assert c.get('/api/status',headers={'host':'evil.example'}).status_code==400


def test_parenthesized_formula_equivalence():
    from materials.parser import composition
    assert composition('Sb(IF3)2')[1]==composition('SbI2F6')[1]
    assert composition('Ca3(PO4)2')[1]==composition('Ca3P2O8')[1]

@pytest.mark.parametrize('symbols',[['XYZ'],['si'],[''],['H1']])
def test_element_filters_require_real_symbols(symbols):
    with pytest.raises(ValueError):ScreeningConfig(exclude_elements=symbols).validate()

def test_composition_and_dielectric_filter(rows):
    assert not screen(rows,ScreeningConfig(exclude_elements=('Si',)))[0]['gap_only']
    rows[1]['properties']['meps_diagonal'][0]=None
    assert len(screen(rows,ScreeningConfig(require_dielectric=True))[0]['gap_only'])==3

def test_public_replay_and_tamper_detection(tmp_path,rows):
    import gzip
    from materials.replay import replay
    r,_=analyze(rows,ScreeningConfig(),ingest_counts(7));r['dataset']={'source':{'sha256':'fixture-source'}};r['ingestion']=ingest_counts(7)
    p=tmp_path/'input.gz';report_path=tmp_path/'report.json';report_path.write_text(json.dumps(r));p.write_bytes(gzip.compress(json.dumps({'materials':rows,'source_sha256':'fixture-source'}).encode()))
    assert replay(p,report_path)['passed'];rows[0]['properties']['gap_mbj']=.5;p.write_bytes(gzip.compress(json.dumps({'materials':rows,'source_sha256':'fixture-source'}).encode()));assert not replay(p,report_path)['passed']

def test_public_export_rejects_unverified_source_terms(fixture_engine,tmp_path):
    from materials.export import export
    engine,job,_=fixture_engine
    with pytest.raises(ValueError,match='redistribution terms'):export(engine,job['id'],tmp_path/'public')

def test_incomplete_job_resumes_from_fixed_cache_idempotently(fixture_engine):
    engine,job,_=fixture_engine;job['status']='interrupted';engine.store.save(job)
    fresh=engine.run(resume=job['id']);assert fresh['status']=='completed';assert fresh['summary']['valid_unique_materials']==7;assert engine.store.explorer(job['id'])['total']==7;assert engine.verify(job['id'])['passed']
