# SPDX-License-Identifier: Apache-2.0
"""Synthetic schema fixtures have explicit expected values; not live evidence."""
import gzip,io,json,hashlib
from copy import deepcopy
from pathlib import Path
import pytest
from genomics.parsers import parse_vcv,parse_rcv,tsv_rows,ImportCounts,import_tsv,condition_key,stars,secure_xml
from genomics.analysis import analyze,variant_evidence,pathogenicity_band
from genomics.storage import GenomicStore
from research_core.http import validate_url,PublicCache
from research_core import EmbeddedAdapter,evidence

@pytest.fixture
def vcv_fixture():
    def scv(i,label,cond,contribute='true',date='2024-01-01'):
        return f'''<ClinicalAssertion ID="{i}" ContributesToAggregateClassification="{contribute}"><ClinVarAccession Accession="SCV{i:09}" Version="1" OrgID="{i}" SubmitterName="Fixture organization {i}" OrganizationCategory="laboratory"/><RecordStatus>current</RecordStatus><Classification DateLastEvaluated="{date}"><ReviewStatus>criteria provided, single submitter</ReviewStatus><GermlineClassification>{label}</GermlineClassification></Classification><TraitSet><Trait><XRef DB="MedGen" ID="{cond}"/><Name><ElementValue>Fixture condition {cond}</ElementValue></Name></Trait></TraitSet><ObservedInList><Sample><SampleID>NEVER_INDEX_THIS</SampleID></Sample></ObservedInList><Citation><ID Source="PubMed">1</ID></Citation></ClinicalAssertion>'''
    return ('''<ClinVarResult-Set><VariationArchive VariationID="1" Accession="VCV000000001" Version="2" VariationName="Synthetic BRCA1 fixture" VariationType="single nucleotide variant"><RecordStatus>current</RecordStatus><Species>Homo sapiens</Species><ClassifiedRecord><SimpleAllele><GeneList><Gene Symbol="BRCA1" GeneID="672"/></GeneList><Location><SequenceLocation Assembly="GRCh38" Accession="NC_000017.11" Chr="17" positionVCF="100" referenceAlleleVCF="A" alternateAlleleVCF="G"/><SequenceLocation Assembly="GRCh37" Accession="NC_000017.10" Chr="17" positionVCF="90" referenceAlleleVCF="A" alternateAlleleVCF="G"/></Location></SimpleAllele><Classifications><GermlineClassification><Description>Conflicting classifications of pathogenicity</Description><ReviewStatus>criteria provided, conflicting classifications</ReviewStatus></GermlineClassification></Classifications><RCVList><RCVAccession Accession="RCV000000001" Version="1"><ClassifiedConditionList><ClassifiedCondition DB="MedGen" ID="C1">Fixture condition C1</ClassifiedCondition></ClassifiedConditionList><RCVClassifications><GermlineClassification><Description>Conflicting classifications of pathogenicity</Description><ReviewStatus>criteria provided, conflicting classifications</ReviewStatus></GermlineClassification></RCVClassifications></RCVAccession><RCVAccession Accession="RCV000000002" Version="1"><ClassifiedConditionList><ClassifiedCondition DB="MedGen" ID="C2">Fixture condition C2</ClassifiedCondition></ClassifiedConditionList></RCVAccession></RCVList><ClinicalAssertionList>'''+scv(1,'Pathogenic','C1')+scv(2,'Benign','C1',date='2025-01-01')+scv(3,'Uncertain significance','C2','false')+'''</ClinicalAssertionList></ClassifiedRecord></VariationArchive></ClinVarResult-Set>''').encode()

@pytest.fixture
def variant(vcv_fixture):return parse_vcv(vcv_fixture)[0]

def test_accession_scopes_mapping_and_public_metadata_only(variant):
    assert variant['vcv']=='VCV000000001.2' and variant['variation_id']=='1'
    assert len(variant['rcvs'])==2 and len(variant['submissions'])==3
    assert variant['submissions'][0]['rcv_matches']==['RCV000000001.1']
    assert variant['locations'][0]['assembly']=='GRCh38' and variant['locations'][1]['position']==90
    assert 'NEVER_INDEX_THIS' not in json.dumps(variant)
    assert variant['submissions'][2]['contributes_to_aggregate'] is False

