# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QLabel,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QInputDialog,
    QProgressDialog,
    QComboBox,
    QLineEdit,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QIcon

from controllers.transaction_controller import TransactionController
from controllers.category_controller import CategoryController
from controllers.favorecido_controller import FavorecidoController
from controllers.ia_import_controller import IAImportController
from controllers.ia_export_controller import IAExportController

from views.transaction_dialog_conta import TransactionDialogConta
from views.TransferDialog import TransferDialog
from views.editar_transacao_dialog import EditTransactionDialog

from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter
from utilitarios.ion_path import IonPath

from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class PainelAccount(QWidget):

    FILTROS = [
        ("MES", "Mês Atual"),
        ("3M", "Últimos 3 Meses"),
        ("ANO", "Ano Atual"),
        ("ALL", "Todos"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.conta = None

        self.transaction_controller = TransactionController()
        self.category_controller = CategoryController()
        self.favorecido_controller = FavorecidoController()
        self.ia_import_controller = IAImportController()
        self.ia_export_controller = IAExportController()

        self.dados_completos = []
        self.pagina_atual = 0
        self.itens_por_pagina = 50
        self.texto_busca = ""

        self.progress_bar = QProgressDialog(self)
        self.progress_bar.setWindowModality(Qt.WindowModal)
        self.progress_bar.close()

        self._icon_cache = {}

        self._montar_ui()

        TranslatorApp.bind(self._on_translate, self)
        self._on_translate()

    # ==================================================
    # REATIVIDADE
    # ==================================================
    def _on_translate(self, *_):
        self.btn_lancamento.setText(TranslatorApp.get("Lançamento"))
        self.btn_transferencia.setText(TranslatorApp.get("Transferência"))
        self.btn_editar.setText(TranslatorApp.get("Editar"))
        self.btn_excluir.setText(TranslatorApp.get("Excluir"))
        self.btn_importar.setText(TranslatorApp.get("Importar"))
        self.btn_exportar.setText(TranslatorApp.get("Exportar"))

        self.lbl_periodo.setText(TranslatorApp.get("Período"))
        self.lbl_buscar.setText(TranslatorApp.get("Buscar"))

        self.input_busca.setPlaceholderText(
            TranslatorApp.get("Buscar descrição ou favorecido")
        )

        self._atualizar_filtros()
        self._update_progress_text()

        TranslatorApp.table_headers(
            self.table,
            [
                "Data",
                "Número",
                "Descrição",
                "Favorecido",
                "Categoria",
                "Receita",
                "Despesa",
                "Saldo",
            ],
        )

        self._aplicar()

    def _update_progress_text(self):
        self.progress_bar.setLabelText(
            TranslatorApp.get("Importando extrato")
        )
        self.progress_bar.setCancelButtonText(
            TranslatorApp.get("Cancelar")
        )

    def _atualizar_filtros(self):
        atual = self.combo_filtro.currentData()

        self.combo_filtro.blockSignals(True)
        self.combo_filtro.clear()

        for key, label in self.FILTROS:
            self.combo_filtro.addItem(
                TranslatorApp.get(label),
                key
            )

        index = self.combo_filtro.findData(atual)
        if index >= 0:
            self.combo_filtro.setCurrentIndex(index)

        self.combo_filtro.blockSignals(False)

    # ==================================================
    # UI
    # ==================================================
    def _montar_ui(self):
        layout = QVBoxLayout(self)

        # TOOLBAR
        toolbar = QHBoxLayout()

        def btn(texto, icon, fn):
            b = QToolButton()
            b.setText(TranslatorApp.get(texto))
            b.setIcon(self._icon(icon))
            b.setIconSize(QSize(18, 18))
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            b.clicked.connect(fn)
            return b

        self.btn_lancamento = btn(
            "Lançamento",
            "add",
            self.add_transaction
        )

        self.btn_transferencia = btn(
            "Transferência",
            "transfer",
            self.transfer_transaction
        )

        self.btn_editar = btn(
            "Editar",
            "edit",
            self.edit_transaction
        )

        self.btn_excluir = btn(
            "Excluir",
            "delete",
            self.delete_transaction
        )

        self.btn_importar = btn(
            "Importar",
            "import",
            self.importar_extrato
        )

        self.btn_exportar = btn(
            "Exportar",
            "export",
            self.exportar_extrato
        )

        toolbar.addWidget(self.btn_lancamento)
        toolbar.addWidget(self.btn_transferencia)
        toolbar.addWidget(self.btn_editar)
        toolbar.addWidget(self.btn_excluir)
        toolbar.addWidget(self.btn_importar)
        toolbar.addWidget(self.btn_exportar)

        toolbar.addStretch()

        self.combo_filtro = QComboBox()
        for key, label in self.FILTROS:
            self.combo_filtro.addItem(TranslatorApp.get(label), key)

        self.combo_filtro.currentIndexChanged.connect(
            self.carregar_historico
        )

        self.lbl_periodo = QLabel(TranslatorApp.get("Período"))
        toolbar.addWidget(self.lbl_periodo)
        toolbar.addWidget(self.combo_filtro)

        layout.addLayout(toolbar)

        # BUSCA
        busca_layout = QHBoxLayout()

        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText(
            TranslatorApp.get("Buscar descrição ou favorecido")
        )
        self.input_busca.textChanged.connect(self._filtrar)

        self.lbl_buscar = QLabel(TranslatorApp.get("Buscar"))
        busca_layout.addWidget(self.lbl_buscar)
        busca_layout.addWidget(self.input_busca)

        layout.addLayout(busca_layout)

        # TABELA
        self.table = QTableWidget(0, 8)

        TranslatorApp.table_headers(
            self.table,
            [
                "Data",
                "Número",
                "Descrição",
                "Favorecido",
                "Categoria",
                "Receita",
                "Despesa",
                "Saldo",
            ],
        )

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        # PAGINAÇÃO
        pag = QHBoxLayout()

        self.btn_prev = QToolButton()
        self.btn_prev.setText("◀")
        self.btn_prev.clicked.connect(self._prev)

        self.lbl_page = QLabel()

        self.btn_next = QToolButton()
        self.btn_next.setText("▶")
        self.btn_next.clicked.connect(self._next)

        pag.addStretch()
        pag.addWidget(self.btn_prev)
        pag.addWidget(self.lbl_page)
        pag.addWidget(self.btn_next)

        layout.addLayout(pag)

        # RESUMO
        self.resumo = QLabel()
        layout.addWidget(self.resumo)

    def _icon(self, nome):
        if nome in self._icon_cache:
            return self._icon_cache[nome]

        path = IonPath.resource("assets", "icons", f"{nome}.svg")
        icon = QIcon(path) if os.path.exists(path) else QIcon()

        self._icon_cache[nome] = icon
        return icon

    # ==================================================
    # CONTA
    # ==================================================
    def set_conta(self, conta):
        self.conta = conta
        self.carregar_historico()

    # ==================================================
    # HISTÓRICO
    # ==================================================
    def carregar_historico(self):
        if not self.conta:
            return

        inicio, fim = self._obter_periodo()

        transacoes = (
            self.transaction_controller
            .get_transactions_by_account_periodo(
                self.conta["ID_Conta"],
                (inicio, fim)
            )
        )

        self.dados_completos = transacoes or []
        self.pagina_atual = 0

        self._aplicar()

    def _obter_periodo(self):
        hoje = datetime.today()
        filtro = self.combo_filtro.currentData()

        if filtro == "MES":
            inicio = datetime(hoje.year, hoje.month, 1)

        elif filtro == "3M":
            mes = max(1, hoje.month - 2)
            inicio = datetime(hoje.year, mes, 1)

        elif filtro == "ANO":
            inicio = datetime(hoje.year, 1, 1)

        else:
            inicio = datetime(2000, 1, 1)

        return inicio.strftime("%Y-%m-%d"), hoje.strftime("%Y-%m-%d")

    # ==================================================
    # FILTRO
    # ==================================================
    def _filtrar(self):
        self.texto_busca = self.input_busca.text().lower()
        self.pagina_atual = 0
        self._aplicar()

    def _aplicar(self):
        dados = self.dados_completos

        if self.texto_busca:
            dados = [
                t for t in dados
                if (
                    self.texto_busca
                    in str(t.get("Descricao", "")).lower()
                    or self.texto_busca
                    in str(t.get("Favorecido", "")).lower()
                )
            ]

        inicio = self.pagina_atual * self.itens_por_pagina
        fim = inicio + self.itens_por_pagina
        pagina = dados[inicio:fim]

        total_paginas = max(
            1,
            (len(dados) + self.itens_por_pagina - 1)
            // self.itens_por_pagina
        )

        self.lbl_page.setText(
            f"{TranslatorApp.get('Página')} "
            f"{self.pagina_atual + 1} / {total_paginas}"
        )

        self._preencher(pagina)

    def _next(self):
        if (
            (self.pagina_atual + 1) * self.itens_por_pagina
            < len(self.dados_completos)
        ):
            self.pagina_atual += 1
            self._aplicar()

    def _prev(self):
        if self.pagina_atual > 0:
            self.pagina_atual -= 1
            self._aplicar()

    # ==================================================
    # TABELA
    # ==================================================
    def _preencher(self, dados):
        self.table.setRowCount(0)

        saldo = 0.0
        receitas = 0.0
        despesas = 0.0

        cor_receita = ThemeManager.get_color("success")
        cor_despesa = ThemeManager.get_color("danger")

        for t in dados:
            r = self.table.rowCount()
            self.table.insertRow(r)

            self.table.setItem(
                r,
                0,
                QTableWidgetItem(
                    DateFormatter.iso_to_br(t.get("Data", ""))
                )
            )

            self.table.setItem(
                r,
                1,
                QTableWidgetItem(str(t.get("ID_Transacao", "")))
            )

            self.table.setItem(
                r,
                2,
                QTableWidgetItem(t.get("Descricao", ""))
            )

            self.table.setItem(
                r,
                3,
                QTableWidgetItem(str(t.get("Favorecido", "")))
            )

            self.table.setItem(
                r,
                4,
                QTableWidgetItem(str(t.get("Categoria", "")))
            )

            valor = float(t.get("Valor", 0))

            if valor > 0:
                receitas += valor

                item = QTableWidgetItem(
                    CurrencyFormatter.format(valor)
                )
                item.setForeground(QColor(cor_receita))

                self.table.setItem(r, 5, item)
                self.table.setItem(r, 6, QTableWidgetItem(""))

            else:
                despesas += abs(valor)

                self.table.setItem(r, 5, QTableWidgetItem(""))

                item = QTableWidgetItem(
                    CurrencyFormatter.format(abs(valor))
                )
                item.setForeground(QColor(cor_despesa))

                self.table.setItem(r, 6, item)

            saldo += valor

            saldo_item = QTableWidgetItem(
                CurrencyFormatter.format(saldo)
            )
            saldo_item.setFont(QFont("", weight=QFont.Bold))

            self.table.setItem(r, 7, saldo_item)

            self.resumo.setText(
                f"{TranslatorApp.get('Créditos do período')}: "
                f"{CurrencyFormatter.format(receitas)} | "
                f"{TranslatorApp.get('Débitos do período')}: "
                f"{CurrencyFormatter.format(despesas)} | "
                f"{TranslatorApp.get('Resultado do período')}: "
                f"{CurrencyFormatter.format(saldo)}"
               )

    # ==================================================
    # AÇÕES
    # ==================================================
    def add_transaction(self):
        if not self.conta:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Nenhuma conta selecionada")
            )
            return

        dlg = TransactionDialogConta(
            parent=self,
            id_conta=self.conta.get("ID_Conta")
        )

        if dlg.exec_():
            self.carregar_historico()

    def transfer_transaction(self):
        dlg = TransferDialog(self)

        if dlg.exec_():
            self.carregar_historico()

    def edit_transaction(self):
        row = self.table.currentRow()

        if row < 0:
            return

        id_transacao = int(
            self.table.item(row, 1).text()
        )

        transacao = (
            self.transaction_controller
            .get_transaction_by_id(id_transacao)
        )

        dlg = EditTransactionDialog(
            transacao,
            self
        )

        if dlg.exec_():
            self.carregar_historico()

    def delete_transaction(self):
        row = self.table.currentRow()

        if row < 0:
            return

        id_transacao = int(
            self.table.item(row, 1).text()
        )

        confirm = QMessageBox.question(
            self,
            TranslatorApp.get("Excluir"),
            TranslatorApp.get(
                "Deseja realmente excluir esta transação"
            ),
            QMessageBox.Yes | QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            self.transaction_controller.delete_transaction(
                id_transacao
            )
            self.carregar_historico()

    # ==================================================
    # IMPORTAÇÃO
    # ==================================================
    def importar_extrato(self):
        if not self.conta:
            return

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            TranslatorApp.get("Selecionar extrato"),
            "",
            "CSV (*.csv);;Excel (*.xlsx);;PDF (*.pdf)",
        )

        if not arquivo:
            return

        try:
            self.progress_bar.setValue(0)
            self.progress_bar.show()

            self.ia_import_controller.importar_arquivo(
                caminho_arquivo=arquivo,
                id_conta=self.conta["ID_Conta"],
                progress_callback=self._mostrar_progresso_importacao,
            )

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("Importação concluída"),
            )

            self.carregar_historico()

        except Exception as e:
            logger.exception("Erro ao importar")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    # ==================================================
    # EXPORTAÇÃO
    # ==================================================
    def exportar_extrato(self):
        if not self.conta:
            return

        formato, ok = QInputDialog.getItem(
            self,
            TranslatorApp.get("Exportar"),
            TranslatorApp.get("Formato"),
            ["CSV", "XLSX", "PDF"],
            0,
            False,
        )

        if not ok:
            return

        arquivo, _ = QFileDialog.getSaveFileName(
            self,
            TranslatorApp.get("Salvar extrato"),
            "",
            f"{formato} (*.{formato.lower()})",
        )

        if not arquivo:
            return

        try:
            inicio, fim = self._obter_periodo()

            transacoes = (
                self.transaction_controller
                .get_transactions_by_account_periodo(
                    self.conta["ID_Conta"],
                    (inicio, fim)
                )
            )

            self.ia_export_controller.exportar_extrato_conta(
                transacoes=transacoes,
                conta=self.conta,
                data_inicio=inicio,
                data_fim=fim,
                formato=formato,
                caminho=arquivo,
            )

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("Exportação concluída"),
            )

        except Exception as e:
            logger.exception("Erro ao exportar")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    # ==================================================
    # PROGRESSO
    # ==================================================
    def _mostrar_progresso_importacao(self, progresso, mensagem=None):
        self.progress_bar.setValue(progresso)

        if mensagem:
            self.progress_bar.setLabelText(mensagem)

        if progresso >= 100:
            self.progress_bar.close()

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
