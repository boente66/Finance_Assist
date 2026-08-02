# -*- coding: utf-8 -*-
"""Dashboard financeiro: composição visual sem regras de negócio locais."""

import logging
from datetime import datetime

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from controllers.account_controller import AccountController
from controllers.fatura_controller import FaturaController
from controllers.meta_controller import MetaController
from controllers.schedule_controller import ScheduleController
from controllers.transaction_controller import TransactionController
from core.session import Session
from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter

logger = logging.getLogger(__name__)


class MetricCard(QFrame):
    """Card puramente apresentacional para um indicador do dashboard."""

    def __init__(self, symbol, label, hint="", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(112)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 14, 14)
        layout.setSpacing(10)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        self.label = QLabel(label)
        self.label.setObjectName("metricLabel")
        self.value = QLabel(CurrencyFormatter.format(0))
        self.value.setObjectName("metricValue")
        self.hint = QLabel(hint)
        self.hint.setObjectName("metricHint")
        copy.addWidget(self.label)
        copy.addWidget(self.value)
        copy.addWidget(self.hint)
        icon = QLabel(symbol)
        icon.setObjectName("metricIcon")
        icon.setAlignment(Qt.AlignCenter)
        layout.addLayout(copy, 1)
        layout.addWidget(icon)

    def set_value(self, value, tone="neutral"):
        self.value.setText(CurrencyFormatter.format(float(value or 0)))
        names = {
            "positive": "metricValuePositive",
            "negative": "metricValueNegative",
            "warning": "metricValueWarning",
        }
        self.value.setObjectName(names.get(tone, "metricValue"))
        self.value.style().unpolish(self.value)
        self.value.style().polish(self.value)


