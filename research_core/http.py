# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Bounded, hash-verified official public downloads. No arbitrary URL service."""
import hashlib,json,time,urllib.request,urllib.error
from urllib.parse import urlsplit
from pathlib import Path
from esae.scanner import no_symlink
from . import now

ALLOWED={'eutils.ncbi.nlm.nih.gov':('/entrez/eutils/esearch.fcgi','/entrez/eutils/esummary.fcgi','/entrez/eutils/efetch.fcgi'),
 'ftp.ncbi.nlm.nih.gov':('/pub/clinvar/',),
 'rest.ensembl.org':('/info/','/lookup/symbol/homo_sapiens/','/vep/human/','/sequence/region/human/')}
def validate_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.fragment or p.port not in (None,443) or p.hostname not in ALLOWED or not any(p.path.startswith(x) for x in ALLOWED[p.hostname]):raise ValueError('Only allowlisted official HTTPS sources')
    return p
class Redirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,policy=validate_url):self.policy=policy
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.policy(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)

class PublicCache:
    def __init__(self,root,max_bytes=200_000_000,max_response_bytes=12_000_000,retries=3,*,source_policy=validate_url,organization=None,parser_version='gee-0.1.0',user_agent='MattocciaLabs-ResearchEngines-GEE/0.1 (public scientific research)'):
        self.root=no_symlink(Path(root)).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.max_bytes=max_bytes;self.max_response=max_response_bytes;self.retries=retries;self.last={};self.network_bytes=0
        self.source_policy=source_policy;self.organization=organization;self.parser_version=parser_version;self.user_agent=user_agent
        self.opener=urllib.request.build_opener(Redirect(source_policy))
    @staticmethod
    def file_hash(path):
        value=hashlib.sha256()
        with path.open('rb') as stream:
            for data in iter(lambda:stream.read(131072),b''):value.update(data)
        return value.hexdigest()
    def fetch(self,url,*,offline=False,refresh=False,as_path=False):
        p=self.source_policy(url);key=hashlib.sha256(url.encode()).hexdigest();dest=self.root/(key+'.data');meta=self.root/(key+'.json')
        for path in (dest,meta):no_symlink(path)
        if dest.exists() and meta.exists() and not refresh:
            if dest.stat().st_size>self.max_response:raise ValueError('Cached response exceeds configured limit')
            record=json.loads(meta.read_text())
            if self.file_hash(dest)!=record['sha256']:raise ValueError('Cached source hash mismatch')
            return (dest if as_path else dest.read_bytes()),record
        if offline:raise ValueError('Frozen source is unavailable in verified cache')
        part=self.root/(key+'.part');partial_meta=self.root/(key+'.partial.json');no_symlink(part);no_symlink(partial_meta)
        for attempt in range(self.retries):
            cached_bytes=sum(p.stat().st_size for p in self.root.glob('*.data') if p!=dest);started=time.monotonic()
            wait=max(0,.45-(time.monotonic()-self.last.get(p.hostname,0)))
            if wait:time.sleep(wait)
            self.last[p.hostname]=time.monotonic()
            headers={'User-Agent':self.user_agent,'Accept-Encoding':'identity'}
            offset=part.stat().st_size if part.exists() else 0
            validator=json.loads(partial_meta.read_text()).get('validator') if partial_meta.exists() else None
            if offset and validator:headers.update({'Range':'bytes='+str(offset)+'-','If-Range':validator})
            elif offset:offset=0
            try:
                with self.opener.open(urllib.request.Request(url,headers=headers),timeout=40) as response:
                    if response.status not in (200,206):raise ValueError('Unexpected source status')
                    if response.status==206:
                        if not response.headers.get('Content-Range','').startswith('bytes '+str(offset)+'-'):raise ValueError('Incompatible resumed range')
                        current=response.headers.get('ETag') or response.headers.get('Last-Modified')
                        if offset and current!=validator:raise ValueError('Source changed during resumed download')
                    else:offset=0
                    partial_meta.write_text(json.dumps({'validator':response.headers.get('ETag') or response.headers.get('Last-Modified'),'url':url})+'\n')
                    length=int(response.headers.get('Content-Length','0'))
                    if offset+length>self.max_response:raise ValueError('Response exceeds configured download limit')
                    with part.open('ab' if offset else 'wb') as out:
                        while data:=response.read(65536):
                            self.network_bytes+=len(data);offset+=len(data)
                            if offset>self.max_response or self.network_bytes>self.max_bytes or cached_bytes+offset>self.max_bytes:raise ValueError('Configured acquisition limit exceeded')
                            if time.monotonic()-started>180:raise ValueError('Download time limit exceeded')
                            out.write(data)
                    if length and part.stat().st_size!=(int(response.headers.get('Content-Range','0-0/0').split('/')[-1]) if response.status==206 else length):raise ValueError('Incomplete response')
                    record={'id':key,'url':url,'organization':self.organization or ('NCBI ClinVar' if 'ncbi.nlm.nih.gov' in p.hostname else 'EMBL-EBI Ensembl'),'acquired_at':now(),'release_date':response.headers.get('Last-Modified'),'etag':response.headers.get('ETag'),'server_date':response.headers.get('Date'),'sha256':self.file_hash(part),'bytes':part.stat().st_size,'http_status':response.status,'parser_version':self.parser_version,'record_counts':None,'errors':[]}
                    part.replace(dest);dest.chmod(0o600);meta.write_text(json.dumps(record,indent=2)+'\n');meta.chmod(0o600);return (dest if as_path else dest.read_bytes()),record
            except (urllib.error.URLError,TimeoutError,OSError) as error:
                with (self.root/'acquisition-errors.jsonl').open('a') as log:log.write(json.dumps({'url':url,'attempt':attempt+1,'at':now(),'status':getattr(error,'code',None),'error':str(error)[:400]})+'\n')
                if isinstance(error,urllib.error.HTTPError) and error.code not in (429,500,502,503,504):raise
                if attempt+1==self.retries:raise
                retry_after=error.headers.get('Retry-After','') if isinstance(error,urllib.error.HTTPError) else ''
                time.sleep(min(15,int(retry_after)) if retry_after.isdigit() else min(8,2**attempt))
        raise RuntimeError('Acquisition did not complete')
