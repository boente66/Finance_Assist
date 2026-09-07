import os
import subprocess
import sys

from utilitarios.makepdf import MakePDF


def test_child_receives_original_library_path_without_changing_parent():
    parent = dict(os.environ)
    supplied = {**parent, 'LD_LIBRARY_PATH': '/tmp/frozen-bundle',
                'LD_LIBRARY_PATH_ORIG': '/tmp/host-libraries'}
    child_env = MakePDF._external_environment(supplied)
    child = subprocess.run(
        [sys.executable, '-c', 'import os; print(os.environ.get("LD_LIBRARY_PATH"))'],
        env=child_env, capture_output=True, text=True, check=True,
    )
    assert child.stdout.strip() == '/tmp/host-libraries'
    assert supplied['LD_LIBRARY_PATH'] == '/tmp/frozen-bundle'
    assert dict(os.environ) == parent


def test_child_does_not_inherit_frozen_loader_when_no_original_path():
    assert MakePDF._external_environment({'LD_LIBRARY_PATH': '/tmp/bundle', 'PATH': '/usr/bin'}) == {'PATH': '/usr/bin'}
