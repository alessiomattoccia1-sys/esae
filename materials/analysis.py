# SPDX-License-Identifier: Apache-2.0
"""Deterministic PV screening, transparent ordering and paired statistics."""
from dataclasses import dataclass,asdict
from collections import Counter
import math,json,hashlib,re
import numpy as np
from scipy.stats import pearsonr,spearmanr

@dataclass(frozen=True)
class ScreeningConfig:
    gap_min:float=.8
    gap_max:float=2.2
    target_gap:float=1.5
    hull_max:float=.1
    slme_min:float=10.
    exclude_elements:tuple=()
    require_dielectric:bool=False
    def validate(self):
        values=[self.gap_min,self.gap_max,self.target_gap,self.hull_max,self.slme_min]
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):raise ValueError('Finite numeric screening parameters required')
        if not 0<=self.gap_min<=self.target_gap<=self.gap_max<=20 or not 0<=self.hull_max<=5 or not 0<=self.slme_min<=100 or self.gap_min==self.gap_max:raise ValueError('Screening interval/threshold out of bounds')
        from jarvis.core.specie import Specie
        if len(self.exclude_elements)>20:raise ValueError('Invalid element filter')
        try:
            if any(not isinstance(x,str) or not re.fullmatch(r'[A-Z][a-z]?',x) or not Specie(x).Z for x in self.exclude_elements):raise ValueError('Invalid element filter')
        except (KeyError,TypeError):raise ValueError('Invalid element filter')
        if not isinstance(self.require_dielectric,bool):raise ValueError('Dielectric filter must be boolean')
        return self

def fraction(n,d):return {'numerator':int(n),'denominator':int(d),'percent':round(100*n/d,6) if d else None}
def prop(row,key):return row['properties'].get(key)
def screen(rows,config):
    config.validate();out={'gap_only':[],'stability':[],'optical':[]};reasons=Counter();counts=Counter()
    for row in rows:
        p=row['properties'];gap=p['gap_mbj'];counts['examined']+=1
        if gap is None:reasons['missing_tbmbj_gap']+=1;continue
        if not config.gap_min<=gap<=config.gap_max:reasons['outside_gap_interval']+=1;continue
        if set(row['elements'])&set(config.exclude_elements):reasons['excluded_composition']+=1;continue
        if config.require_dielectric and any(x is None for x in p['meps_diagonal']):reasons['missing_complete_tbmbj_dielectric']+=1;continue
        out['gap_only'].append(row)
        if p['hull_ev_atom'] is None:reasons['missing_hull_after_gap_filter']+=1;continue
        if p['hull_ev_atom']>config.hull_max:reasons['above_hull_threshold']+=1;continue
        out['stability'].append(row)
        if p['slme_percent'] is None:reasons['missing_slme_after_stability']+=1;continue
        if p['slme_percent']<config.slme_min:reasons['below_slme_threshold']+=1;continue
        out['optical'].append(row)
    out['gap_only'].sort(key=lambda r:(abs(prop(r,'gap_mbj')-config.target_gap),int(r['jid'].split('-')[1])))
    out['stability'].sort(key=lambda r:(prop(r,'hull_ev_atom'),abs(prop(r,'gap_mbj')-config.target_gap),int(r['jid'].split('-')[1])))
    out['optical'].sort(key=lambda r:(-prop(r,'slme_percent'),prop(r,'hull_ev_atom'),abs(prop(r,'gap_mbj')-config.target_gap),int(r['jid'].split('-')[1])))
    return out,dict(reasons)

def correlation(x,y):
    pairs=[(float(a),float(b)) for a,b in zip(x,y) if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)]
    n=len(pairs)
    if n<3 or len({a for a,b in pairs})<2 or len({b for a,b in pairs})<2:return {'n_pairs':n,'status':'not_determinable','pearson':None,'spearman':None}
    a,b=np.array(pairs).T
    return {'n_pairs':n,'status':'computed','pearson':round(float(pearsonr(a,b).statistic),12),'spearman':round(float(spearmanr(a,b).statistic),12),'meaning':'Descriptive paired-complete-case coefficients. No causal or population-inference claim.'}

