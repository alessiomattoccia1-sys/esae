from pathlib import Path
import pytest
from esae.cli import default_tools
from esae.service import Engine

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def repo(tmp_path):
    p=tmp_path/'repo';p.mkdir();(p/'main.c').write_text('int main(void) { return 0; }\n')
    return p

@pytest.fixture
def engine(tmp_path,repo):
    return Engine(tmp_path/'state',(repo,),None,None)

@pytest.fixture(scope='session')
def native_report(tmp_path_factory):
    cpp,clang=default_tools(ROOT)
    assert cpp and clang, 'Native analyzers must be installed for qualification'
    state=tmp_path_factory.mktemp('native')
    engine=Engine(state,(ROOT/'demo',),Path(cpp),Path(clang))
    assert all(x['available'] for x in engine.analyzers.status.values()),engine.analyzers.status
    report=engine.scan(str(ROOT/'demo'))
    return engine,report
