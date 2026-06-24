# -*- coding: utf-8 -*-
import logging
import os

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QAbstractItemView,
    QHeaderView,
    QFrame,
    QSplitter,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from views.agendamento_dialog import AgendamentoDialog
from controllers.schedule_controller import ScheduleController
from controllers.account_controller import AccountController
from controllers.fatura_controller import FaturaController
from controllers.favorecido_controller import FavorecidoController

from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter
from utilitarios.ion_path import IonPath

from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class AgendamentoView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.schedule_controller = ScheduleController()
        self.account_controller = AccountController()
        self.fatura_controller = FaturaController()
        self.favorecido_controller = FavorecidoController()
        

        self._icon_cache = {}

        self.data = []
        self.filtered_data = []

        self.total_pagar = 0
        self.total_receber = 0
        self.total_previsto = 0

        self._init_ui()
        self._connect_signals()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self.load_favorecidos()
        self.load_cartao()
        self.load_data()

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)

    # ==================================================
    # ICON
    # ==================================================
    def _icon(self, nome: str) -> QIcon:

        if nome in self._icon_cache:
            return self._icon_cache[nome]

        path = IonPath.resource(
            "assets",
            "icons",
            f"{nome}.svg"
        )

        icon = QIcon(path) if os.path.exists(path) else QIcon()

        self._icon_cache[nome] = icon

        return icon

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):

        main_layout = QHBoxLayout(self)

        # --------------------------------------------------
        # SIDEBAR
        # --------------------------------------------------
        sidebar = QFrame()

        sidebar_layout = QVBoxLayout(sidebar)

        self.btn_all = QPushButton()
        self.btn_receber = QPushButton()
        self.btn_pagar = QPushButton()
        self.btn_transfer = QPushButton()

        sidebar_layout.addWidget(self.btn_all)
        sidebar_layout.addWidget(self.btn_receber)
        sidebar_layout.addWidget(self.btn_pagar)
        sidebar_layout.addWidget(self.btn_transfer)

        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar, 1)

        # --------------------------------------------------
        # MAIN
        # --------------------------------------------------
        container = QWidget()

        layout = QVBoxLayout(container)

        layout.addLayout(self._create_toolbar())

        self.main_splitter = QSplitter(Qt.Vertical)

        # TOPO
        top = QWidget()

        top_layout = QVBoxLayout(top)

        self.table = self._create_table()

        top_layout.addWidget(self.table)
        top_layout.addLayout(self._create_cards())

        self.main_splitter.addWidget(top)

        # BASE
        self.bottom_splitter = QSplitter(Qt.Vertical)

        self.fatura_group = self._create_fatura()
        self.historico_group = self._create_historico()

        self.bottom_splitter.addWidget(self.fatura_group)
        self.bottom_splitter.addWidget(self.historico_group)

        self.main_splitter.addWidget(self.bottom_splitter)

        layout.addWidget(self.main_splitter)

        main_layout.addWidget(container, 4)

    # ==================================================
    # SIGNALS
    # ==================================================
    def _connect_signals(self):

        self.btn_all.clicked.connect(
            lambda: self.apply_quick_filter(None)
        )

        self.btn_receber.clicked.connect(
            lambda: self.apply_quick_filter("Contas a Receber")
        )

        self.btn_pagar.clicked.connect(
            lambda: self.apply_quick_filter("Contas a Pagar")
        )

        self.btn_transfer.clicked.connect(
            lambda: self.apply_quick_filter("Transferências")
        )

        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        self.btn_exec.clicked.connect(self.execute_agendamento)
        self.btn_cancel.clicked.connect(self.cancel_agendamento)

        self.combo_tipo.currentIndexChanged.connect(
            self.apply_filter
        )

        self.combo_status.currentIndexChanged.connect(
            self.apply_filter
        )

        self.combo_favorecido.currentIndexChanged.connect(
            self.apply_filter
        )

        self.search_input.textChanged.connect(
            self.apply_filter
        )

        self.cartao_filter.currentIndexChanged.connect(
            self.apply_filter
        )

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self):

        self.setWindowTitle(
            TranslatorApp.get("Agendamentos")
        )

        # SIDEBAR
        self.btn_all.setText(
            TranslatorApp.get("Todos")
        )

        self.btn_receber.setText(
            TranslatorApp.get("Receber")
        )

        self.btn_pagar.setText(
            TranslatorApp.get("Pagar")
        )

        self.btn_transfer.setText(
            TranslatorApp.get("Transferência")
        )

        # TOOLBAR
        self.btn_add.setText(
            TranslatorApp.get("Novo")
        )

        self.btn_edit.setText(
            TranslatorApp.get("Editar")
        )

        self.btn_exec.setText(
            TranslatorApp.get("Executar")
        )

        self.btn_cancel.setText(
            TranslatorApp.get("Cancelar")
        )

        self.search_input.setPlaceholderText(
            TranslatorApp.get("Pesquisar...")
        )

        # GROUPS
        self.fatura_group.setTitle(
            TranslatorApp.get("💳 Fatura Prevista")
        )

        self.historico_group.setTitle(
            TranslatorApp.get("📊 Histórico")
        )

        # CARDS
        self.lbl_pagar.setText(
            f"{TranslatorApp.get('Total a Pagar')}: "
            f"{CurrencyFormatter.format(self.total_pagar)}"
        )

        self.lbl_receber.setText(
            f"{TranslatorApp.get('Total a Receber')}: "
            f"{CurrencyFormatter.format(self.total_receber)}"
        )

        total = self.total_receber - self.total_pagar

        self.lbl_total.setText(
            f"{TranslatorApp.get('Total')}: "
            f"{CurrencyFormatter.format(total)}"
        )

        self.lbl_total_fatura.setText(
            f"{TranslatorApp.get('TOTAL PREVISTO')}: "
            f"{CurrencyFormatter.format(self.total_previsto)}"
        )

        # TABLE HEADERS
        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("ID"),
            TranslatorApp.get("Data"),
            TranslatorApp.get("Descrição"),
            TranslatorApp.get("Categoria"),
            TranslatorApp.get("Favorecido"),
            TranslatorApp.get("Conta"),
            TranslatorApp.get("Valor"),
            TranslatorApp.get("Status"),
        ])

        self.table_cartao.setHorizontalHeaderLabels([
            TranslatorApp.get("Data"),
            TranslatorApp.get("Descrição"),
            TranslatorApp.get("Categoria"),
            TranslatorApp.get("Favorecido"),
            TranslatorApp.get("Valor"),
            TranslatorApp.get("Parcelas"),
            TranslatorApp.get("Status"),
        ])

        self.table_hist.setHorizontalHeaderLabels([
            TranslatorApp.get("Data"),
            TranslatorApp.get("Descrição"),
            TranslatorApp.get("Valor"),
            TranslatorApp.get("Status"),
        ])

    # ==================================================
    # RESPONSIVO
    # ==================================================
    def resizeEvent(self, event):

        super().resizeEvent(event)

        h = self.height()

        topo = int(h * 0.5)
        base = int(h * 0.5)

        fatura = int(base * 0.5)
        historico = int(base * 0.5)

        try:
            self.main_splitter.setSizes([topo, base])
            self.bottom_splitter.setSizes([fatura, historico])
        except Exception:
            pass

    # ==================================================
    # TOOLBAR
    # ==================================================
    def _create_toolbar(self):

        layout = QHBoxLayout()

        self.btn_add = QPushButton()
        self.btn_edit = QPushButton()
        self.btn_exec = QPushButton()
        self.btn_cancel = QPushButton()

        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_exec)
        layout.addWidget(self.btn_cancel)

        layout.addStretch()

        self.combo_tipo = QComboBox()

        self.combo_tipo.addItems([
            "Todos",
            "Contas a Receber",
            "Contas a Pagar",
            "Transferências",
        ])

        self.combo_status = QComboBox()

        self.combo_status.addItems([
            "Todos",
            "AGENDADO",
            "PAGO",
            "CANCELADO",
        ])

        self.combo_favorecido = QComboBox()

        self.search_input = QLineEdit()

        layout.addWidget(self.combo_tipo)
        layout.addWidget(self.combo_status)
        layout.addWidget(self.combo_favorecido)
        layout.addWidget(self.search_input)

        return layout

    # ==================================================
    # TABLE
    # ==================================================
    def _create_table(self):

        table = QTableWidget(0, 8)

        table.setColumnHidden(0, True)

        table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        table.itemSelectionChanged.connect(
            self._update_buttons
        )

        return table

    def _create_cards(self):

        layout = QHBoxLayout()

        self.lbl_pagar = QLabel()
        self.lbl_receber = QLabel()
        self.lbl_total = QLabel()

        layout.addWidget(self.lbl_pagar)
        layout.addWidget(self.lbl_receber)
        layout.addWidget(self.lbl_total)

        return layout

    def _update_buttons(self):

        has_selection = len(
            self._get_selected_ids()
        ) > 0

        self.btn_edit.setEnabled(has_selection)
        self.btn_cancel.setEnabled(has_selection)

    def _get_selected_ids(self):

        rows = self.table.selectionModel().selectedRows()

        return [
            int(self.table.item(r.row(), 0).text())
            for r in rows
        ]

    # ==================================================
    # LOAD
    # ==================================================
    def load_data(self):

        self.data = (
            self.schedule_controller.get_all_schedules() or []
        )

        self.apply_filter()

    def load_favorecidos(self):

        self.combo_favorecido.clear()

        self.combo_favorecido.addItem(
            "Todos",
            None
        )

        for favorecido in self.favorecido_controller.listar_favorecidos():

            self.combo_favorecido.addItem(
                favorecido["Nome"],
                favorecido["ID_Favorecido"]
            )

    # ==================================================
    # FILTER
    # ==================================================
    def apply_filter(self):

        tipo = self.combo_tipo.currentText()

        status = self.combo_status.currentText()

        favorecido = self.combo_favorecido.currentData()

        termo = self.search_input.text().lower()

        self.table.setRowCount(0)

        self.filtered_data = []

        self.total_pagar = 0
        self.total_receber = 0

        for ag in self.data:

            if tipo != "Todos" and ag.get("Tipo") != tipo:
                continue

            if status != "Todos" and ag.get("Status") != status:
                continue

            if favorecido and ag.get("ID_Favorecido") != favorecido:
                continue

            if termo and termo not in (
                ag.get("Descricao") or ""
            ).lower():
                continue

            self.filtered_data.append(ag)

            valor = float(ag.get("Valor", 0))

            if ag.get("Tipo") == "Contas a Pagar":
                self.total_pagar += valor

            elif ag.get("Tipo") == "Contas a Receber":
                self.total_receber += valor

            row = self.table.rowCount()

            self.table.insertRow(row)

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(
                    str(ag.get("ID_Agendamento"))
                ),
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(
                    DateFormatter.iso_to_br(
                        ag.get("Data")
                    )
                ),
            )

            self.table.setItem(
                row,
                2,
                QTableWidgetItem(
                    ag.get("Descricao", "")
                ),
            )

            self.table.setItem(
                row,
                3,
                QTableWidgetItem(
                    ag.get("Categoria", "")
                ),
            )

            self.table.setItem(
                row,
                4,
                QTableWidgetItem(
                    ag.get("Favorecido", "")
                ),
            )

            self.table.setItem(
                row,
                5,
                QTableWidgetItem(
                    ag.get("Conta", "")
                ),
            )

            self.table.setItem(
                row,
                6,
                QTableWidgetItem(
                    CurrencyFormatter.format(valor)
                ),
            )

            self.table.setItem(
                row,
                7,
                QTableWidgetItem(
                    ag.get("Status", "")
                ),
            )

        self.load_cartao()
        self.load_historico()
        self._atualizar_textos()

    # ==================================================
    # FATURA
    # ==================================================
    def _create_fatura(self):

        group = QGroupBox()

        layout = QVBoxLayout(group)

        self.cartao_filter = QComboBox()

        layout.addWidget(self.cartao_filter)

        self.table_cartao = QTableWidget(0, 7)

        self.table_cartao.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        layout.addWidget(self.table_cartao)

        self.lbl_total_fatura = QLabel()

        layout.addWidget(self.lbl_total_fatura)

        return group

    def load_cartao(self):

        self.table_cartao.setRowCount(0)

        self.total_previsto = 0

        id_cartao = self.cartao_filter.currentData()

        if not id_cartao:
            self._atualizar_textos()
            return

        for ag in self.filtered_data:

            if ag.get("ID_Cartao") != id_cartao:
                continue

            valor = float(ag.get("Valor", 0))

            self.total_previsto += valor

            row = self.table_cartao.rowCount()

            self.table_cartao.insertRow(row)

            self.table_cartao.setItem(
                row,
                0,
                QTableWidgetItem(
                    DateFormatter.iso_to_br(
                        ag.get("Data")
                    )
                ),
            )

            self.table_cartao.setItem(
                row,
                1,
                QTableWidgetItem(
                    ag.get("Descricao", "")
                ),
            )

            self.table_cartao.setItem(
                row,
                4,
                QTableWidgetItem(
                    CurrencyFormatter.format(valor)
                ),
            )

        self._atualizar_textos()

    # ==================================================
    # HISTÓRICO
    # ==================================================
    def _create_historico(self):

        group = QGroupBox()

        layout = QVBoxLayout(group)

        self.table_hist = QTableWidget(0, 4)

        self.table_hist.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        layout.addWidget(self.table_hist)

        return group

    def load_historico(self):

        self.table_hist.setRowCount(0)

        for ag in self.filtered_data:

            if ag.get("Status") != "PAGO":
                continue

            row = self.table_hist.rowCount()

            self.table_hist.insertRow(row)

            self.table_hist.setItem(
                row,
                0,
                QTableWidgetItem(
                    DateFormatter.iso_to_br(
                        ag.get("Data")
                    )
                ),
            )

            self.table_hist.setItem(
                row,
                1,
                QTableWidgetItem(
                    ag.get("Descricao", "")
                ),
            )

            self.table_hist.setItem(
                row,
                2,
                QTableWidgetItem(
                    CurrencyFormatter.format(
                        float(ag.get("Valor", 0))
                    )
                ),
            )

            self.table_hist.setItem(
                row,
                3,
                QTableWidgetItem(
                    TranslatorApp.get("Pago")
                ),
            )

    # ==================================================
    # ACTIONS
    # ==================================================
    def open_add_dialog(self):

        dlg = AgendamentoDialog(self)

        if dlg.exec_():
            self.load_data()

    def open_edit_dialog(self):

        ids = self._get_selected_ids()

        if not ids:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get(
                    "Selecione um agendamento"
                ),
            )
            return

        dlg = AgendamentoDialog(
            self,
            agendamento_id=ids[0]
        )

        if dlg.exec_():
            self.load_data()

    def cancel_agendamento(self):

        ids = self._get_selected_ids()

        if not ids:
            return

        for ag_id in ids:
            self.schedule_controller.cancelar_agendamento(
                ag_id
            )

        self.load_data()

    def execute_agendamento(self):

        ids = self._get_selected_ids()

        if not ids:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get(
                    "Selecione um agendamento."
                ),
            )
            return

        if len(ids) > 1:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get(
                    "Selecione apenas um agendamento."
                ),
            )
            return

        agendamento = self.schedule_controller.get_schedule_by_id(
            ids[0]
        )

        if not agendamento:
            return

        from views.execute_schedule_dialog import ExecuteScheduleDialog

        dialog = ExecuteScheduleDialog(
            parent=self,
            agendamento=agendamento
        )

        if dialog.exec_():

            dados_execucao = dialog.get_dados_execucao()

            self.schedule_controller.execute_schedule(
                dados_execucao
            )

            self.load_data()

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get(
                    "Agendamento executado com sucesso."
                ),
            )

    def apply_quick_filter(self, tipo):

        self.combo_tipo.setCurrentText(
            tipo or "Todos"
        )