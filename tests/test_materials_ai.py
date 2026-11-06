# SPDX-License-Identifier: Apache-2.0
import json,httpx,pytest
from research_core.local_ai import hypothesis

def response():return {'hypotheses_to_verify':'Confrontare le condizioni ottiche fra le fonti.','suggested_research_checks':'Verificare la stabilità e i criteri di selezione.','interpretation_limits':'Nessuna efficienza sperimentale è dimostrata.','references':['JVASP-1']}
def patch(monkeypatch,value):
    original=httpx.Client
    def handler(request):
        assert request.url.host=='127.0.0.1';r=json.loads(request.content);assert r['format']['additionalProperties'] is False
        return httpx.Response(200,json={'done':True,'response':json.dumps(value)})
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
def call():return hypothesis({'jid':'JVASP-1','formula':'Si','gap':1.5},{'rank':1},['JVASP-1'],'http://127.0.0.1:11434','local-model',['Si'])
def test_facts_and_numbers_are_never_generated_by_model(monkeypatch):
    patch(monkeypatch,response());r=call();assert r['status']=='generated';assert r['observed_data']['value']['gap']==1.5 and r['computed_result']['value']['rank']==1;assert r['verification_status']=='not_verified'
@pytest.mark.parametrize('bad',['measurement','unknown_ref','extra','list','duplicate','oversized'])
def test_invalid_hypotheses_rejected(monkeypatch,bad):
    v=response()
    if bad=='measurement':v['hypotheses_to_verify']='Efficienza prevista del 30%.'
    elif bad=='unknown_ref':v['references']=['JVASP-999']
    elif bad=='extra':v['physical_measurement']=3
    elif bad=='list':v=[]
    elif bad=='duplicate':v['references']=['JVASP-1','JVASP-1']
    else:v['interpretation_limits']='a'*1001
    patch(monkeypatch,v);assert call()['status']=='unavailable'
def test_remote_ai_endpoint_forbidden():
    with pytest.raises(ValueError):hypothesis({}, {},['JVASP-1'],'https://cloud.example','model')