def distribution(rows,key):
    valid=[prop(r,key) for r in rows if prop(r,key) is not None];bins=[0,.8,1.2,1.6,2.2,3,5,10,float('inf')];hist=np.histogram(valid,bins=bins)[0].tolist() if valid else [0]*8
    return {'property':key,'unit':'eV','available':len(valid),'missing':len(rows)-len(valid),'denominator':len(rows),'minimum':min(valid) if valid else None,'maximum':max(valid) if valid else None,'median':float(np.median(valid)) if valid else None,'bins':[{'lower':bins[i],'upper':bins[i+1] if math.isfinite(bins[i+1]) else None,'count':n} for i,n in enumerate(hist)]}

def outliers(rows,key):
    values=[prop(r,key) for r in rows if prop(r,key) is not None]
    if len(values)<4:return {'status':'not_determinable','n':len(values)}
    q1,q3=np.percentile(values,[25,75]);iqr=q3-q1;lower=float(q1-1.5*iqr);upper=float(q3+1.5*iqr);ids=[r['jid'] for r in rows if prop(r,key) is not None and (prop(r,key)<lower or prop(r,key)>upper)] if iqr else []
    return {'status':'computed' if iqr else 'zero_iqr','method':'Tukey 1.5 IQR, descriptive flags not invalid-material decisions','n':len(values),'q1':float(q1),'q3':float(q3),'lower':lower,'upper':upper,'count':len(ids),'example_jids':ids[:20]}

def candidate(row,rank,tier):
    return {'rank':rank,'tier':tier,'jid':row['jid'],'formula':row['formula'],'properties':row['properties'],'methods':row['methods'],'chemical_family':row['chemical_family'],'crystal_system':row['crystal_system'],'n_elements':row['n_elements'],'structure_sha256':row.get('structure_sha256') or row['structure']['sha256'],'url':row['url'],'selection_reason':{'gap_only':'TB-mBJ gap in configured window; ordered by distance to configured midpoint target, not an efficiency prediction','stability':'Gap/composition filters and known hull below threshold; ordered by hull then gap distance','optical':'Gap and hull criteria plus reported SLME threshold; ordered by SLME descending, hull and gap distance'}[tier],'evidence_kind':'observed_data_and_computed_result','not_verified':'No experimental device efficiency, synthesis feasibility, optical-condition equivalence or new-material discovery is established.'}

