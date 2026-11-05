from pathlib import Path
from esae.tools import cppcheck_findings,clang_findings
from esae.models import Finding,deduplicate
from esae.dependencies import graph
from esae.risks import analyze

def test_xml_parsing(tmp_path):
    files={'a.c':'int *x=0;\nreturn *x;\n'}
    xml=f'<results><errors><error id="nullPointer" severity="error" msg="Null pointer"><location file="{tmp_path}/a.c" line="2" column="8"/></error></errors></results>'
    found,errors=cppcheck_findings(xml,tmp_path,files)
    assert not errors and found[0].category=='null_pointer' and found[0].line==2
    assert found[0].verification_status=='reported_by_tool_not_manually_verified'

def test_yaml_offset_utf8(tmp_path):
    source='// è\nint *x=0;\nreturn *x;\n'
    data={'Diagnostics':[{'DiagnosticName':'clang-analyzer-core.NullDereference','Level':'Warning','DiagnosticMessage':{'FilePath':str(tmp_path/'a.c'),'FileOffset':len('// è\nint *x=0;\nreturn '.encode()),'Message':'Null dereference','Replacements':[]}}]}
    found,errors=clang_findings(data,tmp_path,{'a.c':source})
    assert not errors and found[0].line==3 and found[0].column==8

def test_dedup_keeps_tool_reports():
    args=('a.c',2,3,'high','null_pointer','nullPointer','cppcheck','Null')
    found=deduplicate([Finding(*args),Finding(*args)],'scan')
    assert len(found)==1 and len(found[0].tool_reports)==2 and found[0].scan_id=='scan'
    distinct=Finding('a.c',2,4,'high','null_pointer','nullPointer','cppcheck','Other')
    assert len(deduplicate([Finding(*args),distinct],'s'))==2

def test_graph_cycles_and_unresolved():
    g=graph({'a.h':'#include "b.h"\n','b.h':'#include "a.h"\n#include <stdint.h>\n'})
    assert g['cycles']==[['a.h','b.h']] and len(g['edges'])==2
    assert g['unresolved'][0]['include']=='stdint.h'
    assert g['kind']=='lexical_include_graph'

def test_cross_tool_dedup_keeps_origins():
    a=Finding('a.c',2,8,'high','null_pointer','nullPointer','cppcheck','Null pointer dereference')
    b=Finding('a.c',2,8,'medium','null_pointer','clang-analyzer-core.NullDereference','clang-tidy','Dereference of null pointer')
    found=deduplicate([a,b],'demo')
    assert len(found)==1 and {r['tool'] for r in found[0].tool_reports}=={'cppcheck','clang-tidy'}

def test_compiler_error_is_not_counted_as_defect(tmp_path):
    found,errors=clang_findings({'Diagnostics':[{'DiagnosticName':'clang-diagnostic-error','DiagnosticMessage':{'FilePath':str(tmp_path/'a.c'),'FileOffset':0,'Message':'missing header'}}]},tmp_path,{'a.c':'int x;'})
    assert not found and errors

def test_heuristics_not_promoted_to_defects():
    source='volatile int shared;\nvoid Sensor_IRQHandler(void) { void *p=malloc(4); sleep(1); free(p); }\nint rec(int n) { return n ? rec(n-1) : 0; }\n'
    findings=analyze({'a.c':source});rules={f.rule_id for f in findings}
    assert {'embedded.dynamic-allocation','embedded.possibly-blocking-call','embedded.isr-suspicious-call','embedded.recursion-candidate','embedded.shared-volatile-candidate'}<=rules
    assert all(f.confidence_type=='heuristic_indicator' and f.verification_status=='requires_engineering_review' for f in findings)

def test_comments_strings_do_not_create_risks():
    assert analyze({'a.c':'// malloc(4);\nconst char *s="sleep(1)";\nint safe(void){ return 0; }\n'})==[]
