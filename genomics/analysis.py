# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Deterministic evidence comparisons. No diagnosis or reliability score."""
from collections import Counter,defaultdict
import hashlib,json

def pathogenicity_band(label):
    parts={x.strip().lower() for x in label.split('/')}
    if parts and parts<={'pathogenic','likely pathogenic'}:return 'P/LP'
    if parts and parts<={'benign','likely benign'}:return 'B/LB'
    if parts=={'uncertain significance'}:return 'VUS'
    return None
def percentage(n,d):return {'numerator':n,'denominator':d,'percent':round(n*100/d,3) if d else None}
def distribution(values):return dict(sorted(Counter(values).items()))

def variant_evidence(v):
    groups=defaultdict(list);all_bins=set();undetermined=0
    for s in v['submissions']:
        band=pathogenicity_band(s['classification'])
        if band:all_bins.add(band)
        if s['condition_key'] and band and s.get('submitter_id'):groups[s['condition_key']].append(s)
        else:undetermined+=1
    comparisons=[]
    for key,items in sorted(groups.items()):
        orgs={s['submitter_id'] for s in items};bands={pathogenicity_band(s['classification']) for s in items}
        if len(orgs)<2:continue
        contributed=[s for s in items if s['contributes_to_aggregate'] is True]
        dates=sorted({s['last_evaluated'] for s in items if s.get('last_evaluated')})
        comparison={'condition_key':key,'conditions':items[0]['conditions'],'submitters':len(orgs),'scv_count':len(items),'classifications':distribution(s['classification'] for s in items),'bands':sorted(bands),'major_difference':len(bands)>1,'minor_label_difference':len({s['classification'].lower() for s in items})>1 and len(bands)==1,'difference_among_contributing_submissions':len({s['submitter_id'] for s in contributed})>1 and len({pathogenicity_band(s['classification']) for s in contributed})>1,'different_evaluation_dates':len(dates)>1,'evaluation_dates':dates,'scvs':[s['accession'] for s in items],'rcvs':sorted({r for s in items for r in s['rcv_matches']})}
        comparisons.append(comparison)
    same_diff=any(g['major_difference'] for g in comparisons)
    return {'official_aggregate_conflict':'conflicting' in v['germline']['description'].lower(),'same_condition_comparable':bool(comparisons),'same_condition_difference':same_diff,'same_condition_comparisons':comparisons,'different_conditions_only':len(all_bins)>1 and not same_diff and len({s['condition_key'] for s in v['submissions'] if s['condition_key']})>1,'insufficient_submission_context':undetermined,'differences_not_expressed_in_aggregate':same_diff and 'conflicting' not in v['germline']['description'].lower(),'meaning':'Observed classifications from current germline submissions, compared only for identical NCBI-mapped condition sets and independent submitter IDs. Differences are not a clinical reassessment.'}

