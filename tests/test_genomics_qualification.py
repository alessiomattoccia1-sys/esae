# SPDX-License-Identifier: Apache-2.0
"""Qualification gates: AI cannot supply metrics or unreferenced source claims."""
import json
from copy import deepcopy
import httpx,pytest
from genomics.ai import explain_variant
from genomics.parsers import parse_vcv,stars
from genomics.export import export,public_check
from genomics.replay import replay
from test_genomics import vcv_fixture
from test_genomics_api import completed_fixture

@pytest.fixture
def ai_variant(vcv_fixture):return parse_vcv(vcv_fixture)[0]

def mocked_generation(monkeypatch,value):
    original=httpx.Client
    def respond(request):
        body=json.loads(request.content)
        assert request.url.host=='127.0.0.1' and body['stream'] is False
        assert body['format']['additionalProperties'] is False
        assert 'NEVER_INDEX_THIS' not in body['prompt']
        return httpx.Response(200,json={'done':True,'response':json.dumps(value)})
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))

def output():return {'hypotheses_to_verify':'Ipotesi da verificare attraverso il confronto delle evidenze disponibili.','suggested_research_checks':'Controllare criteri dichiarati, date e identità delle condizioni.','interpretation_limits':'I metadati non consentono conclusioni cliniche o causali.','references':['VCV000000001.2']}

def test_local_ai_source_observations_and_counts_are_deterministic(monkeypatch,ai_variant):
    before=deepcopy(ai_variant);mocked_generation(monkeypatch,output())
    r=explain_variant(ai_variant,'http://127.0.0.1:11434','existing-local-model')
    assert r['status']=='generated' and r['verification_status']=='not_verified'
    assert r['observed_data']['official_aggregate']==ai_variant['germline']
    assert r['computational_result']['selected_classification_counts']=={'Pathogenic':1,'Benign':1,'Uncertain significance':1}
    assert r['not_determinable']['kind']=='not_determinable' and ai_variant==before

def test_exact_source_condition_identifiers_are_not_invented_measurements(monkeypatch,ai_variant):
    value=output();value['suggested_research_checks']='Verificare i criteri per MedGen:C1 e SCV000000001.1.'
    mocked_generation(monkeypatch,value)
    assert explain_variant(ai_variant,'http://127.0.0.1:11434','existing-local-model')['status']=='generated'

@pytest.mark.parametrize('bad',['list','extra','numeric','bad_ref','five_refs','empty','oversized','duplicate_refs'])
def test_local_ai_rejects_schema_measurements_and_reference_failures(monkeypatch,ai_variant,bad):
    value=output()
    if bad=='list':value=[]
    elif bad=='extra':value['observed_data']='Invented source fact'
    elif bad=='numeric':value['hypotheses_to_verify']='Conflitti nel 50% dei casi.'
    elif bad=='bad_ref':value['references']=['SCV999999999.1']
    elif bad=='five_refs':value['references']=['VCV000000001.2']*5
    elif bad=='duplicate_refs':value['references']=['VCV000000001.2']*2
    elif bad=='empty':value['interpretation_limits']=''
    elif bad=='oversized':value['interpretation_limits']='x'*1001
    mocked_generation(monkeypatch,value);r=explain_variant(ai_variant,'http://127.0.0.1:11434','existing-local-model')
    assert r['status']=='unavailable' and 'fields' not in r and 'computational_result' not in r

def test_public_export_and_normalized_replay_are_gated_and_tamper_detected(completed_fixture,tmp_path):
    engine,job=completed_fixture;out=tmp_path/'public';r=export(engine,job['id'],out)
    assert r['passed'] and not r['raw_sources_copied']
    assert replay(out/'gee-001-input.json.gz',out/'report.json')['passed']
    assert 'NEVER_INDEX_THIS' not in (out/'report.json').read_text()
    report=json.loads((out/'report.json').read_text());report['analysis_sha256']='0'*64
    (out/'report.json').write_text(json.dumps(report));assert not replay(out/'gee-001-input.json.gz',out/'report.json')['passed']
    job['status']='partial';engine.store.save(job)
    with pytest.raises(ValueError):export(engine,job['id'],out)

@pytest.mark.parametrize('value',[{'Sample':{}},{'email':'private'},{'x':'/'.join(['','Users','private','secret'])}])
def test_public_projection_rejects_private_or_sample_fields(value):
    with pytest.raises(ValueError):public_check(value)

def test_individual_variant_review_status_is_documented_zero_stars():
    assert stars('no classification for the individual variant')==0