def test_expected_counts_and_denominators(variant):
    selection={'genes':['BRCA1'],'selected_unique_ids':[1]};r=analyze([variant],selection);m=r['metrics']
    assert (m['variants'],m['rcv_records'],m['current_germline_scv_records'])==(1,2,3)
    assert m['official_aggregate_conflicts']=={'numerator':1,'denominator':1,'percent':100.0}
    assert m['same_condition_differences']['numerator']==m['same_condition_differences']['denominator']==1
    assert len(r['examples'])==1 and len(r['examples'][0]['scvs'])==2
    assert m['scv_with_citations']['denominator']==3

def test_different_conditions_not_forced_into_same_condition_conflict(variant):
    variant['submissions'][1]['condition_key']='MedGen:C3';r=variant_evidence(variant)
    assert r['same_condition_difference'] is False and r['different_conditions_only'] is True

def test_minor_likelihood_difference_not_major_conflict(variant):
    variant['submissions'][1]['classification']='Likely pathogenic';r=variant_evidence(variant)
    assert not r['same_condition_difference'] and r['same_condition_comparisons'][0]['minor_label_difference']

def test_same_submitter_not_independent_confirmation(variant):
    variant['submissions'][1]['submitter_id']='1';assert not variant_evidence(variant)['same_condition_comparable']

def test_expert_panel_aggregate_does_not_erase_raw_scv_differences(variant):
    variant['germline'].update(description='Pathogenic',review_status='reviewed by expert panel',review_stars=3)
    for s in variant['submissions']:s['contributes_to_aggregate']=False
    result=variant_evidence(variant);assert not result['official_aggregate_conflict']
    assert result['differences_not_expressed_in_aggregate']
    assert not result['same_condition_comparisons'][0]['difference_among_contributing_submissions']

def test_missing_condition_information_is_not_a_comparison(variant):
    for s in variant['submissions']:s['condition_key']=None
    r=variant_evidence(variant);assert not r['same_condition_comparable'] and r['insufficient_submission_context']==3

@pytest.mark.parametrize('value,expected',[('Pathogenic/Likely pathogenic','P/LP'),('Benign/Likely benign','B/LB'),('Uncertain significance','VUS'),('risk factor',None),('drug response',None)])
def test_bands_do_not_conflate_nonpathogenicity_assertions(value,expected):assert pathogenicity_band(value)==expected

@pytest.mark.parametrize('value,expected',[('practice guideline',4),('reviewed by expert panel',3),('criteria provided, multiple submitters, no conflicts',2),('criteria provided, single submitter',1),('no assertion criteria provided',0),('unrecognized official future status',None)])
def test_official_review_stars_are_not_invented_reliability_scores(value,expected):assert stars(value)==expected

def test_unknown_and_generic_conditions_not_guessed():
    assert condition_key([{'db':'MedGen','id':'C3661900','name':'not provided'}]) is None
    assert condition_key([{'db':'OMIM','id':'1','name':'same words'}]) is None

@pytest.mark.parametrize('raw',[b'<set/>',b'<!DOCTYPE x [<!ENTITY y "a">]><x>&y;</x>',b'<x>'*81+b'</x>'*81])
def test_empty_or_unsafe_xml_is_rejected(raw):
    with pytest.raises(ValueError):parse_vcv(raw)

def test_tsv_compression_schema_duplicates_and_exclusions():
    rows=b'#AlleleID\tVariationID\tAssembly\tGeneSymbol\tClinicalSignificance\n1\t1\tGRCh38\tBRCA1\tPathogenic\n1\t1\tGRCh38\tBRCA1\tPathogenic\n2\t2\tGRCh38\tBRCA2\tBenign\n3\t3\tunknown\tBRCA1\tBenign\n'
    out=[];counts=import_tsv(io.BytesIO(gzip.compress(rows)),'variant_summary',ImportCounts(),compressed=True,variation_ids={'1'},sink=out.append)
    assert counts['examined']==4 and counts['imported']==1 and counts['duplicates']==1 and counts['excluded']==1 and counts['invalid']==1
    assert out[0]['scope']=='VCV_summary_not_condition_specific'

