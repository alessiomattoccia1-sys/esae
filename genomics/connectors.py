# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Official ClinVar/Ensembl adapters; future provider contract, not fake connectors."""
import json,re
from typing import Protocol
from urllib.parse import urlencode,quote

class EvidenceConnector(Protocol):
    name:str
    def metadata(self)->dict:...

class ClinVar:
    name='NCBI ClinVar'
    base='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    def __init__(self,cache):self.cache=cache
    def search(self,gene):
        if not re.fullmatch('[A-Z][A-Z0-9.-]{0,19}',gene):raise ValueError('Invalid official gene symbol')
        query=gene+'[gene] AND single_gene[prop]'
        url=self.base+'esearch.fcgi?'+urlencode({'db':'clinvar','term':query,'retmode':'json','retmax':100000})
        raw,source=self.cache.fetch(url);data=json.loads(raw)['esearchresult']
        ids=sorted(set(int(v) for v in data['idlist']));count=int(data['count'])
        if len(ids)!=count:raise ValueError('Search result truncated; lower scope instead of biased selection')
        return ids,{'gene':gene,'query':query,'count':count,'source':source}
    def vcv(self,variation_id):
        if not re.fullmatch(r'[1-9]\d{0,11}',str(variation_id)):raise ValueError('Invalid Variation ID')
        # Current official API requires the variation-id flag for numeric ids.
        url=self.base+'efetch.fcgi?'+urlencode({'db':'clinvar','rettype':'vcv','is_variationid':'true','retmode':'xml','id':str(variation_id)})
        return self.cache.fetch(url)
    def rcv(self,accession):
        if not re.fullmatch(r'RCV\d{9,12}(?:\.\d+)?',accession):raise ValueError('Invalid RCV accession')
        return self.cache.fetch(self.base+'efetch.fcgi?'+urlencode({'db':'clinvar','rettype':'clinvarset','retmode':'xml','id':accession}))

class Ensembl:
    name='Ensembl REST / VEP'
    base='https://rest.ensembl.org/'
    def __init__(self,cache):self.cache=cache
    def metadata(self):
        raw,source=self.cache.fetch(self.base+'info/data?content-type=application/json');return json.loads(raw),source
    def gene(self,symbol):
        if not re.fullmatch('[A-Z][A-Z0-9.-]{0,19}',symbol):raise ValueError('Invalid gene symbol')
        raw,source=self.cache.fetch(self.base+'lookup/symbol/homo_sapiens/'+quote(symbol)+'?content-type=application/json')
        return json.loads(raw),source
    def vep_snv(self,location):
        if location.get('assembly')!='GRCh38':raise ValueError('GRCh38 required; no implicit lift-over')
        chrom=str(location['chromosome']);pos=int(location['position']);ref=location['reference'];alt=location['alternate']
        if not re.fullmatch(r'(?:[1-9]|1\d|2[0-2]|X|Y|MT)',chrom) or pos<1 or not re.fullmatch('[ACGT]',ref) or not re.fullmatch('[ACGT]',alt) or ref==alt:raise ValueError('Only exact GRCh38 SNV representations qualified')
        region=f'{chrom}:{pos}-{pos}:1';url=self.base+'vep/human/region/'+quote(region,safe=':')+'/'+alt+'?'+urlencode({'content-type':'application/json','canonical':1,'check_ref':1})
        raw,source=self.cache.fetch(url);values=json.loads(raw)
        if not isinstance(values,list) or len(values)!=1:raise ValueError('Ambiguous VEP response')
        v=values[0]
        if v.get('assembly_name')!='GRCh38' or str(v.get('seq_region_name'))!=chrom or v.get('start')!=pos or v.get('end')!=pos or v.get('strand')!=1 or v.get('allele_string')!=ref+'/'+alt:raise ValueError('VEP identity/reference/assembly mismatch')
        return {'status':'matched','matching_method':'Exact GRCh38 chromosome/1-based position/reference/alternate, forward strand','location':location,'most_severe_consequence':v.get('most_severe_consequence'),'transcripts':[{'gene_id':x.get('gene_id'),'gene_symbol':x.get('gene_symbol'),'transcript_id':x.get('transcript_id'),'consequence_terms':x.get('consequence_terms',[]),'biotype':x.get('biotype'),'canonical':x.get('canonical',0)} for x in v.get('transcript_consequences',[])],'source':source}

FUTURE_PROVIDERS={'dbSNP':'not_implemented','NCBI Gene':'not_implemented','GEO':'not_implemented'}
