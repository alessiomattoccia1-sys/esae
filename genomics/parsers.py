# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Bounded public-data parsers. Never retain patient/sample observations."""
import csv,gzip,io,re,hashlib,json
from dataclasses import dataclass,asdict
from xml.etree import ElementTree as ET

PARSER_VERSION='gee-0.1.0'
def text(node,path,default=''):
    value=node.find(path) if node is not None else None
    return (value.text or '').strip() if value is not None else default
def accession(value,prefix):
    if not re.fullmatch(prefix+r'\d{9,12}(?:\.\d+)?',str(value)):raise ValueError('Invalid '+prefix+' accession')
    return value
def versioned(node,prefix):
    acc=node.get('Accession') or node.get('Acc') or ''
    accession(acc,prefix);version=node.get('Version')
    return acc+'.'+version if version and '.' not in acc else acc
def secure_xml(raw,max_bytes=12_000_000):
    if not raw or len(raw)>max_bytes or b'<!ENTITY' in raw.upper() or re.search(br'<!DOCTYPE[^>]*\[',raw,re.I):raise ValueError('Invalid/oversized XML or entity declarations')
    depth=0
    for event,_ in ET.iterparse(io.BytesIO(raw),events=('start','end')):
        depth+=1 if event=='start' else -1
        if depth>80:raise ValueError('XML nesting limit exceeded')
    return ET.fromstring(raw)
def stars(status):
    value=status.lower()
    if value=='practice guideline':return 4
    if value=='reviewed by expert panel':return 3
    if value=='criteria provided, multiple submitters, no conflicts':return 2
    if value.startswith('criteria provided,'):return 1
    if value.startswith('no assertion') or value in ('no classification provided','no classification for the single variant','no classification for the individual variant'):return 0
    return None
def criteria(status):
    s=stars(status);return None if s is None else s>0
def classification(node,path='GermlineClassification'):
    el=node.find(path) if node is not None else None
    return {'description':text(el,'Description'),'review_status':text(el,'ReviewStatus'),'review_stars':stars(text(el,'ReviewStatus')),'last_evaluated':el.get('DateLastEvaluated') if el is not None else None}
def condition_key(conditions):
    if not conditions:return None
    if any(c.get('name','').strip().lower() in ('not provided','not specified','unknown','not reported') for c in conditions):return None
    ids=sorted({c['id'] for c in conditions if c.get('db')=='MedGen' and c.get('id')})
    if not ids or any(not c.get('id') or c.get('db')!='MedGen' for c in conditions):return None
    return '|'.join('MedGen:'+i for i in ids)
def citations(node):
    return sorted({c.get('Source')+':'+(c.text or '').strip() for c in node.findall('.//Citation/ID') if c.get('Source') in ('PubMed','DOI') and (c.text or '').strip()})