def test_tsv_metadata_comments_and_scv_scope():
    data=b'##metadata\n#Some description\n#VariationID\tClinicalSignificance\tSCV\tSubmitter\n1\tBenign\tSCV000000001\tFixture\n'
    out=[];counts=import_tsv(io.BytesIO(data),'submission_summary',ImportCounts(),sink=out.append)
    assert counts['imported']==1 and out[0]['scope']=='SCV_submission'

def test_official_pair_conflict_no_means_minor_difference_not_yes():
    data=b'#NCBI_Variation_ID\tSubmitter1_SCV\tSubmitter2_SCV\tConflict_Reported\tSubmitter1_ClinSig\n1\tSCV000000001\tSCV000000002\tno\tBenign\n'
    out=[];import_tsv(io.BytesIO(data),'conflicting_interpretations',ImportCounts(),sink=out.append)
    assert not out[0]['official_conflict']

def test_gzip_expansion_and_long_lines_are_bounded():
    with pytest.raises(ValueError):list(tsv_rows(io.BytesIO(gzip.compress(b'x'*1_000_010)),compressed=True))
    with pytest.raises(ValueError):list(tsv_rows(io.BytesIO(b'abc\n'),max_uncompressed_bytes=2))

def test_deduplication_and_persistence_per_job_not_globally(tmp_path,variant):
    store=GenomicStore(tmp_path/'store');a=store.create('genomics',{});b=store.create('genomics',{})
    store.variant(a['id'],variant);store.variant(a['id'],variant);store.variant(b['id'],variant)
    assert len(store.variants(a['id']))==1 and len(store.variants(b['id']))==1
    with store.connect() as db:assert db.execute('SELECT COUNT(*) FROM submissions WHERE job_id=?',(a['id'],)).fetchone()[0]==3
    assert len(store.variants(a['id'],gene='BRCA1',classification='Conflicting'))==1
    assert store.variants(a['id'],gene="BRCA1' OR 1=1 --")==[]

def test_interrupted_job_retained_and_explicitly_resumable(tmp_path):
    store=GenomicStore(tmp_path/'s');job=store.create('genomics',{})
    other=GenomicStore(tmp_path/'s');assert other.get(job['id'])['status']=='interrupted'

@pytest.mark.parametrize('url',['http://rest.ensembl.org/info/data','https://evil.example/','https://rest.ensembl.org@evil.example/info/data','https://127.0.0.1:443/info/data','https://eutils.ncbi.nlm.nih.gov:444/entrez/eutils/efetch.fcgi'])
def test_only_official_https_sources(url):
    with pytest.raises(ValueError):validate_url(url)

def test_offline_cache_hash_change_is_rejected(tmp_path):
    c=PublicCache(tmp_path);url='https://rest.ensembl.org/info/data';k=hashlib.sha256(url.encode()).hexdigest()
    (tmp_path/(k+'.data')).write_bytes(b'{}');(tmp_path/(k+'.json')).write_text(json.dumps({'sha256':hashlib.sha256(b'{}').hexdigest()}))
    assert c.fetch(url,offline=True)[0]==b'{}'
    (tmp_path/(k+'.data')).write_bytes(b'[]')
    with pytest.raises(ValueError):c.fetch(url,offline=True)

def test_genomic_html_escapes_source_fields(variant):
    from genomics.report import html_report
    variant['germline']['description']='<script>alert(1)</script>'
    value=html_report(analyze([variant],{'genes':['BRCA1']}))
    assert '<script>alert' not in value and '&lt;script&gt;' in value

def test_evidence_types_remain_distinct():
    assert evidence('observed_data','x',['VCV000000001'])['kind']=='observed_data'
    with pytest.raises(ValueError):evidence('confirmed_pathogenic','x',['1'])
