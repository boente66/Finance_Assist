from datetime import date

from database.database import Database
from services.divida_service import DividaService
from services.payment_service import PaymentService
from conftest import criar_conta, criar_usuario


def dados_divida(tipo="FIXO"):
    return {
        "Descricao": "Empréstimo teste",
        "Tipo_Divida": "Empréstimo bancário",
        "Tipo_Parcelamento": tipo,
        "Valor_Emprestado": 900,
        "Valor_Total_Contrato": 1000,
        "Quantidade_Parcelas": 3,
        "Data_Contratacao": "2026-09-01",
        "Primeiro_Vencimento": "2026-10-10",
    }


def test_migration_dividas_preserva_schema_existente(db):
    tables = {row["name"] for row in db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"dividas", "divida_parcelas", "pagamentos_divida"} <= tables
    columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(agendamentos)")}
    assert {"ID_Divida", "ID_Parcela_Divida"} <= columns


def test_divida_fixa_gera_parcelas_e_agendamentos_sem_pagamento(db, db_path):
    usuario = criar_usuario(db, "divida_fixa")
    service = DividaService(db_path)
    debt_id = service.criar(dados_divida(), usuario)
    parcelas = db.fetch_all(
        "SELECT * FROM divida_parcelas WHERE ID_Divida=? ORDER BY Numero_Parcela",
        (debt_id,),
    )
    schedules = db.fetch_all(
        "SELECT * FROM agendamentos WHERE ID_Divida=? ORDER BY Data", (debt_id,)
    )
    assert [row["Valor_Previsto"] for row in parcelas] == [333.33, 333.33, 333.34]
    assert len(schedules) == 3
    assert all(row["Status"] == "AGENDADO" for row in schedules)
    assert db.fetch_one("SELECT COUNT(*) AS n FROM pagamentos_divida")["n"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS n FROM transacoes")["n"] == 0


def test_executar_agendamento_registra_todo_fluxo_uma_vez(db, db_path):
    usuario = criar_usuario(db, "divida_pagamento")
    conta = criar_conta(db, usuario, "Conta", 1000)
    debt_id = DividaService(db_path).criar(dados_divida(), usuario)
    schedule = db.fetch_one(
        "SELECT * FROM agendamentos WHERE ID_Divida=? ORDER BY Data LIMIT 1",
        (debt_id,),
    )
    result = PaymentService(db_path).baixar_agendamento({
        "ID_Agendamento": schedule["ID_Agendamento"],
        "ID_Conta": conta,
        "Valor_Previsto": schedule["Valor"],
        "Desconto": 0,
        "Multa": 0,
        "Juros": 0,
        "Data": date.today().isoformat(),
    }, usuario)
    assert result["sucesso"] is True
    assert db.fetch_one("SELECT COUNT(*) AS n FROM transacoes")["n"] == 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM pagamentos_divida")["n"] == 1
    assert db.fetch_one(
        "SELECT Status FROM divida_parcelas WHERE ID_Parcela=?",
        (schedule["ID_Parcela_Divida"],),
    )["Status"] == "PAGA"
    assert db.fetch_one(
        "SELECT Status FROM agendamentos WHERE ID_Agendamento=?",
        (schedule["ID_Agendamento"],),
    )["Status"] == "EXECUTADO"
    assert round(db.fetch_one(
        "SELECT Saldo_Devedor FROM dividas WHERE ID_Divida=?", (debt_id,)
    )["Saldo_Devedor"], 2) == 666.67
    repeated = PaymentService(db_path).baixar_agendamento({
        "ID_Agendamento": schedule["ID_Agendamento"], "ID_Conta": conta,
        "Valor_Previsto": schedule["Valor"], "Data": date.today().isoformat(),
    }, usuario)
    assert repeated["sucesso"] is False
    assert db.fetch_one("SELECT COUNT(*) AS n FROM pagamentos_divida")["n"] == 1


def test_divida_livre_nao_gera_parcelas_e_aceita_amortizacao(db, db_path):
    usuario = criar_usuario(db, "divida_livre")
    conta = criar_conta(db, usuario, "Conta", 1000)
    service = DividaService(db_path)
    debt_id = service.criar(dados_divida("LIVRE"), usuario)
    assert db.fetch_one("SELECT COUNT(*) AS n FROM divida_parcelas")["n"] == 0
    service.registrar_pagamento({
        "ID_Divida": debt_id, "ID_Conta": conta, "Valor_Pago": 210,
        "Valor_Juros": 10, "Valor_Multa": 0, "Valor_Desconto": 0,
        "Data_Pagamento": "2026-09-27",
    }, usuario)
    debt = db.fetch_one("SELECT * FROM dividas WHERE ID_Divida=?", (debt_id,))
    payment = db.fetch_one("SELECT * FROM pagamentos_divida WHERE ID_Divida=?", (debt_id,))
    assert payment["Valor_Amortizado"] == 200
    assert debt["Saldo_Devedor"] == 800


def test_pagamentos_manuais_identicos_sao_operacoes_distintas(db, db_path):
    usuario = criar_usuario(db, "divida_manual_repetida")
    conta = criar_conta(db, usuario, "Conta", 1000)
    service = DividaService(db_path)
    debt_id = service.criar(dados_divida("LIVRE"), usuario)
    pagamento = {
        "ID_Divida": debt_id,
        "ID_Conta": conta,
        "Valor_Pago": 100,
        "Data_Pagamento": "2026-09-27",
    }

    primeiro = service.registrar_pagamento(pagamento, usuario)
    segundo = service.registrar_pagamento(pagamento, usuario)

    assert primeiro != segundo
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM pagamentos_divida WHERE ID_Divida=?",
        (debt_id,),
    )["n"] == 2
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM transacoes WHERE ID_Conta=?", (conta,)
    )["n"] == 2
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (conta,)
    )["Saldo_Atual"] == 800
    assert db.fetch_one(
        "SELECT Saldo_Devedor FROM dividas WHERE ID_Divida=?", (debt_id,)
    )["Saldo_Devedor"] == 800


