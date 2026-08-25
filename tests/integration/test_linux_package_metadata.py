from pathlib import Path

from core.version import APP_VERSION, DEBIAN_VERSION


ROOT = Path(__file__).resolve().parents[2]


def test_versao_de_teste_possui_formatos_coerentes():
    assert APP_VERSION == "2.1.0-test.2"
    assert DEBIAN_VERSION == "2.1.0~test2"


def test_metadados_debian_declaram_pacote_de_teste():
    control = (ROOT / "packaging/linux/control.in").read_text(encoding="utf-8")
    desktop = (ROOT / "packaging/linux/finance-assist.desktop").read_text(encoding="utf-8")
    assert "Package: finance-assist-test" in control
    assert "versão de teste" in control
    assert "Name=Finance Assist (Teste)" in desktop
    assert "Exec=/usr/bin/finance-assist-test" in desktop
    assert "Ubuntu 22.04 LTS ou posterior" in control


def test_script_nao_embute_banco_backup_ou_ambiente_virtual():
    script = (ROOT / "packaging/linux/build_deb.sh").read_text(encoding="utf-8")
    assert "financeiro.db" not in script
    assert "backup_dir" not in script
    assert "install -m 0644 \"$PROJECT_ROOT/LICENSE\"" in script
    assert "assets/icons/finance_assist.svg" in script
    assert "dist/FinanceAssist-test" in script
