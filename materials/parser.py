# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Whitelisted physical properties and crystal validation; no simulation or ML."""
import json,re,math,hashlib,zipfile,io
from collections import Counter
import numpy as np
from jarvis.core.composition import Composition
from jarvis.core.specie import Specie
from .connectors import MEMBER
PARSER_VERSION='mde-0.1.0'
MISSING={'','na','nan','none','null','n/a'}
UNITS={'bandgap':'eV','formation':'eV/atom','hull':'eV/atom','slme':'%','dielectric':'dimensionless','lattice':'angstrom'}

def quantity(value,unit,kind):
    if value is None or isinstance(value,str) and value.strip().lower() in MISSING:return None
    if isinstance(value,bool):raise ValueError('Boolean is not a physical quantity')
    try:x=float(value)
    except (ValueError,TypeError):raise ValueError('Invalid numeric field')
    if not math.isfinite(x):return None
    scales={'bandgap':{'eV':1,'meV':.001},'formation':{'eV/atom':1,'meV/atom':.001},'hull':{'eV/atom':1,'meV/atom':.001},'slme':{'%':1,'fraction':100},'dielectric':{'dimensionless':1},'lattice':{'angstrom':1,'nm':10}}
    if kind not in scales or unit not in scales[kind]:raise ValueError('Incompatible or unknown units')
    x*=scales[kind][unit]
    if kind in ('bandgap','hull','dielectric') and x<0:raise ValueError('Negative '+kind)
    if kind=='slme' and not 0<=x<=100:raise ValueError('SLME percentage outside bounds')
    return x

def composition(formula):
    if not isinstance(formula,str) or not 1<=len(formula)<=200 or not re.fullmatch(r'[A-Za-z0-9.()]+',formula):raise ValueError('Invalid formula')
    tokens=re.findall(r'[A-Z][a-z]?|\d+(?:\.\d+)?|[()]',formula)
    if ''.join(tokens)!=formula:raise ValueError('Unsupported formula notation')
    stack=[{}];i=0
    while i<len(tokens):
        t=tokens[i]
        if t=='(':stack.append({});i+=1;continue
        if t==')':
            if len(stack)==1 or not stack[-1]:raise ValueError('Unbalanced formula')
            group=stack.pop();i+=1;factor=1.
            if i<len(tokens) and re.fullmatch(r'\d+(?:\.\d+)?',tokens[i]):factor=float(tokens[i]);i+=1
            for k,v in group.items():stack[-1][k]=stack[-1].get(k,0)+v*factor
            continue
        if not re.fullmatch('[A-Z][a-z]?',t):raise ValueError('Invalid formula token')
        i+=1;factor=1.
        if i<len(tokens) and re.fullmatch(r'\d+(?:\.\d+)?',tokens[i]):factor=float(tokens[i]);i+=1
        stack[-1][t]=stack[-1].get(t,0)+factor
    if len(stack)!=1:raise ValueError('Unbalanced formula')
    c=Composition(stack[0]);values=dict(c.to_dict())
    if not values or len(values)>20 or any(not re.fullmatch('[A-Z][a-z]?',k) or not math.isfinite(float(v)) or v<=0 or v>10000 for k,v in values.items()):raise ValueError('Invalid stoichiometry')
    for element in values:Specie(element).Z
    total=sum(values.values());return c.reduced_formula,{k:round(v/total,12) for k,v in sorted(values.items())}

def chemical_family(elements):
    e=set(elements);groups=[]
    for name,group in [('oxide',{'O'}),('chalcogenide',{'S','Se','Te'}),('halide',{'F','Cl','Br','I'}),('pnictide',{'N','P','As','Sb'})]:
        if e&group:groups.append(name)
    return '+'.join(groups) if groups else 'other'

