import tarfile
import pytest
from scripts.setup import validate_member

def test_official_archive_root_directory_accepted():
    m=tarfile.TarInfo('cppcheck-2.22.0');m.type=tarfile.DIRTYPE
    validate_member(m)
    validate_member(tarfile.TarInfo('cppcheck-2.22.0/lib/source.cpp'))

def test_archive_traversal_rejected():
    with pytest.raises(RuntimeError):validate_member(tarfile.TarInfo('cppcheck-2.22.0/../escape'))

def test_archive_symlink_rejected():
    m=tarfile.TarInfo('cppcheck-2.22.0/link');m.type=tarfile.SYMTYPE;m.linkname='/etc/passwd'
    with pytest.raises(RuntimeError):validate_member(m)