def analyze(variants,selection,errors=None):
    variants=sorted(variants,key=lambda v:int(v['variation_id']));n=len(variants)
    if len({v['variation_id'] for v in variants})!=n:raise ValueError('Duplicate variant identity in analysis')
    details=[{'variation_id':v['variation_id'],'vcv':v['vcv'],'genes':[g['symbol'] for g in v['genes']],'url':v['url'],'analysis':variant_evidence(v)} for v in variants]
    submissions=[s for v in variants for s in v['submissions']];scv_n=len(submissions);rcv_n=sum(len(v['rcvs']) for v in variants)
    eligible=[d for d in details if d['analysis']['same_condition_comparable']]
    official=sum(d['analysis']['official_aggregate_conflict'] for d in details);diff=sum(d['analysis']['same_condition_difference'] for d in details)
    aggregate_available=sum(bool(v['germline']['description']) for v in variants)
    metrics={'variants':n,'rcv_records':rcv_n,'current_germline_scv_records':scv_n,'unique_submitters':len({s['submitter_id'] for s in submissions if s['submitter_id']}),'official_aggregate_conflicts':percentage(official,aggregate_available),'same_condition_differences':percentage(diff,len(eligible)),'variants_comparable_by_condition':len(eligible),'classification_distribution':distribution(v['germline']['description'] or 'not available' for v in variants),'review_status_distribution':distribution(v['germline']['review_status'] or 'not available' for v in variants),'review_stars_distribution':distribution(str(v['germline']['review_stars']) if v['germline']['review_stars'] is not None else 'not determinable' for v in variants),'expert_panel_aggregate':percentage(sum(v['germline']['review_stars']==3 for v in variants),n),'scv_criteria_declared':percentage(sum(s['criteria_declared'] is True for s in submissions),scv_n),'scv_criteria_unknown':sum(s['criteria_declared'] is None for s in submissions),'scv_with_evaluation_date':percentage(sum(bool(s['last_evaluated']) for s in submissions),scv_n),'scv_with_citations':percentage(sum(bool(s['citations']) for s in submissions),scv_n),'submitter_categories_scv_weighted':distribution(s['submitter_category'] for s in submissions),'variants_with_ensembl_annotation':percentage(sum(v.get('ensembl',{}).get('status')=='matched' for v in variants),sum(v.get('ensembl',{}).get('status') in ('matched','failed') for v in variants)),'date_heterogeneous_condition_groups':sum(g['different_evaluation_dates'] for d in details for g in d['analysis']['same_condition_comparisons']),'condition_comparison_groups':sum(len(d['analysis']['same_condition_comparisons']) for d in details),'variants_with_unmapped_submission_context':sum(d['analysis']['insufficient_submission_context']>0 for d in details),'variants_with_differences_not_expressed_in_aggregate':sum(d['analysis']['differences_not_expressed_in_aggregate'] for d in details),'variants_with_different_conditions_only':sum(d['analysis']['different_conditions_only'] for d in details)}
    metrics['ensembl_coverage_of_imported_variants']=percentage(sum(v.get('ensembl',{}).get('status')=='matched' for v in variants),n)
    org_categories=defaultdict(set)
    for s in submissions:
        if s.get('submitter_id'):org_categories[s['submitter_id']].add(s['submitter_category'])
    metrics['submitter_categories_unique_organizations']=distribution(' + '.join(sorted(values)) for values in org_categories.values())
    metrics['scvs_without_submitter_id']=sum(not s.get('submitter_id') for s in submissions)
    examples=[]
    ranked=sorted(details,key=lambda d:(not d['analysis']['same_condition_difference'],not d['analysis']['official_aggregate_conflict'],int(d['variation_id'])))
    for d in ranked:
        if not (d['analysis']['official_aggregate_conflict'] or d['analysis']['same_condition_difference']):continue
        v=next(v for v in variants if v['variation_id']==d['variation_id'])
        comparisons=[g for g in d['analysis']['same_condition_comparisons'] if g['major_difference']]
        ids={s for g in comparisons for s in g['scvs']}
        examples.append({**d,'name':v['name'],'aggregate':v['germline'],'comparisons':comparisons,'scvs':[s for s in v['submissions'] if s['accession'] in ids],'rcv_detail_checks':v.get('rcv_detail_checks',[])})
        if len(examples)>=8:break
    findings=[{'id':'GEE-001-Q1','title':'Variant-level classification and conflict counts','kind':'computational_result','method':'Unique Variation IDs, germline VCV classification; explicit denominator for each ratio','dataset':'GEE-001 frozen public-source sample','result':{'classification_distribution':metrics['classification_distribution'],'official_conflicts':metrics['official_aggregate_conflicts'],'same_condition_differences':metrics['same_condition_differences']},'evidence':[v['vcv'] for v in variants],'limits':'Deterministic lowest-ID sample, not random and not a population prevalence estimate.'},
    {'id':'GEE-001-Q2','title':'Documented classification differences','kind':'computational_result','method':'Current germline SCVs, exact NCBI MedGen condition-set match, independent organization IDs; P/LP and B/LB grouped separately from VUS','dataset':'GEE-001 frozen public-source sample','result':{'example_accessions':[e['vcv'] for e in examples],'examples_found':len(examples)},'evidence':[s['accession'] for e in examples for s in e['scvs']],'limits':'Current submission-level differences are not necessarily ClinVar aggregate conflicts; dates, review tiers and noncontributing submissions remain explicit.'},
    {'id':'GEE-001-Q3','title':'Review status and documentary completeness','kind':'computational_result','method':'Count official review labels and available SCV metadata, without invented reliability score','dataset':'GEE-001 frozen public-source sample','result':{'review_distribution':metrics['review_status_distribution'],'criteria':metrics['scv_criteria_declared'],'dates':metrics['scv_with_evaluation_date'],'citations':metrics['scv_with_citations']},'evidence':[v['vcv'] for v in variants],'limits':'Declared criteria/review tier do not establish correctness; missing metadata is not evidence of invalidity.'}]
    report={'experiment':'GEE-001','title':'Classificatory discordance in public BRCA1/BRCA2 variant evidence','engine_version':'0.1.0','method_version':'gee-001-1.0','selection':selection,'metrics':metrics,'per_gene':{gene:{'variants':sum(any(g['symbol']==gene for g in v['genes']) for v in variants),'classification_distribution':distribution(v['germline']['description'] or 'not available' for v in variants if any(g['symbol']==gene for g in v['genes']))} for gene in selection['genes']},'examples':examples,'variant_analysis':details,'findings':findings,'errors':errors or [],'limitations':['Research only: no diagnosis, treatment or individual genetic analysis.','Sample is deterministic by lowest Variation ID within the official single-gene query; no representativeness claim.','VCV, RCV and SCV denominators are distinct. Germline classifications only.','Same-condition comparison requires identical NCBI-mapped MedGen condition sets; unresolved mappings are not forced.','P/LP and B/LB likelihood-only differences are separated from cross-band differences.','Contributing and noncontributing SCVs are reported separately; dates do not prove causes of disagreement.','VEP molecular consequence is independent of clinical classification; only exact GRCh38 SNVs qualified.','No artificial confidence/pathogenicity score, causal conclusion, clinical validation or model-weight learning.']}
    report['analysis_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,ensure_ascii=False).encode()).hexdigest();return report
