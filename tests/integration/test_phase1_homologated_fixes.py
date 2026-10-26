from datetime import date

import pytest

from services.account_service import AccountService
from services.divida_service import DividaService
from services.favorecido_service import FavorecidoService
from services.transaction_service import (
    InsufficientFundsError,
    TransactionService,
)
from conftest import criar_conta, criar_usuario


def _transaction(db, user_id, account_id, value=20, kind="Receita"):
    transaction_id = db.execute_insert("""
        INSERT INTO transacoes
            (ID_Conta, Tipo, Descricao, Valor, Data, ID_Usuario)
        VALUES (?, ?, 'Original', ?, ?, ?)
    """, (account_id, kind, value, date.today().isoformat(), user_id))
    db.execute_query(
        "UPDATE contas SET Saldo_Atual=Saldo_Atual+? WHERE ID_Conta=?",
        (value, account_id),
    )
    return transaction_id


@pytest.mark.parametrize("target_account,kind,value,expected_a,expected_b", [
    ("same", "Receita", 35, 135, 50),
    ("same", "Despesa", 35, 65, 50),
    ("other", "Receita", 35, 100, 85),
    ("other", "Despesa", 35, 100, 15),
])
def test_transaction_edit_persists_account_type_and_balance(
    db, db_path, target_account, kind, value, expected_a, expected_b
):
    user_id = criar_usuario(db, f"edit_{target_account}_{kind}")
    account_a = criar_conta(db, user_id, "A", 100)
    account_b = criar_conta(db, user_id, "B", 50)
    transaction_id = _transaction(db, user_id, account_a)
    target = account_a if target_account == "same" else account_b

    TransactionService(db_path).atualizar_transacao({
        "ID_Transacao": transaction_id,
        "ID_Usuario": user_id,
        "ID_Conta": target,
        "Tipo": kind,
        "Valor": value,
        "Descricao": "Editada",
        "Data": date.today().isoformat(),
    })

    saved = db.fetch_one(
        "SELECT * FROM transacoes WHERE ID_Transacao=?", (transaction_id,)
    )
    assert saved["ID_Conta"] == target
    assert saved["Tipo"] == kind
    assert saved["Valor"] == (-value if kind == "Despesa" else value)
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account_a,)
    )["Saldo_Atual"] == expected_a
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account_b,)
    )["Saldo_Atual"] == expected_b


def test_transaction_edit_insufficient_funds_has_no_effect(db, db_path):
    user_id = criar_usuario(db, "edit_insufficient")
    account = criar_conta(db, user_id, "A", 100)
    transaction_id = _transaction(db, user_id, account)
    service = TransactionService(db_path)
    with pytest.raises(InsufficientFundsError):
        service.atualizar_transacao({
            "ID_Transacao": transaction_id, "ID_Usuario": user_id,
            "ID_Conta": account, "Tipo": "Despesa", "Valor": 101,
            "Descricao": "Recusada", "Data": date.today().isoformat(),
        })
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account,)
    )["Saldo_Atual"] == 120
    assert db.fetch_one(
        "SELECT Valor FROM transacoes WHERE ID_Transacao=?", (transaction_id,)
    )["Valor"] == 20


def test_transaction_edit_failure_rolls_back_balances(db, db_path, monkeypatch):
    user_id = criar_usuario(db, "edit_rollback")
    account_a = criar_conta(db, user_id, "A", 100)
    account_b = criar_conta(db, user_id, "B", 50)
    transaction_id = _transaction(db, user_id, account_a)
    service = TransactionService(db_path)
    monkeypatch.setattr(
        service.transaction_model, "update_transaction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("falha")),
    )
    with pytest.raises(RuntimeError, match="falha"):
        service.atualizar_transacao({
            "ID_Transacao": transaction_id, "ID_Usuario": user_id,
            "ID_Conta": account_b, "Tipo": "Despesa", "Valor": 30,
            "Descricao": "Falha", "Data": date.today().isoformat(),
        })
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account_a,)
    )["Saldo_Atual"] == 120
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account_b,)
    )["Saldo_Atual"] == 50