def test_divida_livre_permite_agendamento_sem_reduzir_saldo(db, db_path):
    usuario = criar_usuario(db, "divida_livre_agendada")
    service = DividaService(db_path)
    debt_id = service.criar(dados_divida("LIVRE"), usuario)
    schedule_id = service.agendar_pagamento_livre({
        "ID_Divida": debt_id, "Valor": 150, "Data": "2026-11-15",
    }, usuario)
    schedule = db.fetch_one(
        "SELECT * FROM agendamentos WHERE ID_Agendamento=?", (schedule_id,)
    )
    debt = db.fetch_one("SELECT * FROM dividas WHERE ID_Divida=?", (debt_id,))
    assert schedule["ID_Divida"] == debt_id
    assert schedule["ID_Parcela_Divida"] is None
    assert schedule["Status"] == "AGENDADO"
    assert debt["Saldo_Devedor"] == 1000
    assert db.fetch_one("SELECT COUNT(*) AS n FROM pagamentos_divida")["n"] == 0


def test_encerrar_divida_cancela_parcelas_e_previsoes_pendentes(db, db_path):
    usuario = criar_usuario(db, "divida_encerrada")
    service = DividaService(db_path)
    debt_id = service.criar(dados_divida(), usuario)
    assert service.encerrar(debt_id, "RENEGOCIADA", usuario)
    assert db.fetch_one(
        "SELECT Status FROM dividas WHERE ID_Divida=?", (debt_id,)
    )["Status"] == "RENEGOCIADA"
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM divida_parcelas WHERE ID_Divida=? AND Status='CANCELADA'",
        (debt_id,),
    )["n"] == 3
    assert db.fetch_one(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE ID_Divida=? AND Status='CANCELADO'",
        (debt_id,),
    )["n"] == 3
