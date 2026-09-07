"""Exercise real view constructors in a child with a disposable database."""
import json
from pathlib import Path
import subprocess
import sys


def test_all_view_modules_construct_and_render(tmp_path):
    root = Path(__file__).resolve().parents[2]
    report = tmp_path / 'views.json'
    result = subprocess.run(
        [sys.executable, str(root / 'run.py'), '--self-test-views',
         '--self-test-report', str(report)],
        cwd=tmp_path, capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['ok'], data['errors']
    expected = {'views.' + p.stem for p in (root / 'views').glob('*.py')
                if p.stem != '__init__'}
    assert expected <= set(data['checked'])
    assert 'views.resumo_financeiro_view.ResumoFinanceiroView' in data['checked']
    assert not (tmp_path / 'financeiro.db').exists()
    assert not (tmp_path / 'database.log').exists()
    assert not (tmp_path / 'finance-assist.log').exists()
