from html import escape
import json

UNVERIFIABLE = ['Worst-Case Execution Time (WCET)', 'Absence of race conditions', 'Functional correctness on hardware',
                'MISRA, CERT, DO-178C, ISO 26262 or other standard compliance/certification',
                'Absence of all defects/security vulnerabilities', 'Complete call graph or AST-based dataflow']

def summarize(findings: list[dict]):
    static = [f for f in findings if f['confidence_type'] == 'static_analysis']
    heuristic = [f for f in findings if f['confidence_type'] == 'heuristic_indicator']
    return {'static_findings': len(static), 'heuristic_indicators': len(heuristic),
            'ai_explanations': sum(f.get('ai_explanation', {}).get('status') == 'generated' for f in findings if f.get('ai_explanation')),
            'static_by_severity': {s: sum(f['severity'] == s for f in static) for s in ['high','medium','low','info']},
            'total_findings': len(findings)}

def html_report(report: dict) -> str:
    esc = lambda x: escape(str(x))
    inv = report.get('inventory', {})
    rows = ''
    for f in report.get('findings', []):
        ai = f.get('ai_explanation')
        ai_html = '<aside><b>AI hypothesis — not verified</b><pre>' + esc(json.dumps(ai, ensure_ascii=False, indent=2)) + '</pre></aside>' if ai else ''
        rows += ('<article><p class="eyebrow">' + esc(f['confidence_type']) + ' / ' + esc(f['severity']) + '</p><h3>' + esc(f['file']) + ':' + esc(f['line']) + '</h3><p>' + esc(f['message']) + '</p><p class="meta">' + esc(f['source_tool']) + ' · ' + esc(f['rule_id']) + ' · ' + esc(f['verification_status']) + '</p><details><summary>Evidence / all tool reports</summary><pre>' + esc(json.dumps(f['tool_reports'], ensure_ascii=False, indent=2)) + '</pre></details>' + ai_html + '</article>')
    errors = ''.join('<li>' + esc(json.dumps(e, ensure_ascii=False)) + '</li>' for e in report.get('errors', [])) or '<li>No tool errors recorded</li>'
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>ESAE · Scan ' + esc(report['id']) + '</title><style>body{font:16px/1.65 system-ui;background:#f6f5f1;color:#14252e;margin:0 auto;max-width:1050px;padding:48px 24px}h1{font-size:44px;line-height:1.1}h2{margin-top:48px}.eyebrow,.meta{color:#536773;font-size:13px}article{background:white;border:1px solid #d7dfe0;padding:24px;margin:16px 0;border-radius:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.stats{padding:20px;background:#e2edef;border-radius:14px}.notice{border-left:3px solid #c18c42;padding:0 20px}@media print{body{padding:12px}article{break-inside:avoid}details{display:block}}</style><header><p class="eyebrow">MATTOCCIA LABS / ENGINEERING EVIDENCE</p><h1>Embedded Software<br>Analysis Engine.</h1><p>Experimental local prototype · v0.1.0</p></header><div class="stats"><b>Scan ' + esc(report['id']) + '</b><p>' + esc(report['created_at']) + ' · ' + esc(report.get('repository','')) + ' · ' + esc(report['status']) + '</p><p>' + esc(inv.get('file_count',0)) + ' captured source files · ' + esc(inv.get('lines',0)) + ' physical lines · ' + esc(report.get('duration_seconds',0)) + ' s</p><pre>' + esc(json.dumps(report.get('summary',{}), indent=2)) + '</pre></div><p class="notice">Tool-reported diagnostics require engineering review. Heuristics are risk indicators. AI text is an unverified hypothesis. No source modification, hardware execution or certification.</p><h2>Executed tools and configuration</h2><pre>' + esc(json.dumps({'configuration':report.get('configuration'), 'executed':report.get('executed',[])},ensure_ascii=False,indent=2)) + '</pre><h2>Analysis errors and coverage limitations</h2><ul>' + errors + '</ul><h2>Findings</h2>' + (rows or '<p>No diagnostics reported; this does not prove the absence of defects.</p>') + '<h2>Not verified</h2><ul>' + ''.join('<li>' + esc(x) + '</li>' for x in report.get('not_verified',UNVERIFIABLE)) + '</ul></html>')
