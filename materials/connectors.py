# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Pinned official JARVIS/Figshare acquisition, no arbitrary URLs or cloud AI."""
import json,re,hashlib,os
from urllib.parse import urlsplit
from research_core.http import PublicCache

ARTICLE=6815699
VERSION=11
FILE_ID=64391379
METADATA=f'https://api.figshare.com/v2/articles/{ARTICLE}/versions/{VERSION}'
FILE_URL=f'https://ndownloader.figshare.com/files/{FILE_ID}'
MEMBER='jdft_3d-9-24-2025.json'
EXPECTED_MD5='c3179161ef0d029cf1fa70da463aac6e'

def source_policy(url):
    p=urlsplit(url)
    allowed=(p.hostname=='api.figshare.com' and re.fullmatch(r'/v2/articles/6815699(?:/versions/11)?',p.path) or p.hostname=='ndownloader.figshare.com' and p.path==f'/files/{FILE_ID}' or p.hostname=='s3-eu-west-1.amazonaws.com' and p.path==f'/pfigshare-u-files/{FILE_ID}/jdft_3d9242025.json.zip' or p.hostname in ('www.ctcms.nist.gov','jarvis.nist.gov') and re.fullmatch(r'/(?:~knc6/(?:static/JARVIS-DFT|jsmol)/JVASP-\d+\.(?:xml|html)|jarvisdft/JVASP-\d+/?)',p.path))
    if p.scheme!='https' or p.port not in (None,443) or p.username or p.password or p.fragment or not allowed:raise ValueError('Only pinned official JARVIS/Figshare HTTPS sources allowed')
    return p

def cache_at(root,max_bytes=200_000_000):return PublicCache(root,max_bytes=max_bytes,max_response_bytes=80_000_000,source_policy=source_policy,organization='NIST JARVIS-DFT / Figshare',parser_version='mde-0.1.0',user_agent='MattocciaLabs-ResearchEngines-MDE/0.1 (public research)')
class JarvisConnector:
    name='NIST JARVIS-DFT'
    def __init__(self,cache):self.cache=cache
    def acquire(self,offline=False):
        raw,metadata_source=self.cache.fetch(METADATA,offline=offline);meta=json.loads(raw)
        if meta.get('id')!=ARTICLE or meta.get('version')!=VERSION or meta.get('license',{}).get('name')!='CC BY 4.0':raise ValueError('Pinned dataset identity/version/reuse terms differ; review required')
        source=next((f for f in meta['files'] if f['id']==FILE_ID),None)
        if not source or source['download_url']!=FILE_URL or source['computed_md5']!=EXPECTED_MD5 or source['size']>80_000_000:raise ValueError('Pinned file metadata mismatch')
        path,record=self.cache.fetch(FILE_URL,offline=offline,as_path=True);md5=hashlib.md5()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(131072),b''):md5.update(chunk)
        if path.stat().st_size!=source['size'] or md5.hexdigest()!=EXPECTED_MD5:raise ValueError('Official file size/MD5 integrity mismatch')
        return path,{'dataset':'JARVIS-DFT 3D','article_id':ARTICLE,'article_version':VERSION,'doi':meta['doi'],'snapshot':source['name'],'snapshot_date':'2025-09-24','published_date':meta['published_date'],'license':meta['license'],'attribution':'NIST JARVIS-DFT / Kamal Choudhary et al.','file_id':FILE_ID,'url':FILE_URL,'zip_member':MEMBER,'official_md5':EXPECTED_MD5,'metadata_source':metadata_source,'source':record}
    def detail(self,jid,offline=False):
        if not re.fullmatch(r'JVASP-[1-9]\d{0,8}',jid):raise ValueError('Invalid JARVIS ID')
        return self.cache.fetch('https://www.ctcms.nist.gov/~knc6/jsmol/'+jid+'.html',offline=offline)

FUTURE_CONNECTORS={'Materials Project':{'implemented':False,'configured':bool(os.environ.get('MP_API_KEY') or os.environ.get('PMG_MAPI_KEY')),'reason':'Optional mp-api connector not qualified; JARVIS experiment is independent'},'other_sources':{'implemented':False}}


def parse_record_page(raw):
    """Read explicit source labels only; never execute HTML or remote scripts."""
    import html
    text=raw.decode('utf-8',errors='replace');text=re.sub(r'<script\b[\s\S]*?</script>',' ',text,flags=re.I);text=html.unescape(re.sub('<[^>]+>',' ',text));text=re.sub(r'\s+',' ',text)
    def field(pattern):
        m=re.search(pattern,text,re.I);return m.group(1) if m else None
    jid=field(r'JARVIS-ID:(JVASP-\d+)');formula=field(r'Chemical formula:([A-Za-z0-9.()]+)');gap=field(r'MBJ bandgap is\s*:\s*([0-9.+Ee-]+)\s*eV');slme=field(r'SLME is:\s*([0-9.+Ee-]+)')
    return {'jid':jid,'formula':formula,'mbj_gap_ev':float(gap) if gap else None,'slme_percent':float(slme) if slme and 'efficiency (in %)' in text else None,'page_reports_500nm_300K':'500 nm thickness and at 300 K' in text,'version':None}
