from datetime import date

from services.fatura_service import FaturaService
import pytest

from conftest import criar_cartao, criar_conta, criar_usuario, saldo


def compra(service, usuario, cartao, data, valor, descricao):
    return service.registrar_despesa_cartao({
        "ID_Usuario": usuario,
        "ID_Cartao": cartao,
        "Data": data,
        "Descricao": descricao,
        "Valor": valor,
        "Num_Parcelas": 1,
    })


def movimentos(db, cartao, mes):
    return db.fetch_all("""
        SELECT Descricao, Valor, Tipo_Movimento, Paga,
               Competencia_Mes, ID_Lancamento_Origem
        FROM lancamentos
        WHERE ID_Cartao = ? AND Competencia_Mes = ?
        ORDER BY ID_Lancamento
    """, (cartao, mes))


def test_ciclo_creditos_pagamento_e_limite_real(db, db_path, monkeypatch):
    class ScenarioDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 19)

    monkeypatch.setattr("services.fatura_service.date", ScenarioDate)
    usuario = criar_usuario(db, "ciclo_real")
    conta = criar_conta(db, usuario, "Conta pagamento", 3000)
    cartao = criar_cartao(db, usuario)
    db.execute_query(
        "UPDATE credito SET Limite = 2000, Dia_Fechamento = 20 "
        "WHERE ID_Cartao = ?",
        (cartao,),
    )
    service = FaturaService(db_path)

    compra(service, usuario, cartao, "2026-08-10", 800, "Compras agosto")
    compra_original = movimentos(db, cartao, 8)[0]
    service.adicionar_credito_fatura({
        "ID_Usuario": usuario,
        "ID_Cartao": cartao,
        "Data": "2026-08-15",
        "Descricao": "Cashback",
        "Tipo_Credito": "Cashback",
        "Valor": 50,
        "ID_Lancamento_Origem": db.fetch_one(
            "SELECT ID_Lancamento FROM lancamentos "
            "WHERE ID_Cartao = ? AND Descricao = 'Compras agosto'",
            (cartao,),
        )["ID_Lancamento"],
    })
    compra(service, usuario, cartao, "2026-08-25", 300, "Compras setembro")

    agosto = service.get_painel_cartao(
        cartao, 8, 2026, usuario
    )["fatura"]
    setembro = service.get_painel_cartao(
        cartao, 9, 2026, usuario
    )["fatura"]
    assert agosto["total_fatura"] == 750.0
    assert agosto["compras"] == 800.0
    assert agosto["creditos"] == -50.0
    assert agosto["estornos"] == 0
    assert agosto["ajustes"] == 0
    assert agosto["pagamentos"] == 0
    assert agosto["saldo_a_pagar"] == 750.0
    assert agosto["status"] == "FECHADA"
    assert agosto["data_fechamento"] == "2026-08-20"
    assert setembro["status"] == "ABERTA"
    assert setembro["compras"] == 300
    assert service.calcular_limite_disponivel(cartao, usuario) == 950
    assert compra_original["Valor"] == 800

    resultado = service.pagar_fatura(
        cartao, 8, 2026, conta, usuario
    )
    assert resultado["codigo"] == "OK"
    agosto_pago = service.get_painel_cartao(
        cartao, 8, 2026, usuario
    )["fatura"]
    assert agosto_pago["status"] == "PAGA"
    assert agosto_pago["compras"] == 800
    assert agosto_pago["creditos"] == -50
    assert agosto_pago["pagamentos"] == 750
    assert agosto_pago["saldo_a_pagar"] == 0
    assert saldo(db, conta) == 2250
    assert service.calcular_limite_disponivel(cartao, usuario) == 1700
    transacao = db.fetch_one(
        "SELECT Valor, Tipo FROM transacoes WHERE ID_Conta = ?",
        (conta,),
    )
    assert transacao["Valor"] == -750
    assert transacao["Tipo"] == "Despesa"

    agosto_itens = movimentos(db, cartao, 8)
    assert [(item["Tipo_Movimento"], item["Valor"]) for item in agosto_itens] == [
        ("COMPRA", 800),
        ("CREDITO", -50),
    ]
    fatura_id = db.fetch_one(
        "SELECT ID_Fatura FROM faturas_cartao "
        "WHERE ID_Cartao = ? AND Competencia_Mes = 8",
        (cartao,),
    )["ID_Fatura"]
    assert db.fetch_one(
        "SELECT COUNT(*) AS total FROM lancamentos "
        "WHERE ID_Cartao = ? AND ID_Fatura = ?",
        (cartao, fatura_id),
    )["total"] == 2
    assert db.fetch_one(
        "SELECT ID_Fatura FROM pagamentos_fatura WHERE ID_Cartao = ?",
        (cartao,),
    )["ID_Fatura"] == fatura_id


