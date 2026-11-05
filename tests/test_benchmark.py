import pytest
from benchmarks.reproduce_cppcheck import validate_checkpoint

def test_checkpoint_reuses_only_matching_profile_and_toolchain():
    saved={'profile_sha256':'source-and-config','tools':{'cppcheck':{'sha256':'binary'}}}
    validate_checkpoint(saved,'source-and-config',{'cppcheck':{'sha256':'binary'}})
    with pytest.raises(ValueError):validate_checkpoint(saved,'other-input',saved['tools'])
    with pytest.raises(ValueError):validate_checkpoint(saved,'source-and-config',{'cppcheck':{'sha256':'changed'}})