def normalize(row):
    if not isinstance(row,dict) or not re.fullmatch(r'JVASP-[1-9]\d{0,8}',str(row.get('jid',''))):raise ValueError('invalid_jid')
    formula,frac=composition(row.get('formula'));a=row.get('atoms')
    if not isinstance(a,dict):raise ValueError('missing_structure')
    elements=a.get('elements');cartesian=a.get('cartesian')
    if not isinstance(elements,list) or not 1<=len(elements)<=512 or not isinstance(cartesian,bool):raise ValueError('invalid_structure_scope')
    counts=Counter(elements)
    if set(counts)!=set(frac) or any(abs(counts[e]/len(elements)-frac[e])>1e-8 for e in counts):raise ValueError('formula_structure_mismatch')
    lattice=np.asarray(a.get('lattice_mat'),dtype=float);coords=np.asarray(a.get('coords'),dtype=float)
    if lattice.shape!=(3,3) or coords.shape!=(len(elements),3) or not np.isfinite(lattice).all() or not np.isfinite(coords).all():raise ValueError('invalid_crystal_arrays')
    det=float(np.linalg.det(lattice))
    if abs(det)<1e-6 or abs(det)>1e8 or np.max(np.abs(coords))>1e6:raise ValueError('invalid_cell_geometry')
    fractional=coords@np.linalg.inv(lattice) if cartesian else coords
    structure={'lattice_angstrom':lattice.tolist(),'fractional_coordinates':np.mod(fractional,1).round(12).tolist(),'elements':elements,'volume_angstrom3':abs(det),'atoms':len(elements),'coordinates':'fractional; input lattice angstrom','source_cartesian':cartesian}
    structure['sha256']=hashlib.sha256(json.dumps(structure,sort_keys=True).encode()).hexdigest()
    anomalies=[];props={}
    mapping={'gap_mbj':('mbj_bandgap','bandgap'),'gap_opt':('optb88vdw_bandgap','bandgap'),'formation_ev_atom':('formation_energy_peratom','formation'),'hull_ev_atom':('ehull','hull'),'slme_percent':('slme','slme')}
    for key,(source,kind) in mapping.items():
        try:props[key]=quantity(row.get(source),UNITS[kind],kind)
        except ValueError as exc:props[key]=None;anomalies.append(source+':'+str(exc))
    for prefix in ('eps','meps'):
        values=[]
        for axis in ('x','y','z'):
            try:values.append(quantity(row.get(prefix+axis),'dimensionless','dielectric'))
            except ValueError as exc:values.append(None);anomalies.append(prefix+axis+':'+str(exc))
        props[prefix+'_diagonal']=values
    method=str(row.get('func','unknown'))[:80]
    return {'jid':row['jid'],'formula':formula,'source_formula':row['formula'],'composition':frac,'elements':sorted(frac),'n_elements':len(frac),'chemical_family':chemical_family(frac),'crystal_system':str(row.get('crys','unknown'))[:60],'space_group':str(row.get('spg_number','unknown'))[:10],'structure':structure,'properties':props,'methods':{'gap_mbj':'TB-mBJ','gap_opt':method,'formation_and_hull':method,'slme':'Reported JARVIS SLME / TB-mBJ documentation; per-record thickness/temperature not encoded','dielectric_eps':method,'dielectric_meps':'TB-mBJ'},'optical_conditions':{'thickness_m':None,'temperature_k':None,'status':'not encoded per record; not independently verified'},'absorption_spectrum_available':False,'anomalies':anomalies,'source_reference':str(row.get('reference',''))[:120],'url':'https://www.ctcms.nist.gov/~knc6/jsmol/'+row['jid']+'.html'}

def records(path,max_rows=150000,max_expanded=500_000_000):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if names!=[MEMBER]:raise ValueError('Unexpected archive members')
        info=z.getinfo(MEMBER)
        if info.file_size>max_expanded or info.compress_size==0 or info.file_size/info.compress_size>100:raise ValueError('Archive expansion limit exceeded')
        with z.open(info) as stream:
            yield from json_array(stream,max_rows=max_rows)


def json_array(stream,max_rows=150000,max_record_chars=4_000_000):
    """Stream objects using the same NaN-tolerant JSON semantics as official Python
    loading, but map nonstandard numeric constants to missing (never zero)."""
    src=io.TextIOWrapper(stream,encoding='utf-8');buffer='';eof=False;decoder=json.JSONDecoder(parse_constant=lambda _:None)
    def fill():
        nonlocal buffer,eof
        value=src.read(65536);buffer+=value;eof=not value
        if len(buffer)>max_record_chars:raise ValueError('JSON record expansion limit exceeded')
    def token():
        nonlocal buffer
        buffer=buffer.lstrip()
        while not buffer and not eof:fill();buffer=buffer.lstrip()
    token()
    if not buffer.startswith('['):raise ValueError('Expected a dataset JSON array')
    buffer=buffer[1:];count=0;expect_object=True
    while True:
        token()
        if buffer.startswith(']'):
            if not expect_object:pass
            elif count:raise ValueError('Trailing comma in dataset')
            buffer=buffer[1:];token()
            if buffer:raise ValueError('Trailing dataset data')
            return
        if not expect_object:
            if not buffer.startswith(','):raise ValueError('Missing dataset separator')
            buffer=buffer[1:];expect_object=True;continue
        try:row,end=decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            if eof:raise ValueError('Incomplete or invalid source JSON')
            fill();continue
        if not isinstance(row,dict):raise ValueError('Material must be a JSON object')
        buffer=buffer[end:];count+=1
        if count>max_rows:raise ValueError('Material record limit exceeded')
        expect_object=False;yield row