@pytest.mark.parametrize("new_balance,expected_delta", [
    (250, 150), (25, -75), (0, -100), (100, None),
])
def test_balance_adjustment_creates_auditable_transaction(
    db, db_path, new_balance, expected_delta
):
    user_id = criar_usuario(db, f"adjust_{new_balance}")
    account = criar_conta(db, user_id, "Conta", 100)
    assert AccountService(db_path).ajustar_saldo(account, new_balance, user_id)
    rows = db.fetch_all(
        "SELECT * FROM transacoes WHERE ID_Conta=?", (account,)
    )
    if expected_delta is None:
        assert rows == []
    else:
        assert len(rows) == 1
        assert rows[0]["Descricao"] == "Ajuste de saldo"
        assert rows[0]["Valor"] == expected_delta
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account,)
    )["Saldo_Atual"] == new_balance


@pytest.mark.parametrize("failure_point", ["transaction", "balance"])
def test_balance_adjustment_failure_rolls_back(
    db, db_path, monkeypatch, failure_point
):
    user_id = criar_usuario(db, f"adjust_rollback_{failure_point}")
    account = criar_conta(db, user_id, "Conta", 100)
    service = AccountService(db_path)
    target = (
        service.transaction_model if failure_point == "transaction"
        else service.model
    )
    method = "add_transaction" if failure_point == "transaction" else "update_saldo"
    monkeypatch.setattr(
        target, method,
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("falha")),
    )
    with pytest.raises(RuntimeError, match="falha"):
        service.ajustar_saldo(account, 250, user_id)
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account,)
    )["Saldo_Atual"] == 100
    assert db.fetch_one("SELECT COUNT(*) AS n FROM transacoes")["n"] == 0


def test_free_debt_overpayment_is_rejected_before_writes(db, db_path):
    user_id = criar_usuario(db, "debt_overpayment")
    account = criar_conta(db, user_id, "Conta", 500)
    service = DividaService(db_path)
    debt_id = service.criar({
        "Descricao": "Livre", "Tipo_Divida": "Empréstimo bancário",
        "Tipo_Parcelamento": "LIVRE", "Valor_Emprestado": 100,
        "Valor_Total_Contrato": 100, "Data_Contratacao": "2026-10-18",
    }, user_id)
    with pytest.raises(ValueError, match="excede"):
        service.registrar_pagamento({
            "ID_Divida": debt_id, "ID_Conta": account,
            "Valor_Pago": 100.01, "Data_Pagamento": "2026-10-18",
        }, user_id)
    assert db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta=?", (account,)
    )["Saldo_Atual"] == 500
    assert db.fetch_one(
        "SELECT Saldo_Devedor FROM dividas WHERE ID_Divida=?", (debt_id,)
    )["Saldo_Devedor"] == 100
    assert db.fetch_one("SELECT COUNT(*) AS n FROM pagamentos_divida")["n"] == 0


@pytest.mark.parametrize("field,valid,invalid", [
    ("CPF", "52998224725", "12345678910"),
    ("CNPJ", "11222333000181", "12345678000190"),
])
def test_document_checksum_and_legacy_preservation(
    db, db_path, field, valid, invalid, monkeypatch
):
    user_id = criar_usuario(db, f"doc_{field.lower()}")
    monkeypatch.setattr("database.database.get_db_path", lambda: db_path)
    service = FavorecidoService()
    created = service.criar({"Nome": "Válido", field: valid}, user_id)
    assert created
    with pytest.raises(ValueError, match="inválido"):
        service.criar({"Nome": "Inválido", field: invalid}, user_id)
    with pytest.raises(ValueError, match="inválido"):
        service.resolver_favorecido({"Nome": "Rápido", field: invalid}, user_id)

    # Simula registro legado sem passar pela validação nova.
    legacy = db.execute_insert(
        "INSERT INTO favorecido (Nome,Tipo,ID_Usuario) VALUES (?,?,?)",
        ("Legado", "PF" if field == "CPF" else "PJ", user_id),
    )
    table = "pessoa_fisica" if field == "CPF" else "pessoa_juridica"
    db.execute_query(
        f"INSERT INTO {table} (ID_Favorecido,{field}) VALUES (?,?)",
        (legacy, invalid),
    )
    service.atualizar(legacy, {"Nome": "Legado preservado"}, user_id)
    assert service.obter(legacy, user_id)[field] == invalid
    with pytest.raises(ValueError, match="inválido"):
        service.atualizar(legacy, {field: invalid[::-1]}, user_id)

