from pathlib import Path
import json
import platform
import threading
import time
import uuid
import subprocess
from . import __version__
from .scanner import validate_root, inventory, snapshot, DEFAULT_EXCLUDES, InputError, read_regular
from .compilation import prepare_database
from .dependencies import graph
from .risks import analyze as risks
from .models import now, deduplicate
from .report import UNVERIFIABLE, summarize, html_report
from .storage import Store
from .tools import Analyzers, CHECKS
from .ai import explain, validate_ollama


class Engine:
    def __init__(self, root: Path, allowed: tuple[Path, ...], cppcheck=None, clang_tidy=None, ollama_url=None, ollama_model=None):
        self.root = root.resolve(); self.allowed = tuple(p.resolve(strict=True) for p in allowed)
        self.store = Store(self.root); self.lock = threading.Lock()
        self.analyzers = Analyzers(cppcheck, clang_tidy, self.root / 'startup')
        self.ollama_url = validate_ollama(ollama_url) if ollama_url else None
        self.ollama_model = ollama_model
        self.system_flags = []
        if platform.system() == 'Darwin':
            # Trusted operator host tool, never a compiler/program from a repository.
            sdk = subprocess.run(['/usr/bin/xcrun','--show-sdk-path'],capture_output=True,text=True,timeout=10)
            value=Path(sdk.stdout.strip())
            if sdk.returncode==0 and value.is_dir() and str(value.resolve()).startswith(('/Library/Developer/','/Applications/Xcode.app/')):
                self.system_flags=['-isysroot',str(value.resolve())]
                cxx=Path('/Library/Developer/CommandLineTools/usr/include/c++/v1')
                if cxx.is_dir():self.system_flags+=['-isystem',str(cxx)]

    def scan(self, path: str, excludes=DEFAULT_EXCLUDES, timeout=30, asynchronous=False):
        repository = validate_root(path, self.allowed)
        if not self.lock.acquire(blocking=False): raise InputError('A scan or AI review is already running; one operation at a time')
        scan_id = str(uuid.uuid4())
        report = {'id': scan_id, 'created_at': now(), 'repository': repository.name, 'version': __version__,
                  'status': 'running', 'phase': 'Inventario dei sorgenti', 'findings': [], 'errors': [], 'executed': [],
                  'configuration': {'excludes': list(excludes), 'per_process_timeout_seconds': timeout,
                                    'clang_checks': CHECKS, 'source_mode': 'private_readonly_snapshot',
                                    'network': 'denied_to_analyzers', 'platform': platform.system(),
                                    'os_sandbox': platform.system() == 'Darwin', 'ai': 'optional_explicit_local_only'},
                  'not_verified': UNVERIFIABLE}
        self.store.save(report)
        if asynchronous:
            threading.Thread(target=self._scan, args=(repository, report, excludes, timeout), daemon=True).start()
        else:
            self._scan(repository, report, excludes, timeout)
        return self.store.get(scan_id)

    def _scan(self, repository, report, excludes, timeout):
        started = time.monotonic(); folder = self.root / 'scans' / report['id']; snap = folder / 'source'
        try:
            inv = inventory(repository, excludes)
            report['inventory'] = inv.public(); snapshot(inv, snap)
            (folder / 'LIFECYCLE.json').write_text(json.dumps({'creator':'ESAE / owner-triggered scan','classification':'EVIDENCE','purpose':'Private bounded immutable source snapshot, logs and results','retention':'Until explicit owner retirement','deletion_condition':'Explicit authorized retirement only','scan_id':report['id']},indent=2))
            report['phase'] = 'Configurazione di compilazione'; self.store.save(report)
            entries, config_errors, ignored = prepare_database(inv, snap, folder / 'compilation',self.system_flags)
            report['configuration']['host_system_headers'] = bool(self.system_flags)
            report['configuration']['database_used'] = inv.database is not None
            report['configuration']['accepted_translation_units'] = len(entries)
            report['configuration']['cppcheck_configuration_scope'] = 'selected compilation configuration' if entries else 'standalone exploratory configurations'
            report['configuration']['ignored_compilation_arguments'] = ignored
            report['errors'] += [{'tool':'compilation', 'file':None, 'error':x} for x in config_errors]
            report['phase'] = 'Cppcheck e clang-tidy'; self.store.save(report)
            found, errors, executed = self.analyzers.analyze(snap, inv.files, folder / 'compilation', entries, folder / 'tools', timeout)
            report['errors'] += errors; report['executed'] = executed
            report['phase'] = 'Rischi embedded e dipendenze'; self.store.save(report)
            found += risks(inv.files)
            report['architecture'] = graph(inv.files)
            report['findings'] = [f.dict() for f in deduplicate(found, report['id'])]
            # Recheck originals without writing: tool execution was on the snapshot only.
            changed = []
            for meta in inv.metadata:
                import hashlib
                try: digest = hashlib.sha256(read_regular(repository / meta['path'], 2_000_000)).hexdigest()
                except (OSError, ValueError): digest = None
                if digest != meta['sha256']: changed.append(meta['path'])
            report['source_integrity'] = {'unchanged_after_scan': not changed, 'changed_paths':changed,
                                         'note':'Concurrent owner edits can change originals; reports always refer to captured hashes'}
            report['status'] = 'partial' if report['errors'] or not executed else 'completed'
            report['phase'] = 'Conclusa con limiti/errori espliciti' if report['errors'] else 'Scansione conclusa'
        except Exception as e:
            report['status'] = 'failed'; report['phase'] = 'Scansione non completata'
            report['errors'].append({'tool':'engine','file':None,'error':f'{type(e).__name__}: {str(e)[:1000]}'})
        finally:
            # Strip host paths from exported diagnostics. Raw private evidence stays local.
            def clean(value):
                if isinstance(value,str): return value.replace(str(snap),'<snapshot>').replace(str(repository),'<repository>').replace(str(folder),'<scan>')
                if isinstance(value,list): return [clean(x) for x in value]
                if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
                return value
            report = clean(report)
            report['duration_seconds'] = round(time.monotonic()-started,3); report['completed_at'] = now()
            report['summary'] = summarize(report['findings']); self.store.save(report)
            if folder.exists():
                (folder / 'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
                (folder / 'report.html').write_text(html_report(report))
            self.lock.release()

    def source(self, scan_id, file):
        report = self.store.get(scan_id)
        allowed = {f['path'] for f in (report or {}).get('inventory',{}).get('files',[])}
        if file not in allowed: raise InputError('File is not part of the captured inventory')
        p = self.root / 'scans' / scan_id / 'source' / file
        return read_regular(p,2_000_000).decode('utf-8')

    def explain(self, scan_id, finding_id):
        if not self.ollama_url or not self.ollama_model: raise InputError('Ollama is not configured; core analysis remains available')
        if not self.lock.acquire(blocking=False): raise InputError('A scan or AI review is already running')
        try:
            report = self.store.get(scan_id)
            if not report: raise InputError('Unknown scan')
            finding = next((f for f in report['findings'] if f['id']==finding_id),None)
            if not finding: raise InputError('Unknown finding')
            finding['ai_explanation'] = explain(finding, self.source(scan_id,finding['file']), self.ollama_url,self.ollama_model)
            report['summary'] = summarize(report['findings']); self.store.save(report)
            folder = self.root/'scans'/scan_id
            (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            (folder/'report.html').write_text(html_report(report))
            return finding['ai_explanation']
        finally: self.lock.release()
