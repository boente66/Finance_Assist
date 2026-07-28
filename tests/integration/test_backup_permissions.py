import json
from pathlib import Path

import pytest

from core.session import Session
from controllers.backup_controller import BackupController
from services.backup_service import BackupService
from services.payment_service import PaymentService
from utilitarios.crypto_util import decrypt_bytes, encrypt_bytes

from conftest import (
    criar_agendamento,
    criar_conta,
    criar_usuario,
    dados_baixa,
    total,
)


def usuario_dict(db, id_usuario):
    return db.fetch_one(
        "SELECT * FROM usuarios WHERE ID_Usuario = ?",
        (id_usuario,)
    )


def test_administrador_cria_backup_sem_tokens(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    db.execute_query(
        """
        INSERT INTO recuperacao_senha (
            ID_Usuario, Token, Expira_Em
        ) VALUES (?, 'token-secreto', datetime('now', '+30 minutes'))
        """,
        (admin_id,)
    )

    resultado = BackupService(db_path).criar_backup(
        str(tmp_path),
        "senha-forte",
        admin
    )

    assert resultado["sucesso"] is True
    arquivo = resultado["dados"]["arquivo"]

    estrutura = json.loads(open(arquivo, encoding="utf-8").read())
    payload = json.loads(
        decrypt_bytes(estrutura["payload"], "senha-forte").decode()
    )
    assert "recuperacao_senha" not in payload
    assert "pagamentos_fatura" in payload


def test_administrador_inicia_restauracao(db, db_path, tmp_path):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    service = BackupService(db_path)
    criado = service.criar_backup(str(tmp_path), "senha-forte", admin)
    arquivo = criado["dados"]["arquivo"]

    db.execute_query(
        "UPDATE usuarios SET Nome = 'Alterado' WHERE ID_Usuario = ?",
        (admin_id,)
    )

    restaurado = service.restaurar_backup(
        arquivo,
        "senha-forte",
        admin
    )

    assert restaurado["sucesso"] is True
    assert usuario_dict(db, admin_id)["Nome"] == "Admin"


def test_usuario_comum_nao_cria_backup_nem_altera_banco(
    db,
    db_path,
    tmp_path
):
    user_id = criar_usuario(db, "comum")
    comum = usuario_dict(db, user_id)
    antes = db.fetch_all("SELECT * FROM usuarios")

    resultado = BackupService(db_path).criar_backup(
        str(tmp_path),
        "senha-forte",
        comum
    )

    assert resultado["codigo"] == "NAO_AUTORIZADO"
    assert list(tmp_path.glob("*.kp")) == []
    assert db.fetch_all("SELECT * FROM usuarios") == antes


def test_usuario_comum_nao_restaura_por_controller(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    user_id = criar_usuario(db, "comum")
    admin = usuario_dict(db, admin_id)
    comum = usuario_dict(db, user_id)
    service = BackupService(db_path)
    arquivo = service.criar_backup(
        str(tmp_path),
        "senha-forte",
        admin
    )["dados"]["arquivo"]

    db.execute_query(
        "UPDATE usuarios SET Nome = 'Estado atual' WHERE ID_Usuario = ?",
        (user_id,)
    )
    antes = db.fetch_all("SELECT * FROM usuarios ORDER BY ID_Usuario")

    Session.set_usuario(comum)
    controller = BackupController(service)
    resultado = controller.restaurar_backup(arquivo, "senha-forte")

    assert resultado["codigo"] == "NAO_AUTORIZADO"
    assert db.fetch_all(
        "SELECT * FROM usuarios ORDER BY ID_Usuario"
    ) == antes


def test_menu_de_backup_so_existe_para_admin(monkeypatch):
    pytest.importorskip("PyQt5")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt5.QtWidgets import QApplication
    from views.main_view import MainView

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(MainView, "_abrir_primeira_view", lambda self: None)
    monkeypatch.setattr(MainView, "aplicar_tema", lambda self: None)

    comum = MainView({"ID_Usuario": 1, "Nome": "Comum", "Nivel_Acesso": "usuario"})
    admin = MainView({"ID_Usuario": 2, "Nome": "Admin", "Nivel_Acesso": "admin"})

    assert not hasattr(comum, "btn_backup")
    assert hasattr(admin, "btn_backup")

    comum.close()
    admin.close()


def test_restauracao_com_agendamento_executado_e_fk_valida(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    conta = criar_conta(db, admin_id, "Conta", 100)
    agendamento = criar_agendamento(db, admin_id, conta)
    baixado = PaymentService(db_path).baixar_agendamento(
        dados_baixa(agendamento, conta),
        admin_id
    )
    assert baixado["codigo"] == "OK"

    service = BackupService(db_path)
    criado = service.criar_backup(str(tmp_path), "senha-forte", admin)
    arquivo = criado["dados"]["arquivo"]
    db.execute_query(
        "UPDATE usuarios SET Nome = 'Alterado' WHERE ID_Usuario = ?",
        (admin_id,)
    )

    restaurado = service.restaurar_backup(arquivo, "senha-forte", admin)

    assert restaurado["codigo"] == "OK"
    assert usuario_dict(db, admin_id)["Nome"] == "Admin"
    assert db.fetch_all("PRAGMA foreign_key_check") == []
    transacao = db.fetch_one(
        "SELECT ID_Agendamento FROM transacoes WHERE ID_Agendamento = ?",
        (agendamento,)
    )
    assert transacao["ID_Agendamento"] == agendamento


def test_falha_no_meio_da_restauracao_faz_rollback_integral(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    conta = criar_conta(db, admin_id, "Conta", 100)
    agendamento = criar_agendamento(db, admin_id, conta)
    PaymentService(db_path).baixar_agendamento(
        dados_baixa(agendamento, conta),
        admin_id
    )
    service = BackupService(db_path)
    arquivo = service.criar_backup(
        str(tmp_path), "senha-forte", admin
    )["dados"]["arquivo"]

    estrutura = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    dados = json.loads(
        decrypt_bytes(estrutura["payload"], "senha-forte").decode("utf-8")
    )
    dados["transacoes"][0]["ID_Conta"] = 999999
    estrutura["payload"] = encrypt_bytes(
        json.dumps(dados, ensure_ascii=False).encode("utf-8"),
        "senha-forte"
    )
    invalido = tmp_path / "backup_invalido.kp"
    invalido.write_text(json.dumps(estrutura), encoding="utf-8")

    tabelas = service.model.RESTORE_ORDER
    antes = {
        tabela: db.fetch_all(f"SELECT * FROM {tabela} ORDER BY rowid")
        for tabela in tabelas
    }
    resultado = service.restaurar_backup(
        str(invalido), "senha-forte", admin
    )
    depois = {
        tabela: db.fetch_all(f"SELECT * FROM {tabela} ORDER BY rowid")
        for tabela in tabelas
    }

    assert resultado["codigo"] == "ERRO_INTERNO"
    assert antes == depois
    preventivo = (resultado["dados"] or {})["backup_preventivo"]
    assert Path(preventivo).is_file()
    assert db.fetch_all("PRAGMA foreign_key_check") == []


def test_dois_backups_no_mesmo_segundo_tem_nomes_diferentes(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    service = BackupService(db_path)

    primeiro = service.criar_backup(
        str(tmp_path), "senha-forte", admin
    )["dados"]["arquivo"]
    segundo = service.criar_backup(
        str(tmp_path), "senha-forte", admin
    )["dados"]["arquivo"]

    assert primeiro != segundo
    assert Path(primeiro).is_file()
    assert Path(segundo).is_file()


def test_backup_preventivo_nao_colide_com_arquivo_restaurado(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    service = BackupService(db_path)
    arquivo = service.criar_backup(
        str(tmp_path), "senha-forte", admin
    )["dados"]["arquivo"]

    resultado = service.restaurar_backup(arquivo, "senha-forte", admin)
    preventivo = resultado["dados"]["backup_preventivo"]

    assert resultado["codigo"] == "OK"
    assert Path(arquivo).resolve() != Path(preventivo).resolve()
    assert Path(arquivo).is_file()
    assert Path(preventivo).is_file()


def test_backup_logico_legado_sem_campos_p0_restaura(
    db,
    db_path,
    tmp_path
):
    admin_id = criar_usuario(db, "admin", "admin")
    admin = usuario_dict(db, admin_id)
    conta = criar_conta(db, admin_id, "Conta", 100)
    service = BackupService(db_path)
    arquivo = service.criar_backup(
        str(tmp_path), "senha-forte", admin
    )["dados"]["arquivo"]

    estrutura = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    dados = json.loads(
        decrypt_bytes(estrutura["payload"], "senha-forte").decode("utf-8")
    )
    dados.pop("pagamentos_fatura", None)
    for transacao in dados.get("transacoes", []):
        transacao.pop("ID_Agendamento", None)
    estrutura["payload"] = encrypt_bytes(
        json.dumps(dados, ensure_ascii=False).encode("utf-8"),
        "senha-forte"
    )
    legado = tmp_path / "backup_legado.kp"
    legado.write_text(json.dumps(estrutura), encoding="utf-8")

    db.execute_query(
        "UPDATE contas SET Saldo_Atual = 1 WHERE ID_Conta = ?",
        (conta,)
    )
    resultado = service.restaurar_backup(
        str(legado), "senha-forte", admin
    )

    assert resultado["codigo"] == "OK"
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta = ?",
        (conta,)
    )["Saldo_Atual"] == 100
    assert db.fetch_all("PRAGMA foreign_key_check") == []