def test_estorno_depois_do_fechamento_entra_na_competencia_seguinte(
    db, db_path
):
    usuario = criar_usuario(db, "estorno_tardio")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    compra(service, usuario, cartao, "2026-08-05", 100, "Compra original")
    original = movimentos(db, cartao, 8)[0]
    original_id = db.fetch_one(
        "SELECT ID_Lancamento FROM lancamentos WHERE ID_Cartao = ?",
        (cartao,),
    )["ID_Lancamento"]

    service.adicionar_credito_fatura({
        "ID_Usuario": usuario,
        "ID_Cartao": cartao,
        "Data": "2026-08-25",
        "Descricao": "Estorno da compra",
        "Tipo_Credito": "Estorno",
        "Valor": 100,
        "ID_Lancamento_Origem": original_id,
    })

    assert original["Valor"] == 100
    setembro = movimentos(db, cartao, 9)
    assert setembro[0]["Tipo_Movimento"] == "ESTORNO"
    assert setembro[0]["Valor"] == -100
    assert setembro[0]["ID_Lancamento_Origem"] == original_id


def test_importacao_preserva_sinal_do_credito(db, db_path):
    usuario = criar_usuario(db, "importa_credito")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    quantidade = service.salvar_lote_importado([{
        "ID_Usuario": usuario,
        "ID_Cartao": cartao,
        "Data": "2026-08-08",
        "Descricao": "Cashback importado",
        "Valor": -25,
        "Competencia_Mes": 8,
        "Competencia_Ano": 2026,
        "Tipo_Movimento": "CREDITO",
    }], usuario)

    assert quantidade == 1
    item = movimentos(db, cartao, 8)[0]
    assert item["Valor"] == -25
    assert item["Tipo_Movimento"] == "CREDITO"


def test_migracao_preserva_compra_sem_materializar_pagamento_historico(db):
    usuario = criar_usuario(db, "migracao_fatura")
    conta = criar_conta(db, usuario, "Conta", 1000)
    cartao = criar_cartao(db, usuario)
    compra_id = db.execute_insert("""
        INSERT INTO lancamentos (
            ID_Cartao, Data, Competencia_Mes, Competencia_Ano,
            Descricao, Valor, Paga, ID_Usuario
        ) VALUES (?, '2026-08-01', 8, 2026, 'Compra preservada', 120, 1, ?)
    """, (cartao, usuario))
    transacao = db.execute_insert("""
        INSERT INTO transacoes (
            ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario
        ) VALUES (?, 'Despesa', 'Pagamento antigo', -120, '2026-08-20', ?)
    """, (conta, usuario))
    db.execute_query("""
        INSERT INTO pagamentos_fatura (
            Chave_Idempotencia, ID_Cartao, Competencia_Mes,
            Competencia_Ano, ID_Conta, ID_Transacao, ID_Usuario, Valor
        ) VALUES ('historico-unico', ?, 8, 2026, ?, ?, ?, 120)
    """, (cartao, conta, transacao, usuario))

    db._migration_006_invoice_cycles()

    itens = movimentos(db, cartao, 8)
    assert db.fetch_one(
        "SELECT ID_Lancamento FROM lancamentos WHERE ID_Lancamento = ?",
        (compra_id,),
    )
    tipos_valores = [
        (item["Tipo_Movimento"], item["Valor"]) for item in itens
    ]
    assert tipos_valores
    assert ("COMPRA", 120) in tipos_valores
    assert ("PAGAMENTO", -120) not in tipos_valores


def test_persistencia_rejeita_sinal_incorreto_em_credito(db, db_path):
    usuario = criar_usuario(db, "sinal_credito")
    cartao = criar_cartao(db, usuario)
    service = FaturaService(db_path)
    with pytest.raises(ValueError, match="valor negativo"):
        service.lancamento_model.add_lancamento({
            "ID_Usuario": usuario,
            "ID_Cartao": cartao,
            "Data": "2026-08-01",
            "Competencia_Mes": 8,
            "Competencia_Ano": 2026,
            "Descricao": "Crédito inválido",
            "Valor": 20,
            "Tipo_Movimento": "CREDITO",
        })
