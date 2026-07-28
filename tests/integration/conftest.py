import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import Database


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "financeiro_test.db")


@pytest.fixture
def db(db_path):
    database = Database(db_path)
    yield database
    database.close()


def criar_usuario(db, login, nivel="usuario"):
    return db.execute_insert(
        """
        INSERT INTO usuarios (Nome, Email, Login, Senha, Nivel_Acesso)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            login.title(),
            f"{login}@example.com",
            login,
            "hash-teste",
            nivel,
        )
    )


def criar_conta(db, id_usuario, nome, saldo):
    return db.execute_insert(
        """
        INSERT INTO contas (Nome_Conta, Tipo, Saldo_Atual, ID_Usuario)
        VALUES (?, 'Corrente', ?, ?)
        """,
        (nome, saldo, id_usuario)
    )


def criar_cartao(db, id_usuario, nome="Cartão teste"):
    return db.execute_insert(
        """
        INSERT INTO credito (
            Nome, Limite, Dia_Fechamento, Dia_Vencimento, ID_Usuario
        )
        VALUES (?, 5000, 10, 20, ?)
        """,
        (nome, id_usuario)
    )


def criar_lancamento(
    db,
    id_usuario,
    id_cartao,
    valor=100,
    mes=7,
    ano=2026,
    descricao="Compra teste",
    paga=0
):
    return db.execute_insert(
        """
        INSERT INTO lancamentos (
            ID_Cartao, Data, Competencia_Mes, Competencia_Ano,
            Descricao, Valor, Paga, ID_Usuario
        )
        VALUES (?, '2026-07-01', ?, ?, ?, ?, ?, ?)
        """,
        (
            id_cartao,
            mes,
            ano,
            descricao,
            valor,
            paga,
            id_usuario,
        )
    )


def criar_agendamento(
    db,
    id_usuario,
    id_conta,
    status="AGENDADO",
    recorrente=0,
    tipo="Contas a Pagar",
    valor=20
):
    return db.execute_insert(
        """
        INSERT INTO agendamentos (
            Tipo, Data, Valor, Descricao, Status, ID_Conta,
            ID_Usuario, Recorrente, Periodicidade, Ativo
        )
        VALUES (?, '2026-07-26', ?, 'Agendamento teste', ?, ?, ?, ?,
                'Mensal', 1)
        """,
        (
            tipo,
            valor,
            status,
            id_conta,
            id_usuario,
            recorrente,
        )
    )


def saldo(db, id_conta):
    return db.fetch_one(
        "SELECT Saldo_Atual FROM contas WHERE ID_Conta = ?",
        (id_conta,)
    )["Saldo_Atual"]


def total(db, tabela):
    permitidas = {
        "transacoes",
        "agendamentos",
        "lancamentos",
        "pagamentos_fatura",
    }
    if tabela not in permitidas:
        raise ValueError("Tabela não permitida no helper de teste.")
    return db.fetch_one(f"SELECT COUNT(*) AS total FROM {tabela}")["total"]


def dados_baixa(id_agendamento, id_conta, valor=20):
    return {
        "ID_Agendamento": id_agendamento,
        "ID_Conta": id_conta,
        "Descricao": "Baixa teste",
        "Data": "2026-07-26",
        "Valor_Previsto": valor,
        "Desconto": 0,
        "Multa": 0,
        "Juros": 0,
    }