def parse_vcv(raw):
    root=secure_xml(raw);archives=[root] if root.tag=='VariationArchive' else root.findall('VariationArchive')
    if not archives:raise ValueError('No VariationArchive returned; empty efetch is not success')
    results=[]
    for a in archives:
        vid=a.get('VariationID','')
        if not re.fullmatch(r'[1-9]\d{0,11}',vid):raise ValueError('Invalid Variation ID in XML')
        if text(a,'RecordStatus')!='current':raise ValueError('Unsupported non-current record: '+vid)
        c=a.find('ClassifiedRecord');allele=c.find('SimpleAllele') if c is not None else None
        if allele is None:raise ValueError('Unsupported haplotype/included/nonclassified record: '+vid)
        if text(a,'Species')!='Homo sapiens':raise ValueError('Human public variants only')
        genes=[{'symbol':g.get('Symbol'),'ncbi_gene_id':g.get('GeneID'),'hgnc_id':g.get('HGNC_ID')} for g in allele.findall('GeneList/Gene')]
        locations=[]
        for l in allele.findall('Location/SequenceLocation'):
            if l.get('Assembly') not in ('GRCh37','GRCh38'):continue
            pos=l.get('positionVCF');ref=l.get('referenceAlleleVCF');alt=l.get('alternateAlleleVCF')
            locations.append({'assembly':l.get('Assembly'),'sequence_accession':l.get('Accession'),'chromosome':l.get('Chr'),'position':int(pos) if pos and pos.isdigit() else None,'start':int(l.get('start')) if l.get('start','').isdigit() else None,'stop':int(l.get('stop')) if l.get('stop','').isdigit() else None,'reference':ref,'alternate':alt,'representation':'VCF 1-based forward genomic' if pos and ref and alt else 'imprecise_or_missing_vcf_alleles'})
        rcvs=[]
        for r in c.findall('RCVList/RCVAccession'):
            cond=[{'db':x.get('DB'),'id':x.get('ID'),'name':(x.text or '').strip()} for x in r.findall('ClassifiedConditionList/ClassifiedCondition')]
            cl=classification(r,'RCVClassifications/GermlineClassification');desc=r.find('RCVClassifications/GermlineClassification/Description')
            cl['last_evaluated']=desc.get('DateLastEvaluated') if desc is not None else None
            rcvs.append({'accession':versioned(r,'RCV'),'conditions':cond,'condition_key':condition_key(cond),'germline':cl})
        mapping={}
        for m in c.findall('TraitMappingList/TraitMapping'):
            for n in m.findall('MedGen'):
                mapping.setdefault(m.get('ClinicalAssertionID'),{})[n.get('CUI')]={'db':'MedGen','id':n.get('CUI'),'name':n.get('Name','')}
        submissions={};excluded={'non_current_scv':0,'non_germline_scv':0,'duplicate_scv':0}
        for s in c.findall('ClinicalAssertionList/ClinicalAssertion'):
            acc=s.find('ClinVarAccession')
            if acc is None:continue
            status=text(s,'RecordStatus')
            if status!='current':excluded['non_current_scv']+=1;continue
            cl=s.find('Classification');label=text(cl,'GermlineClassification')
            if not label:excluded['non_germline_scv']+=1;continue
            sv=versioned(acc,'SCV');review=text(cl,'ReviewStatus')
            cond=list(mapping.get(s.get('ID'),{}).values())
            if not cond:
                for trait in s.findall('TraitSet/Trait'):
                    name=text(trait,'Name/ElementValue');refs=trait.findall('XRef')
                    direct=[{'db':x.get('DB'),'id':x.get('ID'),'name':name} for x in refs if x.get('DB')=='MedGen']
                    cond.extend(direct or [{'db':None,'id':None,'name':name or 'unmapped condition'}])
            key=condition_key(cond);matched_rcv=[r['accession'] for r in rcvs if key is not None and key==r['condition_key']]
            methods=sorted({(x.text or '').strip() for x in s.findall('.//Method/MethodType') if (x.text or '').strip()})
            # Whitelist only organization/evidence metadata; no Sample/ObservedData or narrative comments.
            item={'accession':sv,'variant_id':vid,'submitter_id':acc.get('OrgID'),'submitter':acc.get('SubmitterName'),'submitter_category':acc.get('OrganizationCategory','unknown'),'classification':label,'review_status':review,'review_stars':stars(review),'criteria_declared':criteria(review),'last_evaluated':cl.get('DateLastEvaluated'),'updated_at':s.get('DateLastUpdated'),'current':True,'contributes_to_aggregate':{'true':True,'false':False}.get(s.get('ContributesToAggregateClassification')),'conditions':cond,'condition_key':key,'rcv_matches':matched_rcv,'citations':citations(s),'methods':methods,'url':'https://www.ncbi.nlm.nih.gov/clinvar/?term='+sv}
            base=sv.split('.')[0]
            if base in submissions:
                excluded['duplicate_scv']+=1
                previous=submissions[base]
                if (int(sv.split('.')[-1]) if '.' in sv else 0)<=(int(previous['accession'].split('.')[-1]) if '.' in previous['accession'] else 0):continue
            submissions[base]=item
        aggregate=classification(c,'Classifications/GermlineClassification')
        item={'variation_id':vid,'vcv':versioned(a,'VCV'),'name':a.get('VariationName',''),'variant_type':a.get('VariationType',''),'record_updated':a.get('DateLastUpdated'),'genes':genes,'locations':locations,'canonical_spdi':text(allele,'CanonicalSPDI'),'germline':aggregate,'rcvs':rcvs,'submissions':sorted(submissions.values(),key=lambda x:x['accession']),'excluded_submission_records':excluded,'citations':citations(c.find('Classifications')) if c.find('Classifications') is not None else [],'url':'https://www.ncbi.nlm.nih.gov/clinvar/variation/'+vid+'/','source':'NCBI ClinVar','parser_version':PARSER_VERSION}
        results.append(item)
    return results

def parse_rcv(raw):
    root=secure_xml(raw);out=[]
    for s in root.findall('ClinVarSet'):
        r=s.find('ReferenceClinVarAssertion')
        if r is None:continue
        acc=r.find('ClinVarAccession')
        if acc is None:continue
        germ=r.find('Classifications/GermlineClassification')
        if germ is not None:
            cl=classification(r,'Classifications/GermlineClassification')
            desc=germ.find('Description')
            if not cl.get('last_evaluated') and desc is not None:cl['last_evaluated']=desc.get('DateLastEvaluated')
        else:cl={'description':text(r,'ClinicalSignificance/Description'),'review_status':text(r,'ClinicalSignificance/ReviewStatus'),'last_evaluated':r.find('ClinicalSignificance').get('DateLastEvaluated') if r.find('ClinicalSignificance') is not None else None}
        out.append({'accession':versioned(acc,'RCV'),'germline':cl,'scvs':[versioned(a,'SCV') for a in s.findall('ClinVarAssertion/ClinVarAccession')],'url':'https://www.ncbi.nlm.nih.gov/clinvar/'+versioned(acc,'RCV')+'/'})
    if not out:raise ValueError('No RCV detail returned')
    return out

