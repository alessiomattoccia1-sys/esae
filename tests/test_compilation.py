# Copyright 2026 Alessio Mattoccia
import json
from pathlib import Path
import pytest
from esae.scanner import inventory,snapshot,InputError
from esae.compilation import sanitize_arguments,prepare_database

@pytest.mark.parametrize('flag',['@args','-fplugin=/tmp/x','-Xclang','-load','-include','-imacros','-fmodule-file=x','-ivfsoverlay','--sysroot=/x','-B/tmp'])
def test_dangerous_flags_rejected(flag,repo,tmp_path):
    inv=inventory(repo);snapshot(inv,tmp_path/'snap')
    with pytest.raises(InputError):sanitize_arguments(['arbitrary-compiler',flag,'main.c'],repo,inv,tmp_path/'snap')

def test_cdb_data_only_and_safe_args(repo,tmp_path):
    (repo/'include').mkdir();(repo/'include/a.h').write_text('int x;')
    payload=[{'directory':'.','file':'main.c','command':'evil-command -std=c11 -Iinclude -DFEATURE=1 -Wall -c main.c -o /tmp/never.o'}]
    (repo/'compile_commands.json').write_text(json.dumps(payload))
    inv=inventory(repo);snap=tmp_path/'snap';snapshot(inv,snap)
    entries,errors,ignored=prepare_database(inv,snap,tmp_path/'db')
    assert not errors and len(entries)==1
    args=entries[0]['arguments'];assert args[0]=='clang' and '-DFEATURE=1' in args
    assert '-Wall' not in args and 'evil-command' not in args and '/tmp/never.o' not in args
    assert any(x['ignored']=='-Wall' for x in ignored)

def test_external_include_and_translation_unit_rejected(repo,tmp_path):
    (repo/'compile_commands.json').write_text(json.dumps([{'directory':'.','file':'main.c','arguments':['cc','-I/usr/include','main.c']}]))
    inv=inventory(repo);snapshot(inv,tmp_path/'snap')
    entries,errors,_=prepare_database(inv,tmp_path/'snap',tmp_path/'db')
    assert not entries and errors

def test_missing_database_is_explicit(repo,tmp_path):
    inv=inventory(repo);snapshot(inv,tmp_path/'snap')
    entries,errors,_=prepare_database(inv,tmp_path/'snap',tmp_path/'db')
    assert len(entries)==1 and 'fallback' in errors[0]
