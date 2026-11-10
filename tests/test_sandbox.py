# Copyright 2026 Alessio Mattoccia
from pathlib import Path
import platform
import sys
import pytest
from esae.runner import run_tool

@pytest.mark.skipif(platform.system()!='Darwin',reason='macOS sandbox boundary')
def test_native_sandbox_denies_original_reads_writes_network(tmp_path):
    secret=tmp_path/'outside'/'secret.c';secret.parent.mkdir();secret.write_text('OWNER ORIGINAL')
    work=tmp_path/'own-run'/'tools'/'probe'
    code='''import pathlib,socket,sys,json
p=pathlib.Path(sys.argv[1]);result={}
for label,fn in [('read',lambda:p.read_text()),('write',lambda:p.write_text('bad')),('network',lambda:socket.create_connection(('127.0.0.1',9),timeout=.1))]:
 try:fn();result[label]='ALLOWED'
 except PermissionError:result[label]='DENIED'
 except OSError as e:result[label]='OS_ERROR:'+str(e.errno)
print(json.dumps(result))
'''
    r=run_tool([sys.executable,'-I','-c',code,str(secret)],work,timeout=5)
    assert r.returncode==0,(r.stderr,r.error,r.returncode)
    import json
    result=json.loads(r.stdout)
    assert result=={'read':'DENIED','write':'DENIED','network':'DENIED'}
    assert secret.read_text()=='OWNER ORIGINAL'

def test_timeout_kills_process_group(tmp_path):
    r=run_tool([sys.executable,'-I','-c','import time;time.sleep(8)'],tmp_path/'timeout',timeout=.15)
    assert r.error and 'timeout' in r.error.lower() and r.duration<5

def test_output_limit(tmp_path):
    r=run_tool([sys.executable,'-I','-c','print("x"*100000)'],tmp_path/'output',timeout=5,output_limit=2000)
    assert r.error and 'output limit' in r.error.lower()

def test_interrupt_reaps_owned_analyzer(monkeypatch,tmp_path):
    import esae.runner as module
    killed=[];waited=[]
    class Child:
        pid=999999
        def poll(self):return None
        def wait(self,timeout):waited.append(timeout)
    monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**kw:Child())
    monkeypatch.setattr(module.os,'killpg',lambda pid,sig:killed.append((pid,sig)))
    def interrupt(delay):raise KeyboardInterrupt()
    monkeypatch.setattr(module.time,'sleep',interrupt)
    with pytest.raises(KeyboardInterrupt):module.run_tool(['/usr/bin/true'],tmp_path/'interrupt',sandbox=False)
    assert killed==[(999999,module.signal.SIGKILL)] and waited==[5]
