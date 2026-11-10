# Copyright 2026 Alessio Mattoccia
from pathlib import Path
import json
import sqlite3
import threading

class Store:
    def __init__(self, root: Path):
        self.root = root.resolve(); self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / 'esae.sqlite3'; self.lock = threading.Lock()
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS scans (id TEXT PRIMARY KEY, created TEXT NOT NULL, status TEXT NOT NULL, report TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, file TEXT, line INTEGER, severity TEXT, confidence_type TEXT, record TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS findings_scan ON findings(scan_id)')
        self.path.chmod(0o600)
        # A process stopped mid-scan is recorded honestly; no job replay on restart.
        with self.connect() as db:
            rows = db.execute("SELECT id, report FROM scans WHERE status='running'").fetchall()
            for scan_id, raw in rows:
                report = json.loads(raw); report['status'] = 'interrupted'; report['phase'] = 'Interrotta alla chiusura del processo; avvia una nuova scansione'
                db.execute('UPDATE scans SET status=?, report=? WHERE id=?', ('interrupted', json.dumps(report), scan_id))

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def save(self, report: dict):
        with self.lock, self.connect() as db:
            db.execute('INSERT OR REPLACE INTO scans VALUES (?,?,?,?)', (report['id'], report['created_at'], report['status'], json.dumps(report)))
            for f in report.get('findings', []):
                db.execute('INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?,?,?)', (f['id'], report['id'], f['file'], f['line'], f['severity'], f['confidence_type'], json.dumps(f)))

    def get(self, scan_id: str):
        with self.connect() as db:
            row = db.execute('SELECT report FROM scans WHERE id=?', (scan_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self):
        with self.connect() as db:
            rows = db.execute('SELECT report FROM scans ORDER BY created DESC LIMIT 100').fetchall()
        return [{k: r.get(k) for k in ['id', 'created_at', 'repository', 'status', 'phase', 'duration_seconds', 'summary']} for r in map(lambda row: json.loads(row[0]), rows)]
