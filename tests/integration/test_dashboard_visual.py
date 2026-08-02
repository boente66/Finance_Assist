import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication

import views.resumo_financeiro_view as dashboard_module
from core.session import Session
from core.theme_manager import ThemeManager


class AccountControllerStub:
    def get_all_accounts(self):
        return [{"Nome_Conta": "Conta teste", "Tipo": "Corrente", "Saldo_Atual": 1250}]


class CardControllerStub:
    def get_all_cartoes(self):
        return [{"ID_Cartao": 1, "Nome": "Cartão teste"}]

    def obter_valor_fatura_atual(self, card_id):
        assert card_id == 1
        return 320


class TransactionControllerStub:
    def get_resumo_financeiro(self):
        return {"Receitas": 2100, "Despesas": 800}

    def get_analise_mensal(self):
        return {"Saldo_Atual": 1250, "Receitas": 2100, "Despesas": 800}


class ScheduleControllerStub:
    def get_upcoming_schedules(self):
        return [{"Data": "2026-08-10", "Descricao": "Conta", "Valor": -150}]


class GoalControllerStub:
    def listar_metas_ativas(self):
        return [{"Nome": "Reserva", "Progresso": {"percentual": 40}}]


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    ThemeManager.aplicar_tema("Primavera", application)
    return application


def test_dashboard_usa_hierarquia_do_modelo_sem_alterar_controllers(monkeypatch, app):
    monkeypatch.setattr(dashboard_module, "AccountController", AccountControllerStub)
    monkeypatch.setattr(dashboard_module, "FaturaController", CardControllerStub)
    monkeypatch.setattr(dashboard_module, "TransactionController", TransactionControllerStub)
    monkeypatch.setattr(dashboard_module, "ScheduleController", ScheduleControllerStub)
    monkeypatch.setattr(dashboard_module, "MetaController", GoalControllerStub)
    Session.set_usuario({"ID_Usuario": 99, "Nome": "Leonardo"})

    view = dashboard_module.ResumoFinanceiroView()
    assert view.metric_accounts.value.text()
    assert view.metric_cards.value.text()
    assert view.metric_income.value.text()
    assert view.metric_expense.value.text()
    assert view.metric_result.value.text()
    assert view.chart_panel.objectName() == "dashboardPanel"
    assert view.schedules_panel.objectName() == "dashboardPanel"
    assert view.goals_panel.objectName() == "dashboardPanel"
    assert "Leonardo" in view.title.text()
    view.close()
