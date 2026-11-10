# Copyright 2026 Alessio Mattoccia
from pathlib import Path
import pytest
from esae.scanner import inventory,validate_root,InputError,snapshot,read_regular

def test_lines_and_extensions(repo):
    (repo/'main.c').write_text('// comment\n\nint x;\n')
    for suffix in ['.h','.hpp','.cpp','.cc','.cxx']:(repo/('f'+suffix)).write_text('int n;\n')
    (repo/'blob.c').write_bytes(b'\0bad');(repo/'note.txt').write_text('not source')
    inv=inventory(repo)
    assert len(inv.files)==6
    assert inv.public()['lines']==8 and inv.public()['nonblank_lines']==7
    assert {'path':'blob.c','reason':'binary'} in inv.excluded

def test_excludes_and_snapshot(repo,tmp_path):
    (repo/'vendor').mkdir();(repo/'vendor/v.c').write_text('bad')
    (repo/'CMakeLists.txt').write_text('do not execute')
    inv=inventory(repo);snapshot(inv,tmp_path/'snap')
    assert len(inv.files)==1 and inv.build_systems==['CMakeLists.txt']
    assert not (tmp_path/'snap/CMakeLists.txt').exists()
    assert (tmp_path/'snap/main.c').read_bytes()==(repo/'main.c').read_bytes()

def test_symlink_not_followed(repo,tmp_path):
    outside=tmp_path/'secret.h';outside.write_text('secret')
    (repo/'secret.h').symlink_to(outside)
    assert 'secret.h' not in inventory(repo).files
    with pytest.raises(InputError):read_regular(repo/'secret.h',1000)

def test_root_boundary_and_parent_symlink(repo,tmp_path):
    assert validate_root(repo,(repo,))==repo
    with pytest.raises(InputError):validate_root(tmp_path,(repo,))
    link=tmp_path/'alias';link.symlink_to(repo,target_is_directory=True)
    with pytest.raises(InputError):validate_root(link,(repo,))
    with pytest.raises(InputError):validate_root('/',(Path('/'),))

def test_file_and_inventory_caps(repo):
    (repo/'main.c').write_bytes(b'x'*2_000_001)
    with pytest.raises(InputError):inventory(repo)
    (repo/'main.c').write_text('a')
    (repo/'second.c').write_text('a')
    with pytest.raises(InputError):inventory(repo,max_files=1)
