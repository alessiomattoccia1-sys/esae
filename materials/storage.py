# SPDX-License-Identifier: Apache-2.0
import json
from research_core.jobs import JobStore
class MaterialsStore(JobStore):
    def __init__(self,root):
        super().__init__(root)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS materials(job_id TEXT,jid TEXT,formula TEXT,gap REAL,hull REAL,slme REAL,elements TEXT,family TEXT,data TEXT,PRIMARY KEY(job_id,jid))')
            db.execute('CREATE INDEX IF NOT EXISTS material_filters ON materials(job_id,gap,hull,slme)')
    def batch(self,job_id,values):
        with self.lock,self.connect() as db:db.executemany('INSERT OR REPLACE INTO materials VALUES(?,?,?,?,?,?,?,?,?)',[(job_id,r['jid'],r['formula'],r['properties']['gap_mbj'],r['properties']['hull_ev_atom'],r['properties']['slme_percent'],'|'+ '|'.join(r['elements'])+'|',r['chemical_family'],json.dumps(r,allow_nan=False)) for r in values])
    def get_material(self,job_id,jid):
        with self.connect() as db:row=db.execute('SELECT data FROM materials WHERE job_id=? AND jid=?',(job_id,jid)).fetchone()
        return json.loads(row[0]) if row else None
    def iter_analysis(self,job_id):
        with self.connect() as db:
            cursor=db.execute('SELECT data FROM materials WHERE job_id=? ORDER BY CAST(SUBSTR(jid,7) AS INTEGER)',(job_id,))
            for row in cursor:
                r=json.loads(row[0]);structure=r.pop('structure');r['structure_sha256']=structure['sha256'];r['cell_atoms']=structure['atoms'];r['cell_volume_angstrom3']=structure['volume_angstrom3'];yield r
    def explorer(self,job_id,query='',element='',gap_min=None,gap_max=None,hull_max=None,slme_min=None,sort='jid',offset=0,limit=100):
        columns={'jid':'CAST(SUBSTR(jid,7) AS INTEGER)','gap':'gap','hull':'hull','slme':'slme DESC','formula':'formula'}
        if sort not in columns or len(query)>120 or len(element)>2:raise ValueError('Invalid explorer filter')
        sql=' FROM materials WHERE job_id=?';args=[job_id]
        if query:sql+=' AND (jid LIKE ? OR formula LIKE ?)';args.extend(['%'+query+'%']*2)
        if element:sql+=' AND elements LIKE ?';args.append('%|'+element+'|%')
        for col,op,value in [('gap','>=',gap_min),('gap','<=',gap_max),('hull','<=',hull_max),('slme','>=',slme_min)]:
            if value is not None:sql+=' AND '+col+op+'?';args.append(value)
        with self.connect() as db:
            count=db.execute('SELECT COUNT(*)'+sql,args).fetchone()[0];rows=db.execute('SELECT data'+sql+' ORDER BY '+columns[sort]+',jid LIMIT ? OFFSET ?',args+[min(500,max(1,limit)),max(0,offset)]).fetchall()
        out=[]
        for row in rows:
            r=json.loads(row[0]);structure=r.pop('structure');r['cell_atoms']=structure['atoms'];r['structure_sha256']=structure['sha256'];out.append(r)
        return {'total':count,'offset':offset,'items':out}
