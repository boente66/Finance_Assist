from services.transaction_service import TransactionService

from conftest import criar_conta, criar_usuario, saldo, total


def preparar(db):
    user_id = criar_usuario(db, "usuario")
    origem = criar_conta(db, user_id, "Origem", 100)
    destino = criar_conta(db, user_id, "Destino", 10)
    return user_id, origem, destino


def test_transferencia_normal_um_commit(db, db_path):
    user_id, origem, destino = preparar(db)
    service = TransactionService(db_path)
    eventos = []
    service.transaction_model.connection.set_trace_callback(eventos.append)

    resultado = service.transferir(
        origem,
        destino,
        25,
        "2026-07-26",
        user_id
    )

    assert resultado["codigo"] == "OK"
    assert saldo(db, origem) == 75
    assert saldo(db, destino) == 35
    assert total(db, "transacoes") == 2
    assert sum(e.strip().upper() == "COMMIT" for e in eventos) == 1


def test_falha_apos_debito_reverte_tudo(db, db_path, monkeypatch):
    user_id, origem, destino = preparar(db)
    service = TransactionService(db_path)
    original = service._criar_transacao_base
    chamadas = {"total": 0}

    def falhar_no_credito(dados, validar_saldo):
        chamadas["total"] += 1
        if chamadas["total"] == 2:
            raise RuntimeError("falha simulada antes do crédito")
        return original(dados, validar_saldo)

    monkeypatch.setattr(service, "_criar_transacao_base", falhar_no_credito)
    resultado = service.transferir(
        origem, destino, 25, "2026-07-26", user_id
    )

    assert resultado["sucesso"] is False
    assert saldo(db, origem) == 100
    assert saldo(db, destino) == 10
    assert total(db, "transacoes") == 0


def test_falha_apos_credito_antes_commit_reverte_tudo(
    db,
    db_path,
    monkeypatch
):
    user_id, origem, destino = preparar(db)
    service = TransactionService(db_path)
    original = service._registrar_transferencia

    def falhar_antes_commit(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("falha simulada antes do commit")

    monkeypatch.setattr(service, "_registrar_transferencia", falhar_antes_commit)
    resultado = service.transferir(
        origem, destino, 25, "2026-07-26", user_id
    )

    assert resultado["sucesso"] is False
    assert saldo(db, origem) == 100
    assert saldo(db, destino) == 10
    assert total(db, "transacoes") == 0


def test_transferencia_recusa_mesma_conta(db, db_path):
    user_id, origem, _ = preparar(db)
    resultado = TransactionService(db_path).transferir(
        origem, origem, 10, "2026-07-26", user_id
    )
    assert resultado["codigo"] == "DADOS_INVALIDOS"
    assert saldo(db, origem) == 100
    assert total(db, "transacoes") == 0


def test_transferencia_recusa_conta_de_outro_usuario(db, db_path):
    user_id, origem, _ = preparar(db)
    outro = criar_usuario(db, "outro")
    destino_outro = criar_conta(db, outro, "Outra", 0)

    resultado = TransactionService(db_path).transferir(
        origem, destino_outro, 10, "2026-07-26", user_id
    )
    assert resultado["codigo"] == "NAO_AUTORIZADO"
    assert saldo(db, origem) == 100
    assert saldo(db, destino_outro) == 0
    assert total(db, "transacoes") == 0


def test_transferencia_recusa_zero_e_negativo(db, db_path):
    user_id, origem, destino = preparar(db)
    service = TransactionService(db_path)

    for valor in (0, -10):
        resultado = service.transferir(
            origem, destino, valor, "2026-07-26", user_id
        )
        assert resultado["codigo"] == "DADOS_INVALIDOS"

    assert saldo(db, origem) == 100
    assert saldo(db, destino) == 10
    assert total(db, "transacoes") == 0