class ResumoFinanceiroView(QWidget):
    """Resumo que orquestra controllers existentes e somente apresenta respostas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.account_controller = AccountController()
        self.schedule_controller = ScheduleController()
        self.transaction_controller = TransactionController()
        self.fatura_controller = FaturaController()
        self.meta_controller = MetaController()
        self._canvas = None
        self.setWindowTitle("Resumo Financeiro")
        self._init_ui()
        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _panel(self, title, action_text=None, action=None):
        panel = QFrame()
        panel.setObjectName("dashboardPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        header = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("panelTitle")
        header.addWidget(label)
        header.addStretch()
        if action_text:
            button = QPushButton(action_text)
            button.setObjectName("linkButton")
            if action:
                button.clicked.connect(action)
            header.addWidget(button)
        layout.addLayout(header)
        return panel, layout, label

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(18, 16, 18, 18)
        self.main_layout.setSpacing(16)
        scroll.setWidget(container)
        outer.addWidget(scroll)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        usuario = Session.get_usuario() or {}
        nome = usuario.get("Nome") or TranslatorApp.get("Usuário")
        self.title = QLabel(f"Olá, {nome}")
        self.title.setObjectName("dashboardGreeting")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.clicked.connect(self.load_data)
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(self.refresh_btn)
        self.main_layout.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.metric_accounts = MetricCard("▣", "Saldo total das contas", "Contas cadastradas")
        self.metric_cards = MetricCard("▤", "Cartões de crédito", "Faturas em aberto")
        self.metric_income = MetricCard("↗", "Receitas do mês", "Até o momento")
        self.metric_expense = MetricCard("↘", "Despesas do mês", "Até o momento")
        self.metric_result = MetricCard("◴", "Resultado do mês", "Receitas - Despesas")
        for card in (
            self.metric_accounts, self.metric_cards, self.metric_income,
            self.metric_expense, self.metric_result,
        ):
            metrics.addWidget(card)
        self.main_layout.addLayout(metrics)

        middle = QHBoxLayout()
        middle.setSpacing(16)
        self.chart_panel, self.chart_layout, self.chart_title = self._panel(
            "Receitas x Despesas do mês", "Ver relatório", lambda: self._navigate("btn_relatorios")
        )
        self.chart_content = QVBoxLayout()
        self.chart_layout.addLayout(self.chart_content)
        middle.addWidget(self.chart_panel, 3)

        self.schedules_panel, schedules_box, self.schedules_title = self._panel(
            "Próximos lançamentos", "Ver todos", lambda: self._navigate("btn_agendamentos")
        )
        self.schedules_layout = QVBoxLayout()
        schedules_box.addLayout(self.schedules_layout)
        middle.addWidget(self.schedules_panel, 2)
        self.main_layout.addLayout(middle)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        self.analysis_panel, analysis_box, self.analysis_title = self._panel("Análise do mês")
        self.analysis_layout = QVBoxLayout()
        analysis_box.addLayout(self.analysis_layout)
        lower.addWidget(self.analysis_panel, 1)

        self.goals_panel, goals_box, self.goals_title = self._panel(
            "Metas em andamento", "Ver todas", lambda: self._navigate("btn_metas")
        )
        self.goals_layout = QVBoxLayout()
        goals_box.addLayout(self.goals_layout)
        lower.addWidget(self.goals_panel, 1)

        self.accounts_panel, accounts_box, self.accounts_title = self._panel(
            "Contas e cartões", "Gerenciar", lambda: self._navigate("btn_transacoes")
        )
        self.accounts_layout = QVBoxLayout()
        accounts_box.addLayout(self.accounts_layout)
        lower.addWidget(self.accounts_panel, 1)
        self.main_layout.addLayout(lower)

        tip = QFrame()
        tip.setObjectName("financeTip")
        tip_layout = QHBoxLayout(tip)
        tip_layout.setContentsMargins(14, 8, 14, 8)
        self.tip_label = QLabel()
        self.tip_label.setObjectName("secondary")
        tip_layout.addWidget(QLabel("◉"))
        tip_layout.addWidget(self.tip_label, 1)
        self.main_layout.addWidget(tip)

    def _navigate(self, button_name):
        parent = self.parentWidget()
        while parent is not None:
            button = getattr(parent, button_name, None)
            if button is not None:
                button.click()
                return
            parent = parent.parentWidget()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                ResumoFinanceiroView._clear_layout(item.layout())

    @staticmethod
    def _format(value):
        try:
            return CurrencyFormatter.format(float(value or 0))
        except (TypeError, ValueError):
            return CurrencyFormatter.format(0)

    def _atualizar_textos(self, *_):
        self.setWindowTitle(TranslatorApp.get("Resumo Financeiro"))
        usuario = Session.get_usuario() or {}
        nome = usuario.get("Nome") or TranslatorApp.get("Usuário")
        self.title.setText(f"{TranslatorApp.get('Olá')}, {nome}")
        self.subtitle.setText(TranslatorApp.get("Aqui está o resumo da sua vida financeira."))
        self.refresh_btn.setText(TranslatorApp.get("Atualizar"))
        self.tip_label.setText(TranslatorApp.get(
            "Dica financeira: acompanhe receitas, despesas e metas antes de assumir novos compromissos."
        ))
        self.load_data()

    def load_data(self):
        loaders = (
            self.load_accounts, self.load_credit_cards, self.load_scheduled_transactions,
            self.load_monthly_summary, self.load_monthly_analysis, self.load_metas,
        )
        for loader in loaders:
            try:
                loader()
            except Exception:
                logger.exception("Erro ao atualizar bloco do dashboard: %s", loader.__name__)

    def _empty(self, layout, text):
        label = QLabel(TranslatorApp.get(text))
        label.setObjectName("muted")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(52)
        layout.addWidget(label)

    def _list_row(self, title, detail, amount=None, positive=True):
        row = QFrame()
        row.setObjectName("dashboardRow")
        line = QHBoxLayout(row)
        line.setContentsMargins(2, 7, 2, 7)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        name = QLabel(str(title))
        name.setObjectName("cardTitle")
        secondary = QLabel(str(detail or ""))
        secondary.setObjectName("muted")
        copy.addWidget(name)
        copy.addWidget(secondary)
        line.addLayout(copy, 1)
        if amount is not None:
            value = QLabel(self._format(amount))
            value.setObjectName("listAmountPositive" if positive else "listAmountNegative")
            line.addWidget(value)
        return row

    def load_accounts(self):
        self._clear_layout(self.accounts_layout)
        accounts = self.account_controller.get_all_accounts() or []
        total = 0.0
        for account in accounts:
            saldo = float(account.get("Saldo_Atual", 0) or 0)
            total += saldo
            self.accounts_layout.addWidget(self._list_row(
                account.get("Nome_Conta", "Conta"), account.get("Tipo", ""), saldo, saldo >= 0
            ))
        self.metric_accounts.set_value(total, "positive" if total >= 0 else "negative")
        self.metric_accounts.hint.setText(f"{len(accounts)} {TranslatorApp.get('contas')}")
        if not accounts:
            self._empty(self.accounts_layout, "Nenhuma conta encontrada")

    def load_credit_cards(self):
        cards = self.fatura_controller.get_all_cartoes() or []
        total = 0.0
        for card in cards:
            try:
                total += float(self.fatura_controller.obter_valor_fatura_atual(card["ID_Cartao"]) or 0)
            except Exception:
                logger.exception("Erro ao obter fatura do cartão %s", card.get("ID_Cartao"))
        self.metric_cards.set_value(total, "warning" if total > 0 else "neutral")
        self.metric_cards.hint.setText(f"{len(cards)} {TranslatorApp.get('cartões')}")

    def load_scheduled_transactions(self):
        self._clear_layout(self.schedules_layout)
        scheduled = self.schedule_controller.get_upcoming_schedules() or []
        for item in scheduled[:5]:
            value = float(item.get("Valor", 0) or 0)
            date = DateFormatter.iso_to_br(item.get("Data"))
            self.schedules_layout.addWidget(self._list_row(
                item.get("Descricao") or TranslatorApp.get("Lançamento"), date, value, value >= 0
            ))
        if not scheduled:
            self._empty(self.schedules_layout, "Nenhum lançamento agendado")
        self.schedules_layout.addStretch(1)

    def load_monthly_summary(self):
        self._clear_layout(self.chart_content)
        data = self.transaction_controller.get_resumo_financeiro() or {}
        income = float(data.get("Receitas", 0) or 0)
        expense = abs(float(data.get("Despesas", 0) or 0))
        result = income - expense
        self.metric_income.set_value(income, "positive")
        self.metric_expense.set_value(expense, "negative" if expense else "neutral")
        self.metric_result.set_value(result, "positive" if result >= 0 else "negative")

        if self._canvas:
            self._canvas.deleteLater()
        colors = ThemeManager.get_chart_colors()
        figure = Figure(figsize=(5.4, 3.0), facecolor="none")
        self._canvas = FigureCanvas(figure)
        self._canvas.setMinimumHeight(260)
        axis = figure.add_subplot(111)
        axis.set_facecolor("none")
        bars = axis.bar(
            [TranslatorApp.get("Receitas"), TranslatorApp.get("Despesas")],
            [income, expense], color=[colors["receita"], colors["despesa"]], width=.48,
        )
        axis.grid(axis="y", linestyle="--", alpha=.18)
        for spine in ("top", "right", "left"):
            axis.spines[spine].set_visible(False)
        axis.tick_params(axis="both", colors=colors["text"], length=0)
        axis.bar_label(bars, labels=[self._format(income), self._format(expense)], padding=4,
                       color=colors["text"], fontsize=9)
        figure.tight_layout(pad=1.2)
        self.chart_content.addWidget(self._canvas)

    def load_monthly_analysis(self):
        self._clear_layout(self.analysis_layout)
        analysis = self.transaction_controller.get_analise_mensal() or {}
        values = (
            ("Saldo atual", float(analysis.get("Saldo_Atual", 0) or 0)),
            ("Receitas do mês", float(analysis.get("Receitas", 0) or 0)),
            ("Despesas do mês", abs(float(analysis.get("Despesas", 0) or 0))),
        )
        if not analysis:
            self._empty(self.analysis_layout, "Sem análise disponível")
            return
        for label, value in values:
            positive = label != "Despesas do mês" and value >= 0
            self.analysis_layout.addWidget(self._list_row(
                TranslatorApp.get(label), TranslatorApp.get("Mês atual"), value, positive
            ))
        self.analysis_layout.addStretch(1)

    def load_metas(self):
        self._clear_layout(self.goals_layout)
        goals = self.meta_controller.listar_metas_ativas() or []
        for goal in goals[:4]:
            progress = goal.get("Progresso") or {}
            line = QWidget()
            box = QVBoxLayout(line)
            box.setContentsMargins(2, 5, 2, 5)
            header = QHBoxLayout()
            header.addWidget(QLabel(goal.get("Nome", TranslatorApp.get("Meta"))))
            percent = int(float(progress.get("percentual", 0) or 0))
            header.addStretch()
            header.addWidget(QLabel(f"{percent}%"))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(max(0, min(percent, 100)))
            bar.setTextVisible(False)
            box.addLayout(header)
            box.addWidget(bar)
            self.goals_layout.addWidget(line)
        if not goals:
            self._empty(self.goals_layout, "Nenhuma meta ativa")
        self.goals_layout.addStretch(1)

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass
        if self._canvas:
            self._canvas.deleteLater()
            self._canvas = None
        super().closeEvent(event)
