# SPDX-License-Identifier: Apache-2.0
"""Persistent local research jobs; domain results stay in their own schema."""
import json,sqlite3,threading,uuid
from pathlib import Path
from contextlib import contextmanager
from esae.scanner import no_symlink
from . import now
from .locking import OperationLock

class JobStore:
    def __init__(self,root):
        self.root=no_symlink(Path(root)).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=self.root/'research.sqlite3';no_symlink(self.path);self.lock=threading.RLock()
        lease=OperationLock(self.root/'active.lock');recover=lease.acquire(False)
        try:
            with self.connect() as db:
                db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, created TEXT, status TEXT, data TEXT)')
                for row in db.execute("SELECT id,data FROM jobs WHERE status='running'").fetchall() if recover else []:
                    item=json.loads(row[1]);item.update(status='interrupted',phase='Process stopped; resume explicitly')
                    db.execute('UPDATE jobs SET status=?,data=? WHERE id=?',('interrupted',json.dumps(item),row[0]))
            self.path.chmod(0o600)
        finally:
            if recover:lease.release()
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=20)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            with db:yield db
        finally:db.close()
    def save(self,item):
        with self.lock,self.connect() as db:db.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?,?)',(item['id'],item['created_at'],item['status'],json.dumps(item,ensure_ascii=False)))
    def create(self,engine,parameters):
        item={'id':str(uuid.uuid4()),'engine':engine,'created_at':now(),'status':'running','phase':'Preparing','progress':{'completed':0,'planned':0},'parameters':parameters,'errors':[],'sources':[]}
        self.save(item);return item
    def get(self,job_id):
        job_id=str(uuid.UUID(job_id))
        with self.connect() as db:row=db.execute('SELECT data FROM jobs WHERE id=?',(job_id,)).fetchone()
        return json.loads(row[0]) if row else None
    def list(self):
        with self.connect() as db:rows=db.execute('SELECT data FROM jobs ORDER BY created DESC LIMIT 100').fetchall()
        return [json.loads(row[0]) for row in rows]
