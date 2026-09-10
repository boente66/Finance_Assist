import os

import pytest

from core.session import Session
from controllers.user_controller import UserController
from database.database import Database


PASSWORD = 'Senha-de-teste-2026'


def test_profile_requires_confirmation_and_logs_out_after_closure(account, monkeypatch):
    from PyQt5.QtWidgets import QApplication, QMessageBox, QInputDialog
    from views.perfil_view import PerfilView
    app = QApplication.instance() or QApplication([])
    controller, user, _ = account
    view = PerfilView(user_controller=controller)
    exits = []
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    view.logout_requested.connect(lambda: exits.append(True))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    view.close_account_button.click()
    assert controller.get_user_by_id(user['ID_Usuario'])['Ativo'] == 1
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args: (PASSWORD, True))
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: QMessageBox.Ok)
    view.close_account_button.click()
    assert exits == [True]
    assert warnings == []
    assert controller.get_user_by_id(user['ID_Usuario'])['Ativo'] == 0
    app.processEvents()
    view.close()


@pytest.fixture
def account(tmp_path, monkeypatch):
    path = str(tmp_path / 'accounts.db')
    monkeypatch.setattr('database.database.get_db_path', lambda: path)
    controller = UserController()
    model = controller.service.user_model
    for login, role in (('admin', 'admin'), ('cliente', 'usuario')):
        model.add_user({'Nome': login, 'Login': login, 'Email': login + '@example.invalid',
                        'Senha': PASSWORD, 'Nivel_Acesso': role})
    user = model.get_user_by_login('cliente')
    previous = Session.get_usuario()
    Session.set_usuario(user)
    model.execute_query("INSERT INTO contas (ID_Conta,Nome_Conta,ID_Usuario) VALUES (1,'Conta',?)", (user['ID_Usuario'],))
    model.execute_query("""INSERT INTO transacoes
        (ID_Conta,ID_Usuario,Tipo,Descricao,Valor,Data) VALUES (1,?,'Receita','Preservar',100,'2026-01-01')""", (user['ID_Usuario'],))
    yield controller, user, path
    Session.set_usuario(previous)
    model.close()
    controller.service.password_reset_model.close()


def test_close_access_preserves_history_and_invalidates_reset(account):
    controller, user, _ = account
    service = controller.service
    token = service.password_reset_model.create_token(user['ID_Usuario'])
    before = service.user_model.fetch_all('SELECT * FROM transacoes')
    assert controller.delete_own_account(PASSWORD)
    assert Session.get_usuario() is None
    assert service.user_model.get_user_by_id(user['ID_Usuario'])['Ativo'] == 0
    assert service.user_model.fetch_all('SELECT * FROM transacoes') == before
    assert controller.authenticate_user('cliente', PASSWORD) is None
    assert not controller.reset_password_with_token(token, 'Outra-senha-segura')


def test_password_identity_and_last_admin_are_required(account):
    controller, user, _ = account
    assert not controller.delete_own_account('errada')
    assert not controller.service.delete_own_account(1, PASSWORD, user)
    admin = controller.get_user_by_id(1)
    Session.set_usuario(admin)
    assert not controller.delete_own_account(PASSWORD)
    assert controller.authenticate_user('admin', PASSWORD)


def test_token_failure_rolls_back_account_closure(account):
    controller, user, _ = account
    controller.service.password_reset_model.create_token(user['ID_Usuario'])
    controller.service.user_model.execute_query("""CREATE TRIGGER fail_token
        BEFORE UPDATE ON recuperacao_senha BEGIN SELECT RAISE(ABORT, 'falha injetada'); END""")
    assert not controller.delete_own_account(PASSWORD)
    assert controller.get_user_by_id(user['ID_Usuario'])['Ativo'] == 1
    assert controller.authenticate_user('cliente', PASSWORD)


def test_backup_restore_preserves_closed_access_and_history(account, tmp_path):
    from models.backup_model import BackupModel
    controller, user, path = account
    assert controller.delete_own_account(PASSWORD)
    backup = BackupModel(path)
    before = backup.db.fetch_all('SELECT * FROM transacoes')
    archive = backup.criar_backup(str(tmp_path), PASSWORD)
    assert backup.restaurar_backup(archive, PASSWORD)
    assert backup.db.fetch_all('SELECT * FROM transacoes') == before
    assert controller.get_user_by_id(user['ID_Usuario'])['Ativo'] == 0
    assert controller.authenticate_user('cliente', PASSWORD) is None
    backup.db.close()


@pytest.mark.parametrize('legacy', [True, False])
def test_additive_migration_preserves_existing_database(account, legacy):
    controller, user, path = account
    model = controller.service.user_model
    before = model.fetch_all('SELECT * FROM transacoes')
    model.execute_query('DELETE FROM schema_migrations WHERE Versao = 4')
    if legacy:
        model.execute_query('ALTER TABLE usuarios DROP COLUMN Ativo')
    else:
        model.execute_query('UPDATE usuarios SET Ativo = 0 WHERE ID_Usuario = ?', (user['ID_Usuario'],))
    model.close()
    controller.service.password_reset_model.close()
    Database._initialized_paths.discard(os.path.abspath(path))
    reopened = Database(path)
    assert reopened.fetch_all('SELECT * FROM transacoes') == before
    assert reopened.fetch_one('SELECT Ativo FROM usuarios WHERE ID_Usuario = ?', (user['ID_Usuario'],))['Ativo'] == int(legacy)
    assert reopened.fetch_one('PRAGMA integrity_check')['integrity_check'] == 'ok'
    assert reopened.fetch_all('PRAGMA foreign_key_check') == []
    reopened.close()
