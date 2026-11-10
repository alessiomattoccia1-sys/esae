# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Resumable local public-source experiment orchestration, no cloud backend."""
from pathlib import Path
import json,threading,time,hashlib
from collections import Counter
from research_core import now,validate_ollama
from research_core.http import PublicCache
from research_core.locking import OperationLock
from .storage import GenomicStore
from .connectors import ClinVar,Ensembl
from .parsers import parse_vcv,parse_rcv,PARSER_VERSION
from .analysis import analyze,variant_evidence
from .report import html_report

class GenomicsEngine:
    def __init__(self,root,*,ollama_url=None,ollama_model=None,max_download_bytes=200_000_000):
        self.store=GenomicStore(Path(root));self.root=self.store.root;self.lock=OperationLock(self.root/'active.lock');self.max_download=max_download_bytes
        self.ollama_url=validate_ollama(ollama_url) if ollama_url else None;self.ollama_model=ollama_model
    def run(self,genes=('BRCA1','BRCA2'),per_gene=40,ensembl_limit=12,detail_limit=6,asynchronous=False,resume=None):
        if not genes or len(genes)>2 or any(g not in ('BRCA1','BRCA2') for g in genes):raise ValueError('GEE-001 v0.1 accepts public BRCA1/BRCA2 genes only')
        if not 1<=per_gene<=100 or not 0<=ensembl_limit<=30 or not 0<=detail_limit<=12:raise ValueError('Experiment limits exceeded')
        if not self.lock.acquire(False):raise ValueError('A research job is already active')
        try:
            if resume:
                job=self.store.get(resume)
                if not job or job['status'] not in ('interrupted','failed','partial'):raise ValueError('Only incomplete jobs can resume')
                folder=self.root/'jobs'/job['id'];history=folder/'attempt-history'
                history.mkdir(parents=True,exist_ok=True)
                for name in ('report.json','report.html','manifest.json'):
                    source=folder/name
                    if source.exists():
                        raw=source.read_bytes();dest=history/(hashlib.sha256(raw).hexdigest()+'-'+name)
                        if not dest.exists():dest.write_bytes(raw)
                job.update(status='running',errors=[]);self.store.save(job)
            else:job=self.store.create('genomics',{'genes':sorted(set(genes)),'per_gene':per_gene,'ensembl_limit':ensembl_limit,'detail_limit':detail_limit,'public_only':True})
        except BaseException:self.lock.release();raise
        if asynchronous:threading.Thread(target=self._run,args=(job,),daemon=True).start()
        else:self._run(job)
        return self.store.get(job['id'])
    def _phase(self,job,phase,completed=0,planned=0):
        job.update(phase=phase,progress={'completed':completed,'planned':planned});self.store.save(job)
    def _source(self,job,source,counts=None):
        value={**source,'record_counts':counts};self.store.source(job['id'],value);return value
    def _run(self,job):
        started=time.monotonic();folder=self.root/'jobs'/job['id'];folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        cache=PublicCache(folder/'cache',max_bytes=self.max_download);clin=ClinVar(cache);ens=Ensembl(cache)
        errors=[];excluded=Counter();variants=[];parameters=job['parameters'];gene_info={};info=None
        try:
            if 'selection' not in job:
                searches={};selected=[]
                for gene in parameters['genes']:
                    self._phase(job,'Searching official ClinVar index: '+gene)
                    ids,search=clin.search(gene);chosen=ids[:parameters['per_gene']]
                    self._source(job,search['source'],{'examined_query_ids':len(ids),'selected':len(chosen),'not_selected':len(ids)-len(chosen),'invalid':0})
                    searches[gene]={'query':search['query'],'available_ids':len(ids),'selected_ids':chosen,'not_selected':len(ids)-len(chosen),'source_id':search['source']['id']};selected+=chosen
                selection={'genes':parameters['genes'],'rule':'First N unique numeric ascending Variation IDs per official gene AND single_gene query; selected before classifications are fetched','per_gene_requested':parameters['per_gene'],'searches':searches,'selected_unique_ids':sorted(set(selected)),'sample_type':'deterministic_nonrandom_not_prevalence_estimate'}
                job['selection']=selection;self.store.save(job)
            selection=job['selection'];ids=selection['selected_unique_ids'];job['exclusions']={}
            for i,vid in enumerate(ids):
                self._phase(job,'Importing VCV '+str(vid),i,len(ids))
                try:
                    raw,source=clin.vcv(vid);records=parse_vcv(raw)
                    if len(records)!=1 or records[0]['variation_id']!=str(vid):raise ValueError('Requested/returned VCV identity mismatch')
                    v=records[0];symbols={g['symbol'] for g in v['genes']}
                    if len(symbols)!=1 or not symbols.intersection(parameters['genes']):
                        excluded['outside_single_gene_scope']+=1;self._source(job,source,{'examined':1,'imported':0,'excluded':1,'reason':'outside_single_gene_scope'});continue
                    v['source_id']=source['id'];v['source_sha256']=source['sha256'];v['ensembl']={'status':'not_selected','reason':'Bounded annotation subset'}
                    self.store.variant(job['id'],v);variants.append(v)
                    self._source(job,source,{'examined':1,'imported':1,'excluded':0,'invalid':0,'rcv_records':len(v['rcvs']),'current_germline_scv_records':len(v['submissions']),'excluded_scv_records':v['excluded_submission_records']})
                except ValueError as exc:
                    if str(exc).startswith(('Unsupported haplotype/included/nonclassified record:','Unsupported non-current record:')):
                        excluded['unsupported_record_type']+=1
                        self._source(job,source,{'examined':1,'imported':0,'excluded':1,'reason':'unsupported_record_type'})
                    else:errors.append({'source':'ClinVar','variation_id':str(vid),'error':str(exc)[:400]});excluded['invalid_or_unusable_vcv']+=1
                except Exception as exc:errors.append({'source':'ClinVar','variation_id':str(vid),'error':str(exc)[:400]});excluded['acquisition_failure']+=1
            self._phase(job,'VCV import completed',len(ids),len(ids))
            if not variants:raise ValueError('No compatible real variants; experiment cannot be completed')
            if parameters['ensembl_limit']:
                try:
                    info,source=ens.metadata();self._source(job,source,{'metadata_records':1})
                    for gene in parameters['genes']:
                        value,source=ens.gene(gene);gene_info[gene]=value;self._source(job,source,{'gene_records':1})
                except Exception as exc:errors.append({'source':'Ensembl','error':str(exc)[:400]})
            attempted=0
            eligible={g:[] for g in parameters['genes']}
            for v in variants:
                if any(l['assembly']=='GRCh38' and l['position'] and l['reference'] in ('A','C','G','T') and l['alternate'] in ('A','C','G','T') for l in v['locations']):
                    for g in v['genes']:
                        if g['symbol'] in eligible:eligible[g['symbol']].append(v['variation_id'])
            targets=[]
            for i in range(max([len(x) for x in eligible.values()] or [0])):
                for gene in parameters['genes']:
                    if i<len(eligible[gene]) and len(targets)<parameters['ensembl_limit']:targets.append(eligible[gene][i])
            selection['ensembl_selection_rule']='Round-robin by gene, ascending selected Variation ID among exact GRCh38 SNVs; fixed limit before VEP responses'
            selection['ensembl_selected_ids']=targets
            for v in variants:
                locations=[l for l in v['locations'] if l['assembly']=='GRCh38' and l['position'] and l['reference'] in ('A','C','G','T') and l['alternate'] in ('A','C','G','T')]
                if not locations:v['ensembl']={'status':'incompatible','reason':'No exact GRCh38 SNV VCF representation; no coordinate guessing or lift-over'};self.store.variant(job['id'],v);continue
                if v['variation_id'] not in targets:continue
                attempted+=1;self._phase(job,'Exact Ensembl VEP annotation',attempted,parameters['ensembl_limit'])
                try:
                    annotation=ens.vep_snv(locations[0]);expected={gene_info[g['symbol']]['id'] for g in v['genes'] if g['symbol'] in gene_info}
                    observed={t['gene_id'] for t in annotation['transcripts']}
                    if not expected or not expected.intersection(observed):raise ValueError('Coordinate-matched VEP lacks the independently resolved gene ID')
                    annotation['release']=info;annotation['verified_gene_ids']=sorted(expected.intersection(observed));v['ensembl']=annotation
                    self._source(job,annotation['source'],{'examined':1,'matched':1,'invalid':0})
                except Exception as exc:v['ensembl']={'status':'failed','error':str(exc)[:400]};errors.append({'source':'Ensembl','variation_id':v['variation_id'],'error':str(exc)[:400]})
                self.store.variant(job['id'],v)
            detailed=0
            for v in sorted(variants,key=lambda x:(not variant_evidence(x)['same_condition_difference'],int(x['variation_id']))):
                if detailed>=parameters['detail_limit']:break
                analysis=variant_evidence(v);groups=[g for g in analysis['same_condition_comparisons'] if g['major_difference']]
                targets=list(dict.fromkeys(r for g in groups for r in g['rcvs']))
                if not targets and analysis['official_aggregate_conflict']:targets=[r['accession'] for r in v['rcvs'][:1]]
                for target in targets[:2]:
                    if detailed>=parameters['detail_limit']:break
                    detailed+=1;self._phase(job,'Checking versioned RCV detail',detailed,parameters['detail_limit'])
                    try:
                        raw,source=clin.rcv(target);records=parse_rcv(raw);match=next((x for x in records if x['accession']==target),None)
                        if not match:raise ValueError('RCV accession/version mismatch')
                        summary=next(r for r in v['rcvs'] if r['accession']==target)
                        check={'accession':target,'summary_classification':summary['germline']['description'],'detail_classification':match['germline']['description'],'same_classification':summary['germline']['description']==match['germline']['description'],'detail_scv_count':len(match['scvs']),'source_id':source['id'],'url':match['url']}
                        v.setdefault('rcv_detail_checks',[]).append(check);self._source(job,source,{'rcv_records':len(records),'matched_versioned_rcv':1})
                        if not check['same_classification']:errors.append({'source':'RCV verification','accession':target,'error':'VCV condition summary and versioned RCV classification differ'})
                    except Exception as exc:errors.append({'source':'RCV','accession':target,'error':str(exc)[:400]})
                self.store.variant(job['id'],v)
            self._phase(job,'Deterministic evidence correlation')
            report=analyze(variants,selection,errors)
            report.update(created_at=job['created_at'],completed_at=now(),sources=self.store.sources(job['id']),exclusions={'selected_variants':len(ids),'imported_variants':len(variants),'excluded_variants':sum(excluded.values()),'reasons':dict(excluded),'not_selected_query_ids':{g:s['not_selected'] for g,s in selection['searches'].items()}},ensembl_summary={'server_release':info,'attempted':attempted,'matched_variants':[{'vcv':v['vcv'],'variation_id':v['variation_id'],'location':v['ensembl']['location'],'consequence':v['ensembl']['most_severe_consequence'],'verified_gene_ids':v['ensembl']['verified_gene_ids'],'transcript_count':len(v['ensembl']['transcripts']),'source_id':v['ensembl']['source']['id']} for v in variants if v['ensembl']['status']=='matched']},ai_used=False)
            manifest={'experiment':'GEE-001','engine_version':'0.1.0','parser_version':PARSER_VERSION,'selection':selection,'sources':report['sources'],'analysis_sha256':report['analysis_sha256'],'variant_versions':{v['variation_id']:v['vcv'] for v in variants},'source_code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},'data_policy':'Public variant/organization metadata only; no Sample/ObservedData/free-text clinical narratives in indexed/exported results','reproduce':'python -m genomics.cli verify --data SAME_LOCAL_ARCHIVE --job JOB_ID (raw cache required; no network)'}
            (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(folder/'report.html').write_text(html_report(report));(folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
            job.update(status='partial' if errors else 'completed',phase='Completed with explicit errors' if errors else 'Experiment completed',summary=report['metrics'],errors=errors,exclusions=report['exclusions'],analysis_sha256=report['analysis_sha256'],progress={'completed':len(ids),'planned':len(ids)})
        except Exception as exc:job.update(status='failed',phase='Experiment not completed',errors=errors+[{'source':'engine','error':str(exc)[:500]}])
        finally:job.update(completed_at=now(),duration_seconds=round(time.monotonic()-started,3));self.store.save(job);self.lock.release()
    def report(self,job_id):
        job=self.store.get(job_id)
        if not job:raise ValueError('Unknown research job')
        p=self.root/'jobs'/job['id']/'report.json'
        if not p.exists():raise ValueError('Report is not available yet')
        return json.loads(p.read_text())
    def verify(self,job_id):
        job=self.store.get(job_id);report=self.report(job_id);cache=PublicCache(self.root/'jobs'/job['id']/'cache',max_bytes=self.max_download)
        stored=self.store.variants(job_id,limit=500);reparsed=[];observations_match=True
        for v in stored:
            source=next(s for s in report['sources'] if s['id']==v['source_id']);raw,record=cache.fetch(source['url'],offline=True)
            if record['sha256']!=source['sha256']:raise ValueError('Source manifest/hash mismatch')
            parsed=parse_vcv(raw)[0]
            for k in parsed:
                if parsed[k]!=v[k]:observations_match=False
            parsed.update({k:v[k] for k in ('source_id','source_sha256','ensembl','rcv_detail_checks') if k in v});reparsed.append(parsed)
        for source in report['sources']:
            _,record=cache.fetch(source['url'],offline=True)
            if record['sha256']!=source['sha256']:raise ValueError('Cached dataset changed')
        regenerated=analyze(reparsed,report['selection'],report['errors'])
        return {'passed':observations_match and regenerated['analysis_sha256']==report['analysis_sha256'],'raw_sources_verified':len(report['sources']),'variants_reparsed':len(reparsed),'analysis_sha256':regenerated['analysis_sha256'],'expected_analysis_sha256':report['analysis_sha256'],'observations_match':observations_match,'network_used':False,'verified_at':now()}