@dataclass
class ImportCounts:
    examined:int=0
    imported:int=0
    excluded:int=0
    invalid:int=0
    duplicates:int=0
    reason_counts:dict=None
    def __post_init__(self):self.reason_counts={}
    def count(self,reason):self.reason_counts[reason]=self.reason_counts.get(reason,0)+1

def tsv_rows(stream,*,compressed=False,max_uncompressed_bytes=200_000_000,max_rows=2_000_000):
    """Stream each row; metadata comments preceding the header are supported."""
    src=gzip.GzipFile(fileobj=stream) if compressed else stream
    total=0;header=None;rows=0
    for raw in iter(lambda:src.readline(1_000_001),b''):
        total+=len(raw)
        if total>max_uncompressed_bytes or len(raw)>1_000_000:raise ValueError('TSV expansion/line limit exceeded')
        line=raw.decode('utf-8-sig').rstrip('\r\n')
        if header is None:
            candidate=line.lstrip('#').split('\t')
            if len(candidate)>3 and any(x in candidate for x in ('VariationID','NCBI_Variation_ID','AlleleID')):header=candidate
            continue
        if not line or line.startswith('#'):continue
        rows+=1
        if rows>max_rows:raise ValueError('TSV record limit exceeded')
        values=next(csv.reader([line],delimiter='\t',quoting=csv.QUOTE_NONE))
        yield dict(zip(header,values)) if len(values)==len(header) else {'_invalid':'column_count'}
    if header is None:raise ValueError('Official TSV header not recognized')

def normalize_tsv(row,kind):
    if '_invalid' in row:raise ValueError(row['_invalid'])
    vid=row.get('VariationID') or row.get('NCBI_Variation_ID')
    if not vid or not vid.isdigit():raise ValueError('Missing Variation ID')
    if kind=='variant_summary':
        assembly=row.get('Assembly');
        if assembly not in ('GRCh37','GRCh38'):raise ValueError('Unsupported assembly')
        return {'variation_id':vid,'scope':'VCV_summary_not_condition_specific','assembly':assembly,'gene':row.get('GeneSymbol'),'classification':row.get('ClinicalSignificance'),'review_status':row.get('ReviewStatus'),'rcvs':row.get('RCVaccession','').split('|'),'position':row.get('PositionVCF'),'reference':row.get('ReferenceAlleleVCF'),'alternate':row.get('AlternateAlleleVCF')}
    if kind=='submission_summary':
        scv=row.get('SCV') or row.get('SCVaccession');accession(scv,'SCV')
        return {'variation_id':vid,'scope':'SCV_submission','scv':scv,'classification':row.get('ClinicalSignificance'),'condition':row.get('ReportedPhenotypeInfo'),'submitter':row.get('Submitter'),'last_evaluated':row.get('DateLastEvaluated'),'review_status':row.get('ReviewStatus')}
    if kind=='conflicting_interpretations':
        return {'variation_id':vid,'scope':'official_submitter_pair','scv1':accession(row.get('Submitter1_SCV'),'SCV'),'scv2':accession(row.get('Submitter2_SCV'),'SCV'),'classification1':row.get('Submitter1_ClinSig'),'classification2':row.get('Submitter2_ClinSig'),'official_conflict':row.get('Conflict_Reported','').lower()=='yes','conditions1':row.get('Submitter1_Sub_Condition'),'conditions2':row.get('Submitter2_Sub_Condition')}
    raise ValueError('Unknown TSV type')

def import_tsv(stream,kind,counts,*,compressed=False,variation_ids=None,sink=None,**limits):
    seen=set()
    for row in tsv_rows(stream,compressed=compressed,**limits):
        counts.examined+=1
        try:item=normalize_tsv(row,kind)
        except (ValueError,TypeError):counts.invalid+=1;counts.count('invalid_row');continue
        if variation_ids is not None and item['variation_id'] not in variation_ids:counts.excluded+=1;counts.count('outside_selected_ids');continue
        key=hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()
        if key in seen:counts.duplicates+=1;counts.count('duplicate');continue
        seen.add(key);counts.imported+=1
        if sink:sink(item)
    return asdict(counts)
