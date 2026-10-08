import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox

import views.painel_fatura as painel_module


class FaturaControllerStub:
    def __init__(self):
        self.pagamentos = []

    def obter_resumo_fatura(self, id_cartao, mes, ano):
        return {
            "total_fatura": 100.0,
            "pagamentos": 60.0,
            "saldo_a_pagar": 40.0,
            "status": "FECHADA",
        }

    def obter_fatura_mes(self, *_args):
        raise AssertionError("A View não deve somar os lançamentos da fatura.")

    def pagar_fatura(self, id_cartao, id_conta, mes, ano, valor=None):
        self.pagamentos.append((id_cartao, id_conta, mes, ano, valor))
        return {"sucesso": True, "mensagem": "Pagamento registrado"}


class AccountControllerStub:
    def get_all_accounts(self):
        return [{"ID_Conta": 9, "Nome_Conta": "Conta principal"}]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_view_exibe_saldo_restante_oficial_no_pagamento_parcial(
    app, monkeypatch
):
    monkeypatch.setattr(painel_module, "FaturaController", FaturaControllerStub)
    monkeypatch.setattr(painel_module, "AccountController", AccountControllerStub)
    prompt = {}
    monkeypatch.setattr(
        painel_module.QInputDialog,
        "getItem",
        lambda _parent, _title, label, *_args: (
            prompt.setdefault("texto", label) and "Conta principal",
            True,
        ),
    )
    monkeypatch.setattr(
        painel_module.QMessageBox, "question", lambda *_args: QMessageBox.Yes
    )
    monkeypatch.setattr(
        painel_module.QInputDialog,
        "getDouble",
        lambda *_args: (
            prompt.setdefault("pagamento_args", _args) and 25.0,
            True,
        ),
    )
    monkeypatch.setattr(
        painel_module.QMessageBox, "information", lambda *_args: QMessageBox.Ok
    )

    panel = painel_module.PainelFatura()
    panel.cartao = {"ID_Cartao": 3, "Nome": "Cartão"}
    panel.mes_combo.blockSignals(True)
    panel.ano_combo.blockSignals(True)
    panel.mes_combo.setCurrentIndex(7)
    panel.ano_combo.setCurrentText("2026")
    panel.mes_combo.blockSignals(False)
    panel.ano_combo.blockSignals(False)
    recarregado = []
    panel._carregar = lambda: recarregado.append(True)

    panel.pagar_fatura()

    texto = prompt["texto"].replace("\xa0", " ")
    assert "R$ 40,00" in texto
    assert "R$ 100,00" not in texto
    assert prompt["pagamento_args"][4] == 5.0
    assert prompt["pagamento_args"][8] == 5.0
    assert panel.controller.pagamentos == [(3, 9, 8, 2026, 25.0)]
    assert recarregado == [True]
    panel.close()
