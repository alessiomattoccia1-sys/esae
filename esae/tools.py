from pathlib import Path
import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET
import yaml
from .models import Finding, category
from .runner import run_tool
CHECKS = '-*,clang-analyzer-*,bugprone-sizeof-expression,bugprone-infinite-loop,bugprone-suspicious-memset-usage,bugprone-narrowing-conversions,cert-err34-c,portability-*'

def mapped_file(value: str, snap: Path, files: dict) -> str | None:
    p = Path(value)
    if not p.is_absolute(): p = snap / p
    try: rel = p.resolve().relative_to(snap.resolve()).as_posix()
    except ValueError: return None
    return rel if rel in files else None

def cppcheck_findings(xml: str, snap: Path, files: dict):
    findings, errors = [], []
    start = xml.find('<?xml')
    if start < 0: start = xml.find('<results')
    if start < 0: return [], ['Cppcheck did not produce XML diagnostics']
    doc = ET.fromstring(xml[start:])
    for item in doc.findall('./errors/error'):
        rule = item.get('id', 'unknown')
        if rule in ('syntaxError', 'preprocessorErrorDirective', 'internalError', 'configurationNotChecked', 'unknownMacro'):
            errors.append(rule + ': ' + item.get('msg', '')[:1000])
            continue  # Coverage/configuration failures are not source-code defects.
        locations = item.findall('location')
        location = next((x for x in locations if mapped_file(x.get('file', ''), snap, files)), None)
        if location is None:
            if rule not in ('checkersReport', 'missingIncludeSystem'): errors.append(rule + ': diagnostic has no captured source location')
            continue
        rel = mapped_file(location.get('file', ''), snap, files); severity = item.get('severity', 'information')
        evidence = {'analyzer_severity': severity, 'inconclusive': item.get('inconclusive') == 'true',
                    'trace': [{"file": mapped_file(x.get('file', ''), snap, files), "line": int(x.get('line', 0)), "info": x.get('info', '')} for x in locations]}
        findings.append(Finding(rel, int(location.get('line', 0)), int(location.get('column', 0)),
                                {'error': 'high', 'warning': 'medium', 'style': 'low', 'performance': 'low', 'portability': 'medium'}.get(severity, 'info'),
                                category(rule, item.get('msg', '')), rule, 'cppcheck', item.get('verbose') or item.get('msg', ''), evidence))
    return findings, errors

def clang_findings(data: dict, snap: Path, files: dict):
    findings, errors = [], []
    for item in data.get('Diagnostics', []) or []:
        message = item.get('DiagnosticMessage', {}); rel = mapped_file(message.get('FilePath', ''), snap, files); rule = item.get('DiagnosticName', 'unknown')
        if not rel:
            errors.append(rule + ': diagnostic outside captured sources (not imported)'); continue
        raw = files[rel].encode(); offset = max(0, min(int(message.get('FileOffset', 0)), len(raw)))
        line = raw[:offset].count(b'\n') + 1; column = offset - raw[:offset].rfind(b'\n'); description = message.get('Message', '')
        if rule == 'clang-diagnostic-error':
            errors.append(f'{rel}:{line}: {description}')
            continue  # A missing header/compiler error is a coverage failure, not a code defect.
        notes = [{'file': mapped_file(n.get('FilePath', ''), snap, files), 'message': n.get('Message', '')[:1500]} for n in item.get('Notes', [])]
        findings.append(Finding(rel, line, column, 'high' if item.get('Level') == 'Error' else 'medium', category(rule, description), rule, 'clang-tidy', description,
                                {'analyzer_level': item.get('Level', 'Warning'), 'notes': notes, 'suggested_replacements_not_applied': len(message.get('Replacements', []))}))
    return findings, errors

class Analyzers:
    def __init__(self, cppcheck: Path | None, clang_tidy: Path | None, work: Path):
        self.paths = {'cppcheck': cppcheck, 'clang-tidy': clang_tidy}; self.work = work; self.status = {}
        for name, p in self.paths.items():
            if not p:
                self.status[name] = {'available': False, 'error': 'Not installed/configured; see README installation'}; continue
            result = run_tool([str(p), '--version'], work / ('probe-' + name), timeout=10)
            available = result.returncode == 0 and not result.error
            self.status[name] = {'available': available, 'version': (result.stdout or result.stderr).strip()[:600],
                                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,
                                 'error': None if available else (result.error or result.stderr[:1000] or f'Version probe exited {result.returncode}; no output')}

    def analyze(self, snap: Path, files: dict, database: Path, entries: list, work: Path, timeout=45):
        findings, errors, executed = [], [], []
        deadline=time.monotonic()+300
        for name, status in self.status.items():
            if not status['available']:
                errors.append({'tool': name, 'file': None, 'error': status['error']}); continue
            exe = str(self.paths[name])
            if name == 'cppcheck':
                command = [exe, '--xml', '--xml-version=2', '--enable=warning,style,performance,portability', '--inconclusive', '--max-configs=12', '--max-ctu-depth=2', '--error-exitcode=0']
                command += ['--project=' + str(database / 'compile_commands.json')] if entries else [str(snap)]
                result = run_tool(command, work / name, timeout=timeout, read_roots=(snap, database))
                executed.append({'tool': name, 'translation_units': len(entries) or len([x for x in files if x.endswith(('.c', '.cpp', '.cc', '.cxx'))]), 'returncode': result.returncode, 'duration_seconds': result.duration, 'version': status['version']})
                if result.error or result.returncode: errors.append({'tool': name, 'file': None, 'error': result.error or result.stderr[-1500:]})
                try:
                    found, issues = cppcheck_findings(result.stderr, snap, files); findings += found
                    errors += [{'tool': name, 'file': None, 'error': x} for x in issues]
                except (ET.ParseError, ValueError) as e: errors.append({'tool': name, 'file': None, 'error': 'Malformed XML: ' + str(e)})
            else:
                for index, entry in enumerate(entries):
                    if time.monotonic()>=deadline:
                        errors.append({'tool':name,'file':None,'error':f'Total analysis budget (300s) reached; {len(entries)-index} translation units not analyzed'})
                        break
                    rel = Path(entry['file']).relative_to(snap).as_posix(); folder = work / name / str(index); folder.mkdir(parents=True, exist_ok=True)
                    fixes = folder / 'diagnostics.yml'
                    config = json.dumps({'Checks': CHECKS, 'WarningsAsErrors': '', 'HeaderFilterRegex': '.*', 'SystemHeaders': False, 'FormatStyle': 'none'})
                    command = [exe, entry['file'], '-p', str(database), '--config=' + config, '--export-fixes=' + str(fixes), '--quiet']
                    result = run_tool(command, folder, timeout=timeout, read_roots=(snap, database))
                    executed.append({'tool': name, 'file': rel, 'returncode': result.returncode, 'duration_seconds': result.duration, 'version': status['version']})
                    if result.error or result.returncode: errors.append({'tool': name, 'file': rel, 'error': result.error or result.stderr[-1500:]})
                    if fixes.exists():
                        if fixes.stat().st_size > 4_000_000:
                            errors.append({'tool': name, 'file': rel, 'error': 'Diagnostics size limit exceeded'}); continue
                        try:
                            found, issues = clang_findings(yaml.safe_load(fixes.read_text()) or {}, snap, files); findings += found
                            errors += [{'tool': name, 'file': rel, 'error': x} for x in issues]
                        except (yaml.YAMLError, ValueError, TypeError) as e: errors.append({'tool': name, 'file': rel, 'error': 'Malformed diagnostics: ' + str(e)})
        return findings, errors, executed