def analyze(rows,config,ingestion):
    rows=sorted(rows,key=lambda r:int(r['jid'].split('-')[1]))
    if not rows:raise ValueError('No valid materials: experiment not completed')
    if len({r['jid'] for r in rows})!=len(rows):raise ValueError('Duplicate material identity in analysis')
    ranked,reasons=screen(rows,config);n=len(rows);m={'records_acquired':ingestion['records_seen'],'valid_unique_materials':n,'invalid_records':ingestion['invalid_records'],'duplicate_records':ingestion['duplicates'],'excluded_reasons':ingestion['invalid_reasons'],'availability':{},'screen_counts':{k:fraction(len(v),n) for k,v in ranked.items()},'screen_exclusions':reasons,'formula_count':len({r['formula'] for r in rows}),'crystal_systems':dict(sorted(Counter(r['crystal_system'] for r in rows).items()))}
    for key in ['gap_mbj','gap_opt','formation_ev_atom','hull_ev_atom','slme_percent']:
        m['availability'][key]=fraction(sum(prop(r,key) is not None for r in rows),n)
    m['availability']['tbmbj_dielectric_complete']=fraction(sum(all(v is not None for v in r['properties']['meps_diagonal']) for r in rows),n)
    sensitivity=[];sets=[]
    for low,high in [(.8,2.2),(1.,2.),(1.2,1.8)]:
        for hull in [0.,.05,.1,.2]:
            c=ScreeningConfig(low,high,1.5,hull,config.slme_min,config.exclude_elements,config.require_dielectric);v,_=screen(rows,c);ids={r['jid'] for r in v['optical']};sets.append(ids);base_top={r['jid'] for r in ranked['optical'][:10]};new_top={r['jid'] for r in v['optical'][:10]}
            sensitivity.append({'gap_min':low,'gap_max':high,'hull_max':hull,'slme_min':config.slme_min,'gap_count':len(v['gap_only']),'stability_count':len(v['stability']),'optical_count':len(v['optical']),'top10_jids':[r['jid'] for r in v['optical'][:10]],'top10_overlap_with_configured_optical':fraction(len(base_top&new_top),len(base_top|new_top))})
    common=sorted(set.intersection(*sets)) if sets else [];tops={k:[r['jid'] for r in v[:10]] for k,v in ranked.items()};comparisons={}
    for a,b in [('gap_only','stability'),('stability','optical'),('gap_only','optical')]:
        sa,sb=set(tops[a]),set(tops[b]);comparisons[a+'_vs_'+b]={'top10_jaccard':fraction(len(sa&sb),len(sa|sb)),'top10_common':sorted(sa&sb),'lost_on_additional_filter':len(ranked[a])-len(ranked[b]),'note':'Changed cohort eligibility and ordering are distinct; raw rank shifts are not proof of physical improvement.'}
    groups={family:{'count':sum(r['chemical_family']==family for r in rows),'mbj_gap_median':float(np.median([prop(r,'gap_mbj') for r in rows if r['chemical_family']==family and prop(r,'gap_mbj') is not None])) if any(r['chemical_family']==family and prop(r,'gap_mbj') is not None for r in rows) else None,'mbj_gap_denominator':sum(r['chemical_family']==family and prop(r,'gap_mbj') is not None for r in rows)} for family in sorted({r['chemical_family'] for r in rows})}
    correlations={a+'_vs_'+b:correlation([prop(r,a) for r in rows],[prop(r,b) for r in rows]) for a,b in [('gap_mbj','slme_percent'),('gap_mbj','hull_ev_atom'),('slme_percent','hull_ev_atom')]}
    result={'experiment':'MDE-001','title':'Computational Screening of Photovoltaic Materials','engine_version':'0.1.0','method_version':'mde-001-1.0','configuration':asdict(config),'bandgap_method':'TB-mBJ; optB88vdW distribution kept separate','ranking_method':{'gap_only':'abs(TB-mBJ gap - configured target), JID','stability':'energy_above_hull, gap distance, JID','optical':'reported SLME descending, hull, gap distance, JID','composite_probability_score':False},'metrics':m,'bandgap_distributions':{k:distribution(rows,k) for k in ['gap_mbj','gap_opt']},'candidate_lists':{k:[candidate(r,i+1,k) for i,r in enumerate(v[:100])] for k,v in ranked.items()},'candidate_lists_limit':100,'sensitivity':sensitivity,'robust_across_all12_criteria':{'count':len(common),'jids':common[:100],'list_limit':100},'ranking_comparisons':comparisons,'chemical_groups':groups,'correlations':correlations,'outliers':{k:outliers(rows,k) for k in ['gap_mbj','hull_ev_atom','slme_percent']},'findings':[{'id':'MDE-001-F1','title':'Property coverage and band-gap distribution','method':'All valid unique JARVIS IDs, separate computational methods, missing values retained','evidence':'metrics / bandgap_distributions','interpretation':'Descriptive source coverage, not an estimate of all possible materials'},{'id':'MDE-001-F2','title':'Reproducible photovoltaic screening candidates','method':'Configured TB-mBJ gap, known hull and reported SLME criteria; explicit lexicographic ranking','evidence':'candidate_lists / configuration','interpretation':'Candidates for further research, not new materials or validated devices'},{'id':'MDE-001-F3','title':'Sensitivity to thresholds and missing properties','method':'Three gap windows × four hull thresholds; compare stage counts and top-ten membership','evidence':'sensitivity / ranking_comparisons','interpretation':'Cohort and ordering changes depend on coverage and chosen criteria, not probability of success'}],'limitations':['Experimental public-data screening, not a new DFT calculation or physical experiment.','TB-mBJ and optB88vdW band gaps are not pooled or treated as interchangeable.','Formation energy is separate from energy above hull; missing hull is excluded at the stability stage.','Hull threshold is exploratory and does not establish synthesis feasibility or finite-temperature stability.','SLME is a reported theoretical percentage, not experimental efficiency; per-record optical thickness/temperature are not encoded or independently verified.','Absorption spectra are not present in this bulk snapshot; dielectric diagonals are scalar descriptors, not full spectra.','Ranking uses transparent lexicographic order, not a learned probability or arbitrary confidence score.','Correlations are paired descriptive statistics, not causal laws. Source sampling and missingness limit comparisons.','Polymorphs retain separate JARVIS IDs; materials are not deduplicated by formula.','No toxicity, availability, manufacturing, environmental or economic suitability validation.'],'ai_used_for_numeric_results':False}
    result['analysis_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,allow_nan=False).encode()).hexdigest();return result,ranked
