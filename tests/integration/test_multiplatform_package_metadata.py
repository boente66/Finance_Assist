from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_workflow_gera_artefatos_linux_e_windows():
    workflow = (ROOT / ".github/workflows/build-multiplatform.yml").read_text(encoding="utf-8")
    assert "runs-on: ubuntu-22.04" in workflow
    assert "runs-on: windows-2022" in workflow
    assert "packaging/linux/build_deb.sh" in workflow
    assert "packaging\\windows\\build_windows.ps1" in workflow
    assert workflow.count("actions/upload-artifact@v4") == 2


def test_pacote_windows_e_portavel_e_nao_embute_dados_locais():
    script = (ROOT / "packaging/windows/build_windows.ps1").read_text(encoding="utf-8")
    assert "FinanceAssist-test.exe" in script
    assert "README.md" in script and "LICENSE" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    forbidden = ("financeiro.db", "backups", ".venv\\Lib", "configuracoes.json")
    assert all(item not in script for item in forbidden)


def test_especificacao_gera_nome_comercial_sem_dados_do_usuario():
    spec = (ROOT / "ControleFinanceiro-teste.spec").read_text(encoding="utf-8")
    assert "name='FinanceAssist-test'" in spec
    assert "'pytest', '_pytest'" in spec
    assert "financeiro.db" not in spec
    assert "configuracoes.json" not in spec
