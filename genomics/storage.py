# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Local normalized genomic evidence, separate from the existing ESAE database."""
import json
from research_core.jobs import JobStore

class GenomicStore(JobStore):
    def __init__(self,root):
        super().__init__(root)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS variants(job_id TEXT,id TEXT,gene TEXT,classification TEXT,review TEXT,conditions TEXT,data TEXT,PRIMARY KEY(job_id,id))')
            db.execute('CREATE TABLE IF NOT EXISTS submissions(job_id TEXT,variant_id TEXT,accession TEXT,submitter_id TEXT,condition_key TEXT,data TEXT,PRIMARY KEY(job_id,variant_id,accession))')
            db.execute('CREATE TABLE IF NOT EXISTS datasets(job_id TEXT,source_id TEXT,data TEXT,PRIMARY KEY(job_id,source_id))')
            db.execute('CREATE INDEX IF NOT EXISTS variants_filter ON variants(job_id,gene,classification,review)')
            db.execute('CREATE INDEX IF NOT EXISTS submissions_condition ON submissions(job_id,variant_id,condition_key)')
    def variant(self,job_id,value):
        conditions='; '.join(c.get('name','') for r in value['rcvs'] for c in r['conditions'])
        with self.lock,self.connect() as db:
            db.execute('INSERT OR REPLACE INTO variants VALUES(?,?,?,?,?,?,?)',(job_id,value['variation_id'],','.join(g['symbol'] for g in value['genes']),value['germline']['description'],value['germline']['review_status'],conditions,json.dumps(value,ensure_ascii=False)))
            db.execute('DELETE FROM submissions WHERE job_id=? AND variant_id=?',(job_id,value['variation_id']))
            for s in value['submissions']:db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?)',(job_id,value['variation_id'],s['accession'],s['submitter_id'],s['condition_key'],json.dumps(s,ensure_ascii=False)))
    def source(self,job_id,source):
        with self.lock,self.connect() as db:db.execute('INSERT OR REPLACE INTO datasets VALUES(?,?,?)',(job_id,source['id'],json.dumps(source,ensure_ascii=False)))
    def sources(self,job_id):
        with self.connect() as db:rows=db.execute('SELECT data FROM datasets WHERE job_id=? ORDER BY source_id',(job_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def variants(self,job_id,*,gene='',classification='',review='',condition='',offset=0,limit=200):
        query='SELECT data FROM variants WHERE job_id=?';args=[job_id]
        for col,value,exact in [('gene',gene,True),('classification',classification,False),('review',review,False),('conditions',condition,False)]:
            if value:
                if len(value)>200:raise ValueError('Filter length exceeded')
                query+=' AND '+col+(' = ?' if exact else ' LIKE ?');args.append(value if exact else '%'+value+'%')
        query+=' ORDER BY CAST(id AS INTEGER) LIMIT ? OFFSET ?';args.extend([min(limit,500),max(offset,0)])
        with self.connect() as db:rows=db.execute(query,args).fetchall()
        return [json.loads(r[0]) for r in rows]
    def get_variant(self,job_id,vid):
        with self.connect() as db:row=db.execute('SELECT data FROM variants WHERE job_id=? AND id=?',(job_id,vid)).fetchone()
        return json.loads(row[0]) if row else None
