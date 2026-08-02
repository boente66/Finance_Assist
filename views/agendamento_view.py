# -*- coding: utf-8 -*-
"""Visão unificada de agendamentos e faturas virtuais."""

import logging
import os
from datetime import date, datetime, timedelta

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from controllers.schedule_controller import ScheduleController
from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter
from utilitarios.ion_path import IonPath
from views.agendamento_dialog import AgendamentoDialog
from views.responsive_layout import FlowLayout

logger = logging.getLogger(__name__)


class AgendamentoView(QWidget):
    open_invoice_requested = pyqtSignal(int, int, int)

    FILTER_ALL = "TODOS"
    FILTER_RECEIVE = "RECEBER"
    FILTER_PAY = "PAGAR"
    FILTER_TRANSFER = "TRANSFERENCIAS"
    FILTER_INVOICES = "FATURAS"

    def __init__(self, parent=None, schedule_controller=None):
        super().__init__(parent)
        self.schedule_controller = schedule_controller or ScheduleController()
        self.data = []
        self.filtered_data = []
        self.totals = {}
        self._icon_cache = {}
        self._loading_error = None
        self._init_ui()
        self._connect_signals()
        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()
        self.load_data()

    def _icon(self, name):
        if name not in self._icon_cache:
            path = IonPath.resource("assets", "icons", f"{name}.svg")
            self._icon_cache[name] = QIcon(path) if os.path.exists(path) else QIcon()
        return self._icon_cache[name]

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")
        self.subtitle.setWordWrap(True)
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.period_combo = QComboBox()
        self.period_combo.addItem("3 meses", 3)
        self.period_combo.addItem("6 meses", 6)
        self.period_combo.addItem("12 meses", 12)
        self.period_combo.setCurrentIndex(2)
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.setIcon(self._icon("refresh"))
        header.addWidget(self.period_combo)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.actions_layout = FlowLayout(horizontal_spacing=8, vertical_spacing=8)
        self.btn_add = QPushButton()
        self.btn_edit = QPushButton()
        self.btn_exec = QPushButton()
        self.btn_cancel = QPushButton()
        self.btn_edit.setObjectName("secondaryButton")
        self.btn_exec.setObjectName("secondaryButton")
        self.btn_cancel.setObjectName("dangerButton")
        for button, icon in (
            (self.btn_add, "add"), (self.btn_edit, "edit"),
            (self.btn_exec, "pay"), (self.btn_cancel, "delete"),
        ):
            button.setIcon(self._icon(icon))
            self.actions_layout.addWidget(button)
        root.addLayout(self.actions_layout)

        filters = QFrame()
        filters.setObjectName("card")
        filter_layout = QVBoxLayout(filters)
        self.quick_filter_layout = FlowLayout(horizontal_spacing=7, vertical_spacing=7)
        self.quick_buttons = {}
        for code in (
            self.FILTER_ALL, self.FILTER_RECEIVE, self.FILTER_PAY,
            self.FILTER_TRANSFER, self.FILTER_INVOICES,
        ):
            button = QPushButton()
            button.setObjectName("filterButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, value=code: self.apply_quick_filter(value))
            self.quick_buttons[code] = button
            self.quick_filter_layout.addWidget(button)
        self.quick_buttons[self.FILTER_ALL].setChecked(True)
        filter_layout.addLayout(self.quick_filter_layout)
        self.fields_filter_layout = FlowLayout(horizontal_spacing=7, vertical_spacing=7)
        self.combo_status = QComboBox()
        for label, value in (
            ("Todos", "TODOS"), ("Pendentes", "PENDENTES"),
            ("Executados", "EXECUTADOS"), ("Cancelados", "CANCELADOS"),
        ):
            self.combo_status.addItem(label, value)
        self.combo_conta = QComboBox()
        self.combo_categoria = QComboBox()
        self.combo_pessoa = QComboBox()
        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(230)
        for widget in (self.combo_status, self.combo_conta, self.combo_categoria, self.combo_pessoa):
            self.fields_filter_layout.addWidget(widget)
        self.fields_filter_layout.addWidget(self.search_input)
        filter_layout.addLayout(self.fields_filter_layout)
        root.addWidget(filters)

        self.error_label = QLabel()
        self.error_label.setObjectName("warning")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        root.addWidget(self.error_label)

        self.table = QTableWidget(0, 10)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(5, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        summary = QFrame()
        summary.setObjectName("card")
        self.summary_layout = QGridLayout(summary)
        self.summary_layout.setSpacing(10)
        self.summary_labels = {}
        self.summary_widgets = []
        for index, key in enumerate(("receber", "agendamentos_pagar", "faturas", "pagar", "resultado")):
            item = QFrame()
            item.setObjectName("summaryItem")
            box = QVBoxLayout(item)
            caption = QLabel()
            caption.setObjectName("cardTitle")
            value = QLabel()
            value.setObjectName("cardValue")
            box.addWidget(caption)
            box.addWidget(value)
            self.summary_layout.addWidget(item, 0, index)
            self.summary_widgets.append(item)
            self.summary_labels[key] = (caption, value)
        root.addWidget(summary)
        self.set_compact_mode(False, self.width())

    def set_compact_mode(self, compact, available_width=None):
        width = int(available_width or self.width())
        columns = 5 if width >= 1200 else 3 if width >= 820 else 2
        for item in self.summary_widgets:
            self.summary_layout.removeWidget(item)
        for index, item in enumerate(self.summary_widgets):
            self.summary_layout.addWidget(item, index // columns, index % columns)
        for column in range(5):
            self.summary_layout.setColumnStretch(column, 1 if column < columns else 0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        if width >= 980:
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "summary_widgets"):
            self.set_compact_mode(event.size().width() < 980, event.size().width())

    def _connect_signals(self):
        self.refresh_btn.clicked.connect(self.load_data)
        self.period_combo.currentIndexChanged.connect(self.load_data)
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        self.btn_exec.clicked.connect(self.execute_agendamento)
        self.btn_cancel.clicked.connect(self.cancel_agendamento)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected_item())
        self.combo_status.currentIndexChanged.connect(self.load_data)
        self.combo_conta.currentIndexChanged.connect(self.load_data)
        self.combo_categoria.currentIndexChanged.connect(self.load_data)
        self.combo_pessoa.currentIndexChanged.connect(self.load_data)
        self.search_input.textChanged.connect(self.apply_filter)

    def _atualizar_textos(self, *_):
        self.setWindowTitle(TranslatorApp.get("Agendamentos"))
        self.title.setText(TranslatorApp.get("Agendamentos"))
        self.subtitle.setText(TranslatorApp.get("Planeje receitas, pagamentos e transferências futuras"))
        self.refresh_btn.setText(TranslatorApp.get("Atualizar"))
        self.period_combo.setItemText(0, TranslatorApp.get("3 meses"))
        self.period_combo.setItemText(1, TranslatorApp.get("6 meses"))
        self.period_combo.setItemText(2, TranslatorApp.get("12 meses"))
        for index, label in enumerate(("Todos", "Pendentes", "Executados", "Cancelados")):
            self.combo_status.setItemText(index, TranslatorApp.get(label))
        self.btn_add.setText(TranslatorApp.get("Novo"))
        self.btn_edit.setText(TranslatorApp.get("Editar"))
        self.btn_exec.setText(TranslatorApp.get("Executar / Abrir"))
        self.btn_cancel.setText(TranslatorApp.get("Cancelar"))
        labels = {
            self.FILTER_ALL: "Todos", self.FILTER_RECEIVE: "A receber",
            self.FILTER_PAY: "A pagar", self.FILTER_TRANSFER: "Transferências",
            self.FILTER_INVOICES: "Faturas",
        }
        for code, button in self.quick_buttons.items():
            button.setText(TranslatorApp.get(labels[code]))
        self.search_input.setPlaceholderText(TranslatorApp.get("Buscar descrição, favorecido ou cartão"))
        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("Data / Vencimento"), TranslatorApp.get("Período"),
            TranslatorApp.get("Descrição"), TranslatorApp.get("Origem"),
            TranslatorApp.get("Categoria"), TranslatorApp.get("Favorecido / Cartão"),
            TranslatorApp.get("Conta"), TranslatorApp.get("Valor"),
            TranslatorApp.get("Status"), TranslatorApp.get("Detalhe"),
        ])
        captions = {
            "receber": "Total a receber", "agendamentos_pagar": "Agendamentos a pagar",
            "faturas": "Faturas em aberto", "pagar": "Total geral a pagar",
            "resultado": "Resultado previsto",
        }
        for key, (caption, value) in self.summary_labels.items():
            caption.setText(TranslatorApp.get(captions[key]))
            value.setText(CurrencyFormatter.format(self.totals.get(key, 0)))
        self._update_buttons()

    def on_load(self):
        self.load_data()

    def load_data(self):
        try:
            projection = self.schedule_controller.get_financial_projection(
                self.period_combo.currentData() or 12
            )
            self.data = projection.get("itens", [])
            self.totals = projection.get("totais", {})
            self._loading_error = None
            self.error_label.hide()
            self._rebuild_dynamic_filters()
            self.apply_filter()
        except Exception as exc:
            logger.exception("Erro ao consultar a projeção financeira")
            self.data = []
            self.totals = {}
            self._loading_error = exc
            self.error_label.setText(TranslatorApp.get(
                "Não foi possível carregar a projeção. Tente atualizar novamente."
            ))
            self.error_label.show()
            self._render_rows([])
            self._atualizar_textos()

    def _rebuild_dynamic_filters(self):
        current = {
            "conta": self.combo_conta.currentData(),
            "categoria": self.combo_categoria.currentData(),
            "pessoa": self.combo_pessoa.currentData(),
        }
        values = {
            "conta": sorted({i["conta"] for i in self.data if i.get("conta")}),
            "categoria": sorted({i["categoria"] for i in self.data if i.get("categoria")}),
            "pessoa": sorted({i["favorecido"] for i in self.data if i.get("favorecido")}),
        }
        for key, combo in (("conta", self.combo_conta), ("categoria", self.combo_categoria), ("pessoa", self.combo_pessoa)):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(TranslatorApp.get("Todos"), None)
            for value in values[key]:
                combo.addItem(value, value)
            index = combo.findData(current[key])
            combo.setCurrentIndex(max(0, index))
            combo.blockSignals(False)

    def apply_quick_filter(self, code):
        code = code or self.FILTER_ALL
        for item_code, button in self.quick_buttons.items():
            button.setChecked(item_code == code)
        self.load_data()

    def _quick_filter(self):
        return next((code for code, button in self.quick_buttons.items() if button.isChecked()), self.FILTER_ALL)

    def apply_filter(self, *_):
        quick = self._quick_filter()
        status_filter = self.combo_status.currentData() or "TODOS"
        account = self.combo_conta.currentData()
        category = self.combo_categoria.currentData()
        person = self.combo_pessoa.currentData()
        term = self.search_input.text().strip().casefold()
        pending = {"AGENDADO", "ATRASADO", "PENDENTE", "A_PAGAR"}
        executed = {"EXECUTADO", "PAGO"}
        filtered = []
        for item in self.data:
            if quick == self.FILTER_RECEIVE and item["tipo"] != "Contas a Receber":
                continue
            if quick == self.FILTER_PAY and item["tipo"] != "Contas a Pagar":
                continue
            if quick == self.FILTER_TRANSFER and item["tipo_origem"] != "TRANSFERENCIA":
                continue
            if quick == self.FILTER_INVOICES and item["tipo_origem"] != "FATURA_CARTAO":
                continue
            if status_filter == "PENDENTES" and item["status"] not in pending:
                continue
            if status_filter == "EXECUTADOS" and item["status"] not in executed:
                continue
            if status_filter == "CANCELADOS" and item["status"] != "CANCELADO":
                continue
            if account and item.get("conta") != account:
                continue
            if category and item.get("categoria") != category:
                continue
            if person and item.get("favorecido") != person:
                continue
            searchable = " ".join(str(item.get(k) or "") for k in ("descricao", "detalhe", "favorecido", "categoria", "conta")).casefold()
            if term and term not in searchable:
                continue
            filtered.append(item)
        self.filtered_data = filtered
        self._render_rows(filtered)
        self._atualizar_textos()

    def _render_rows(self, items):
        self.table.setRowCount(0)
        if not items and not self._loading_error:
            self.table.setRowCount(1)
            empty = QTableWidgetItem(TranslatorApp.get("Nenhum compromisso no período"))
            empty.setTextAlignment(Qt.AlignCenter)
            self.table.setSpan(0, 0, 1, self.table.columnCount())
            self.table.setItem(0, 0, empty)
            return
        for item in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                DateFormatter.iso_to_br(item.get("data") or ""),
                self._period_label(item.get("data")), self._display_description(item),
                TranslatorApp.get(item.get("origem") or ""), item.get("categoria"),
                item.get("favorecido"), item.get("conta"),
                CurrencyFormatter.format(item.get("valor", 0)),
                TranslatorApp.get(self._status_label(item.get("status"))),
                TranslatorApp.get(item.get("detalhe") or ""),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value or "—"))
                if column == 0:
                    cell.setData(Qt.UserRole, item)
                if column == 7:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    cell.setForeground(QColor(
                        ThemeManager.get_color("danger") if item["tipo"] == "Contas a Pagar"
                        else ThemeManager.get_color("success")
                    ))
                self.table.setItem(row, column, cell)

    @staticmethod
    def _display_description(item):
        if item.get("tipo_origem") != "FATURA_CARTAO":
            return item.get("descricao") or ""
        month = DateFormatter.map_nome_mes(int(item["competencia_mes"]))
        return f"{TranslatorApp.get('Fatura')} – {month} {item['competencia_ano']}"

    @staticmethod
    def _status_label(status):
        return {
            "A_PAGAR": "A pagar", "AGENDADO": "Agendado", "ATRASADO": "Atrasado",
            "EXECUTADO": "Executado", "PAGO": "Pago", "CANCELADO": "Cancelado",
        }.get(status, status or "")

    @staticmethod
    def _period_label(iso_date):
        try:
            target = datetime.strptime(iso_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return "—"
        today = date.today()
        if target < today:
            return TranslatorApp.get("Atrasados")
        if target == today:
            return TranslatorApp.get("Hoje")
        if target <= today + timedelta(days=7):
            return TranslatorApp.get("Próximos 7 dias")
        if target.month == today.month and target.year == today.year:
            return TranslatorApp.get("Restante do mês")
        return TranslatorApp.get("Meses seguintes")

    def _selected_item(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        cell = self.table.item(rows[0].row(), 0)
        return cell.data(Qt.UserRole) if cell else None

    def _get_selected_ids(self):
        item = self._selected_item()
        return [item["id_agendamento"]] if item and item.get("id_agendamento") else []

    def _update_buttons(self):
        item = self._selected_item()
        invoice = bool(item and item.get("tipo_origem") == "FATURA_CARTAO")
        self.btn_edit.setEnabled(bool(item))
        self.btn_exec.setEnabled(bool(item))
        self.btn_cancel.setEnabled(bool(item) and not invoice and item.get("status") in ("AGENDADO", "ATRASADO"))
        if invoice:
            self.btn_edit.setToolTip(TranslatorApp.get("Abrir painel da fatura"))
            self.btn_exec.setText(TranslatorApp.get("Pagar fatura"))
        else:
            self.btn_edit.setToolTip("")
            self.btn_exec.setText(TranslatorApp.get("Executar"))

    def open_selected_item(self):
        item = self._selected_item()
        if not item:
            return
        if item["tipo_origem"] == "FATURA_CARTAO":
            self.open_invoice_requested.emit(
                int(item["id_cartao"]), int(item["competencia_mes"]), int(item["competencia_ano"])
            )
        else:
            self.open_edit_dialog()

    def open_add_dialog(self):
        if AgendamentoDialog(self).exec_():
            self.load_data()

    def open_edit_dialog(self):
        item = self._selected_item()
        if not item:
            return
        if item["tipo_origem"] == "FATURA_CARTAO":
            self.open_selected_item()
            return
        dialog = AgendamentoDialog(self, agendamento_id=item["id_agendamento"])
        if dialog.exec_():
            self.load_data()

    def cancel_agendamento(self):
        item = self._selected_item()
        if not item or item["tipo_origem"] == "FATURA_CARTAO":
            return
        if self.schedule_controller.cancelar_agendamento(item["id_agendamento"]):
            self.load_data()

    def execute_agendamento(self):
        item = self._selected_item()
        if not item:
            return
        if item["tipo_origem"] == "FATURA_CARTAO":
            self.open_selected_item()
            return
        agendamento = self.schedule_controller.get_schedule_by_id(item["id_agendamento"])
        if not agendamento:
            return
        from views.execute_schedule_dialog import ExecuteScheduleDialog
        dialog = ExecuteScheduleDialog(parent=self, agendamento=agendamento)
        if not dialog.exec_():
            return
        resultado = self.schedule_controller.execute_schedule(dialog.get_dados_execucao())
        if not resultado.get("sucesso"):
            QMessageBox.warning(self, TranslatorApp.get("Aviso"), TranslatorApp.get(
                resultado.get("mensagem", "Não foi possível executar o agendamento.")
            ))
            return
        self.load_data()

    # Métodos legados mantidos para integrações externas da view.
    def load_favorecidos(self):
        self._rebuild_dynamic_filters()

    def load_cartao(self):
        self.apply_filter()

    def load_historico(self):
        self.apply_filter()

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass
        super().closeEvent(event)
