from services.fatura_service import FaturaService

from conftest import (
    criar_cartao,
    criar_conta,
    criar_lancamento,
    criar_usuario,
    saldo,
    total,
)


MES = 7
ANO = 2026


def preparar(db, saldo_conta=500, valores=(100,)):
    user_id = criar_usuario(db, "usuario")
    conta = criar_conta(db, user_id, "Conta", saldo_conta)
    cartao = criar_cartao(db, user_id)
    lancamentos = [
        criar_lancamento(
            db,
            user_id,
            cartao,
            valor=valor,
            mes=MES,
            ano=ANO,
            descricao=f"Compra {indice}"
        )
        for indice, valor in enumerate(valores, start=1)
    ]
    return user_id, conta, cartao, lancamentos


def lancamentos_fatura(db, cartao):
    return db.fetch_all(
        """
        SELECT * FROM lancamentos
        WHERE ID_Cartao = ?
          AND Competencia_Mes = ?
          AND Competencia_Ano = ?
        ORDER BY ID_Lancamento
        """,
        (cartao, MES, ANO)
    )


def pagar(service, user_id, conta, cartao):
    return service.pagar_fatura(
        cartao,
        MES,
        ANO,
        conta,
        user_id
    )


def test_pagamento_total_normal(db, db_path):
    user_id, conta, cartao, _ = preparar(db, valores=(100, 50))
    resultado = pagar(FaturaService(db_path), user_id, conta, cartao)

    assert resultado["codigo"] == "OK"
    assert saldo(db, conta) == 350
    assert all(item["Paga"] == 1 for item in lancamentos_fatura(db, cartao))
    assert total(db, "transacoes") == 1
    assert total(db, "pagamentos_fatura") == 1


def test_falha_apos_debito_reverte_tudo(db, db_path, monkeypatch):
    user_id, conta, cartao, _ = preparar(db)
    service = FaturaService(db_path)

    def falhar(*_args, **_kwargs):
        raise RuntimeError("falha simulada antes da baixa")

    monkeypatch.setattr(service.lancamento_model, "marcar_como_pago", falhar)
    resultado = pagar(service, user_id, conta, cartao)

    assert resultado["sucesso"] is False
    assert saldo(db, conta) == 500
    assert lancamentos_fatura(db, cartao)[0]["Paga"] == 0
    assert total(db, "transacoes") == 0
    assert total(db, "pagamentos_fatura") == 0


def test_falha_durante_atualizacao_reverte_tudo(
    db,
    db_path,
    monkeypatch
):
    user_id, conta, cartao, _ = preparar(db, valores=(60, 40))
    service = FaturaService(db_path)
    original = service.lancamento_model.marcar_como_pago
    chamadas = {"total": 0}

    def falhar_na_segunda(*args, **kwargs):
        chamadas["total"] += 1
        if chamadas["total"] == 2:
            raise RuntimeError("falha simulada na segunda baixa")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        service.lancamento_model,
        "marcar_como_pago",
        falhar_na_segunda
    )
    resultado = pagar(service, user_id, conta, cartao)

    assert resultado["sucesso"] is False
    assert saldo(db, conta) == 500
    assert all(item["Paga"] == 0 for item in lancamentos_fatura(db, cartao))
    assert total(db, "transacoes") == 0
    assert total(db, "pagamentos_fatura") == 0


def test_reenvio_do_mesmo_pagamento_nao_debita(db, db_path):
    user_id, conta, cartao, _ = preparar(db)
    service = FaturaService(db_path)

    primeiro = pagar(service, user_id, conta, cartao)
    segundo = pagar(service, user_id, conta, cartao)

    assert primeiro["codigo"] == "OK"
    assert segundo["codigo"] == "JA_PROCESSADO"
    assert saldo(db, conta) == 400
    assert total(db, "transacoes") == 1
    assert total(db, "pagamentos_fatura") == 1


def test_conta_de_outro_usuario_e_recusada(db, db_path):
    user_id, _, cartao, _ = preparar(db)
    outro = criar_usuario(db, "outro")
    conta_outro = criar_conta(db, outro, "Outra", 500)

    resultado = pagar(
        FaturaService(db_path),
        user_id,
        conta_outro,
        cartao
    )

    assert resultado["codigo"] == "NAO_AUTORIZADO"
    assert saldo(db, conta_outro) == 500
    assert total(db, "transacoes") == 0


def test_fatura_ja_paga_nao_gera_debito(db, db_path):
    user_id, conta, cartao, _ = preparar(db)
    db.execute_query(
        "UPDATE lancamentos SET Paga = 1 WHERE ID_Cartao = ?",
        (cartao,)
    )

    resultado = pagar(FaturaService(db_path), user_id, conta, cartao)
    assert resultado["codigo"] == "DADOS_INVALIDOS"
    assert saldo(db, conta) == 500
    assert total(db, "transacoes") == 0


def test_valor_zero_ou_negativo_e_recusado(db, db_path):
    user_id, conta, cartao, _ = preparar(db, valores=(0, -10))
    resultado = pagar(FaturaService(db_path), user_id, conta, cartao)

    assert resultado["codigo"] == "DADOS_INVALIDOS"
    assert saldo(db, conta) == 500
    assert total(db, "transacoes") == 0


def test_saldo_insuficiente(db, db_path):
    user_id, conta, cartao, _ = preparar(db, saldo_conta=50, valores=(100,))
    resultado = pagar(FaturaService(db_path), user_id, conta, cartao)

    assert resultado["codigo"] == "SALDO_INSUFICIENTE"
    assert saldo(db, conta) == 50
    assert lancamentos_fatura(db, cartao)[0]["Paga"] == 0
    assert total(db, "transacoes") == 0
