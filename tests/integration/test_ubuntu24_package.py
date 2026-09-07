"""Contract for the separate Noble artifact; CI executes the actual DEB."""
from pathlib import Path
import os
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_noble_variant_keeps_identity_and_rebuilds():
    script = (ROOT / 'packaging/linux/build_deb.sh').read_text()
    control = (ROOT / 'packaging/linux/control.in').read_text()
    assert 'Package: finance-assist-test' in control
    assert '${ASSET_VERSION}_ubuntu24.04_${ARCH}.deb' in script
    assert '${DEBIAN_VERSION}+ubuntu24.04.1' in script
    assert 'LIBC_DEPENDENCY="libc6 (>= 2.39)"' in script
    assert 'GLIB_DEPENDENCY="libglib2.0-0t64"' in script
    assert 'exige recompilação do executável' in script
    assert '"${VERSION_ID:-}" != "24.04"' in script


@pytest.mark.skipif(os.name != 'posix', reason='Build DEB requires Linux')
def test_unknown_base_is_rejected_before_build():
    result = subprocess.run(['bash', str(ROOT / 'packaging/linux/build_deb.sh')],
                            env={**os.environ, 'FINANCE_ASSIST_DEB_BASE': 'invalid'},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'Base de pacote desconhecida' in result.stderr


def test_noble_workflow_tests_installed_binary_and_storage():
    workflow = (ROOT / '.github/workflows/build-ubuntu24.yml').read_text()
    for required in ('runs-on: ubuntu-24.04', 'FINANCE_ASSIST_DEB_BASE: ubuntu24.04',
                     'python -m pytest -q', 'sudo apt install -y ./finance-assist_',
                     '--self-test-views --self-test-ocr', 'sha256sum -c',
                     'noble-clean-home', 'PRESERVAR', 'PRAGMA integrity_check'):
        assert required in workflow
