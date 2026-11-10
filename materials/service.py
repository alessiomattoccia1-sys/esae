# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Persistent local acquisition, scientific screening and raw-source replay."""
from pathlib import Path
import json,threading,time,hashlib,importlib.metadata,sys
from collections import Counter
from dataclasses import asdict
from research_core import now,validate_ollama
from research_core.locking import OperationLock
from .storage import MaterialsStore
from .connectors import JarvisConnector,cache_at,parse_record_page
from .parser import records,normalize,composition,PARSER_VERSION,UNITS
from .analysis import ScreeningConfig,analyze
from .report import html_report,candidates_csv,methodology

class MaterialsEngine:
    def __init__(self,root,*,ollama_url=None,ollama_model=None,max_download_bytes=200_000_000):
        self.store=MaterialsStore(root);self.root=self.store.root;self.lock=OperationLock(self.root/'active.lock');self.max_download=max_download_bytes;self.ollama_url=validate_ollama(ollama_url) if ollama_url else None;self.ollama_model=ollama_model
    def phase(self,job,name,completed=0,planned=0):job.update(phase=name,progress={'completed':completed,'planned':planned});self.store.save(job)
    def run(self,config=None,*,asynchronous=False,resume=None):
        config=(config or ScreeningConfig()).validate()
        if not self.lock.acquire(False):raise ValueError('A materials operation is already active')
        try:
            if resume:
                job=self.store.get(resume)
                if not job or job['status'] not in ('interrupted','failed','partial'):raise ValueError('Only an incomplete job can resume')
                config=ScreeningConfig(**job['parameters']).validate();job['status']='running';self.store.save(job)
            else:job=self.store.create('materials',asdict(config))
            folder=self.root/'jobs'/job['id'];folder.mkdir(parents=True,exist_ok=True)
            if asynchronous:threading.Thread(target=self.execute,args=(job,config),daemon=True).start();return job
            self.execute(job,config);return self.store.get(job['id'])
        except BaseException:self.lock.release();raise
    def ingest(self,path,job=None):
        counts={'records_seen':0,'valid_unique':0,'invalid_records':0,'duplicates':0,'invalid_reasons':{},'property_anomalies':{}};invalid=Counter();anomalies=Counter();seen={};batch=[];values=[]
        for raw in records(path):
            counts['records_seen']+=1
            try:r=normalize(raw)
            except (ValueError,TypeError,KeyError,OverflowError) as exc:counts['invalid_records']+=1;invalid[str(exc)[:100]]+=1;continue
            digest=hashlib.sha256(json.dumps(r,sort_keys=True,allow_nan=False).encode()).hexdigest()
            if r['jid'] in seen:
                if seen[r['jid']]!=digest:raise ValueError('Conflicting duplicate JARVIS identity: '+r['jid'])
                counts['duplicates']+=1;continue
            seen[r['jid']]=digest;counts['valid_unique']+=1;anomalies.update(r['anomalies'])
            if job:
                batch.append(r)
                if len(batch)>=500:self.store.batch(job['id'],batch);batch=[];self.phase(job,'Normalizing and indexing crystals',counts['records_seen'],0)
            else:
                structure=r.pop('structure');r.update(structure_sha256=structure['sha256'],cell_atoms=structure['atoms'],cell_volume_angstrom3=structure['volume_angstrom3']);values.append(r)
        if job and batch:self.store.batch(job['id'],batch)
        counts['invalid_reasons']=dict(sorted(invalid.items()));counts['property_anomalies']=dict(sorted(anomalies.items()));return counts,values
    def source_checks(self,path,ranked):
        import os
        os.environ.setdefault('MPLCONFIGDIR',str(self.root/'matplotlib-cache'))
        from jarvis.core.atoms import Atoms
        selected={r['jid']:r for r in (ranked['optical'] or ranked['stability'] or ranked['gap_only'])[:6]};checks=[]
        for index,raw in enumerate(records(path)):
            if raw.get('jid') not in selected:continue
            expected=selected[raw['jid']];parsed=normalize(raw);atoms=Atoms.from_dict(raw['atoms']);comp=dict(atoms.composition.to_dict());total=sum(comp.values());structure_match=abs(atoms.volume-parsed['structure']['volume_angstrom3'])<=1e-7*max(1,atoms.volume) and all(abs(comp[e]/total-parsed['composition'][e])<1e-9 for e in comp)
            passed=parsed['formula']==expected['formula'] and parsed['properties']==expected['properties'] and structure_match
            checks.append({'jid':raw['jid'],'source_array_index':index,'formula_matches':parsed['formula']==expected['formula'],'all_whitelisted_properties_match':parsed['properties']==expected['properties'],'jarvis_tools_independent_geometry_and_composition':structure_match,'units':UNITS,'method':parsed['methods'],'passed':passed,'scope':'Original archive record round-trip plus JARVIS-library crystal check; not a second database or independent physical validation','source_url':expected['url']})
            if len(checks)==len(selected):break
        if len(checks)!=len(selected) or any(not c['passed'] for c in checks):raise ValueError('Candidate source-level verification failed')
        return checks
    def external_checks(self,ranked):
        checks=[];connector=JarvisConnector(cache_at(self.root/'detail-cache',self.max_download))
        for r in (ranked['optical'] or ranked['stability'] or ranked['gap_only'])[:3]:
            try:
                raw,source=connector.detail(r['jid']);view=parse_record_page(raw)
                if view['jid']!=r['jid']:raise ValueError('Official detail identity mismatch')
                formula_match=composition(view['formula'])[1]==r['composition'];gap_delta=abs(view['mbj_gap_ev']-r['properties']['gap_mbj']) if view['mbj_gap_ev'] is not None else None;slme_delta=abs(view['slme_percent']-r['properties']['slme_percent']) if view['slme_percent'] is not None and r['properties']['slme_percent'] is not None else None
                checks.append({'jid':r['jid'],'status':'acquired','source':source,'page_fields':view,'snapshot_gap_ev':r['properties']['gap_mbj'],'snapshot_slme_percent':r['properties']['slme_percent'],'formula_equivalent':formula_match,'gap_absolute_difference_ev':gap_delta,'slme_absolute_difference_percentage_points':slme_delta,'reported_slme_differs':slme_delta is not None and slme_delta>.01,'scope':'Same-provider rendering cross-check, not an independent database. Page version unspecified; differences cannot be attributed to a cause from available metadata.'})
            except Exception as exc:checks.append({'jid':r['jid'],'status':'unavailable','error':str(exc)[:300]})
        return checks
    def execute(self,job,config):
        start=time.monotonic();folder=self.root/'jobs'/job['id']
        try:
            self.phase(job,'Acquiring pinned official JARVIS snapshot');path,dataset=JarvisConnector(cache_at(self.root/'cache',self.max_download)).acquire();(folder/'dataset.json').write_text(json.dumps(dataset,indent=2)+'\n')
            ingestion,_=self.ingest(path,job);self.phase(job,'Computing distributions, rankings and sensitivity');rows=list(self.store.iter_analysis(job['id']))
            if len(rows)!=ingestion['valid_unique']:raise ValueError('Stored material count differs from import')
            report,ranked=analyze(rows,config,ingestion);self.phase(job,'Verifying original candidate records');checks=self.source_checks(path,ranked);external=self.external_checks(ranked);report.update(external_detail_checks=external,dataset=dataset,ingestion=ingestion,detail_checks=checks,created_at=job['created_at'],completed_at=now(),duration_seconds=round(time.monotonic()-start,3))
            software={x:importlib.metadata.version(x) for x in ['numpy','scipy','jarvis-tools','fastapi']};software['python']=sys.version.split()[0]
            manifest={'experiment':'MDE-001','engine_version':'0.1.0','parser_version':PARSER_VERSION,'method_version':report['method_version'],'dataset':dataset,'configuration':asdict(config),'ingestion':ingestion,'software':software,'analysis_sha256':report['analysis_sha256'],'units':UNITS,'json_nonfinite_policy':'Official Python-compatible NaN/Infinity constants parsed as missing, never zero','source_checks':checks,'external_detail_checks':external,'source_code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},'data_license':'CC BY4.0; NIST JARVIS / Kamal Choudhary et al.; normalization/screening are modifications','original_software_license':'Apache-2.0','duration_seconds':report['duration_seconds'],'errors':[]}
            artifacts={'MDE-001_RESULTS.json':json.dumps(report,indent=2,allow_nan=False)+'\n','MDE-001_REPORT.html':html_report(report),'MDE-001_CANDIDATES.csv':candidates_csv(ranked),'MDE-001_MANIFEST.json':json.dumps(manifest,indent=2)+'\n','MDE-001_METHODOLOGY.md':methodology(asdict(config))}
            for name,value in artifacts.items():(folder/name).write_text(value)
            job.update(status='completed',phase='MDE-001 completed',completed_at=report['completed_at'],duration_seconds=report['duration_seconds'],summary=report['metrics'],analysis_sha256=report['analysis_sha256'],progress={'completed':ingestion['records_seen'],'planned':ingestion['records_seen']},errors=[])
        except Exception as exc:job.update(status='failed',phase='Experiment not completed',completed_at=now(),duration_seconds=round(time.monotonic()-start,3),errors=[str(exc)[:600]])
        finally:self.store.save(job);self.lock.release()
    def report(self,job_id):
        job=self.store.get(job_id)
        if not job:raise ValueError('Unknown materials job')
        path=self.root/'jobs'/job['id']/'MDE-001_RESULTS.json'
        if not path.is_file():raise ValueError('Results not ready')
        return json.loads(path.read_text())
    def verify(self,job_id):
        report=self.report(job_id);path,dataset=JarvisConnector(cache_at(self.root/'cache',self.max_download)).acquire(offline=True)
        if dataset['source']['sha256']!=report['dataset']['source']['sha256']:raise ValueError('Dataset source hash changed')
        for check in report.get('external_detail_checks',[]):
            if check['status']=='acquired':
                _,source=cache_at(self.root/'detail-cache',self.max_download).fetch(check['source']['url'],offline=True)
                if source['sha256']!=check['source']['sha256']:raise ValueError('Detail source changed')
        ingestion,rows=self.ingest(path);fresh,_=analyze(rows,ScreeningConfig(**report['configuration']),ingestion);passed=fresh['analysis_sha256']==report['analysis_sha256'] and ingestion==report['ingestion'];return {'passed':passed,'network_used':False,'materials_reparsed':len(rows),'records_reparsed':ingestion['records_seen'],'source_sha256':dataset['source']['sha256'],'analysis_sha256':fresh['analysis_sha256'],'expected':report['analysis_sha256'],'verified_at':now()}
