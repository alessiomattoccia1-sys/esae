import json
import pytest
import httpx
from contextlib import contextmanager
from esae.ai import validate_ollama,explain,FIELDS

@pytest.mark.parametrize('url',['https://api.openai.com','http://example.com:11434','http://192.168.1.1:11434','http://localhost:11434','http://127.0.0.1:11434/proxy','http://user:pass@127.0.0.1:11434'])
def test_nonlocal_ollama_rejected(url):
    with pytest.raises(ValueError):validate_ollama(url)

def test_ollama_unavailable_is_explicit():
    f={'id':'demo','file':'a.c','line':1,'rule_id':'nullPointer','source_tool':'cppcheck','message':'Null','confidence_type':'static_analysis'}
    result=explain(f,'int x;','http://127.0.0.1:1','not-downloaded',timeout=.2)
    assert result['status']=='unavailable' and result['verification_status']=='not_verified'

def test_ai_schema_anchored_to_real_finding(monkeypatch):
    captured={}
    class Client:
        def __init__(self,**kwargs):assert kwargs['trust_env'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        @contextmanager
        def stream(self,method,url,json):
            captured.update(json)
            yield httpx.Response(200,content=__import__('json').dumps({'done':True,'response':__import__('json').dumps({k:'Hypothesis' for k in FIELDS})}),request=httpx.Request(method,url))
    monkeypatch.setattr(httpx,'Client',Client)
    f={'id':'actual-finding','file':'a.c','line':1,'rule_id':'r','source_tool':'cppcheck','message':'Real diagnostic','confidence_type':'static_analysis'}
    r=explain(f,'int a;','http://127.0.0.1:11434','test')
    assert r['status']=='generated' and r['finding_id']=='actual-finding' and r['confidence_type']=='ai_hypothesis'
    assert 'actual-finding' in captured['prompt'] and captured['keep_alive']==0
