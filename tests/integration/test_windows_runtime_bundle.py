import runpy
from pathlib import Path

import pytest


replace_runtime = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                                    'packaging/windows/runtime_binaries.py'))['replace_runtime']


def test_replaces_nested_and_root_runtime_preserving_other_binaries(tmp_path):
    for name in ('msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'):
        (tmp_path / name).touch()
    binaries = [('msvcp140.dll', 'old', 'BINARY'),
                ('PyQt5/Qt5/bin/msvcp140.dll', 'old-qt', 'BINARY'),
                ('other.dll', 'original', 'BINARY')]
    result = replace_runtime(binaries, tmp_path)
    assert result[:2] == [(item[0], str(tmp_path / 'msvcp140.dll'), 'BINARY') for item in binaries[:2]]
    assert result[2] == binaries[2]
    assert len(result) == 5


def test_missing_runtime_fails_build(tmp_path):
    with pytest.raises(RuntimeError, match='incompleto'):
        replace_runtime([], tmp_path)
