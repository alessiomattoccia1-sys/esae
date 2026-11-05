import pytest

@pytest.mark.integration
def test_real_native_tools(native_report):
    engine,r=native_report
    assert r['status']=='completed',r['errors']
    assert {x['tool'] for x in r['executed']}=={'cppcheck','clang-tidy'}
    assert r['source_integrity']['unchanged_after_scan'] is True

@pytest.mark.integration
def test_real_demo_expected_defects(native_report):
    engine,r=native_report
    static=[x for x in r['findings'] if x['confidence_type']=='static_analysis']
    cats={x['category'] for x in static}
    assert {'bounds','null_pointer','uninitialized','memory_leak'}<=cats
    assert all(x['line']>0 and x['file'] in {m['path'] for m in r['inventory']['files']} for x in static)

@pytest.mark.integration
def test_real_graph_and_heuristics(native_report):
    engine,r=native_report
    assert ['include/comm.h','include/diagnostics.h'] in r['architecture']['cycles']
    rules={x['rule_id'] for x in r['findings'] if x['confidence_type']=='heuristic_indicator'}
    assert 'embedded.isr-suspicious-call' in rules and 'embedded.recursion-candidate' in rules
