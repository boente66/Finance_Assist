import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from core.background_manager import BackgroundManager
from core.session import Session
from database.database import Database
from views.painel_account import PainelAccount
from views.painel_fatura import PainelFatura
from views.transacao_view import TransacaoView


def _app():
    return QApplication.instance() or QApplication([])


def _database(tmp_path, monkeypatch):
    path = str(tmp_path / "financeiro.db")
    monkeypatch.setattr("database.database.get_db_path", lambda: path)
    db = Database(path)
    user = db.execute_insert(
        "INSERT INTO usuarios (Nome, Login, Senha, Nivel_Acesso) VALUES ('Admin','admin','hash','admin')"
    )
    account = db.execute_insert(
        "INSERT INTO contas (Nome_Conta, Tipo, Saldo_Atual, ID_Usuario) VALUES ('Conta','Corrente',100,?)",
        (user,),
    )
    card = db.execute_insert(
        "INSERT INTO credito (Nome, Limite, Dia_Fechamento, Dia_Vencimento, ID_Usuario) VALUES ('Cartão',1000,20,27,?)",
        (user,),
    )
    Session.set_usuario({"ID_Usuario": user, "Nome": "Admin", "Nivel_Acesso": "admin"})
    return db, path, account, card


def test_tabelas_usam_menu_contextual_sem_botao_acoes(tmp_path, monkeypatch):
    app = _app()
    db, _, account, card = _database(tmp_path, monkeypatch)
    account_view = PainelAccount()
    account_view.set_conta({"ID_Conta": account, "Nome_Conta": "Conta"})
    invoice_view = PainelFatura()
    invoice_view.set_cartao({"ID_Cartao": card, "Nome": "Cartão", "Limite": 1000})
    assert account_view.table.contextMenuPolicy() == Qt.CustomContextMenu
    assert invoice_view.table.contextMenuPolicy() == Qt.CustomContextMenu
    assert not hasattr(invoice_view, "btn_acoes")
    assert not hasattr(account_view, "btn_editar")
    assert account_view.btn_prev.objectName() == "circularNavButton"
    assert invoice_view.btn_next.width() == 38
    account_view.close(); invoice_view.close(); app.processEvents(); db.close()


def test_backup_automatico_usa_chave_local_e_preserva_banco(tmp_path, monkeypatch):
    app = _app()
    db, path, _, _ = _database(tmp_path, monkeypatch)
    data_dir = tmp_path / "dados"
    monkeypatch.setattr("core.background_manager.DATA_DIR", str(data_dir))
    monkeypatch.setattr("core.background_manager.get_db_path", lambda: path)
    monkeypatch.setattr("core.background_manager.carregar_config", lambda: {
        "backup_retencao": 2,
    })
    monkeypatch.setattr("core.background_manager.salvar_config", lambda config: True)
    manager = BackgroundManager()
    manager.timer.stop()
    manager._create_backup()
    backups = list((data_dir / "backups" / "automaticos").glob("*.kp"))
    assert len(backups) == 1
    key = data_dir / ".automatic_backup_key"
    assert key.exists() and key.read_text().strip()
    if os.name != "nt":
        assert key.stat().st_mode & 0o077 == 0
    assert Database(path).fetch_one("SELECT Nome FROM usuarios WHERE ID_Usuario=1")["Nome"] == "Admin"
    manager.deleteLater(); app.processEvents(); db.close()


def test_troca_de_painel_oculta_imediatamente_a_tela_anterior(tmp_path, monkeypatch):
    app = _app()
    db, _, _, _ = _database(tmp_path, monkeypatch)
    view = TransacaoView()
    view.show(); app.processEvents()
    boas_vindas = view.painel_ativo
    view.selecionar_cartao(view.lista_cartoes.item(0))
    app.processEvents()
    assert not boas_vindas.isVisible()
    assert isinstance(view.painel_ativo, PainelFatura)
    assert view.painel_ativo.isVisibleTo(view)
    view.close(); app.processEvents(); db.close()
