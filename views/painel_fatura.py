# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QDialog,
    QToolButton, QMessageBox, QPushButton, QInputDialog,
    QFrame, QProgressBar, QMenu, QApplication, QLineEdit
)
from PyQt5.QtGui import QColor, QIcon, QFont
from PyQt5.QtCore import Qt, QSize

from controllers.fatura_controller import FaturaController
from controllers.account_controller import AccountController

from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from core.session import Session

from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter
from utilitarios.ion_path import IonPath

from views.fatura_dialog import FaturaDialog
from views.editar_fatura_dialog import EditarFaturaDialog
from views.responsive_layout import FlowLayout

logger = logging.getLogger(__name__)


class PainelFatura(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = FaturaController()
        self.account_controller = AccountController()

        self.cartao = None
        self.page = 0
        self.limit = 50
        self.filtro_status = "Todos"
        self._icon_cache = {}
        self._updating = False

        hoje = datetime.today()
        self.mes_atual = hoje.month
        self.ano_atual = hoje.year

        self._init_ui()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        Session.on_idioma_change(self._on_idioma_changed)

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    def _atualizar_textos(self):
        self.setWindowTitle(TranslatorApp.get("Fatura"))

        self.btn_lancar.setText(TranslatorApp.get("+ Lançar"))
        self.btn_pagar.setText(TranslatorApp.get("Pagar"))
        self.btn_exportar.setText(TranslatorApp.get("PDF"))
        self.btn_importar.setText(TranslatorApp.get("Importar fatura"))

        self.lbl_status.setText(TranslatorApp.get("Status:"))
        self.lbl_mes.setText(TranslatorApp.get("Mês:"))
        self.lbl_ano.setText(TranslatorApp.get("Ano:"))

        self.filtro_combo.setItemText(0, TranslatorApp.get("Todos"))
        self.filtro_combo.setItemText(1, TranslatorApp.get("Abertos"))
        self.filtro_combo.setItemText(2, TranslatorApp.get("Pagos"))

        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("Data"),
            TranslatorApp.get("Descrição"),
            TranslatorApp.get("Categoria"),
            TranslatorApp.get("Valor"),
            TranslatorApp.get("Status"),
        ])

    # ======================================================
    # EVENTOS SEGUROS
    # ======================================================
    def _on_idioma_changed(self, *_):
        if self._updating:
            return

        self._updating = True

        try:
            self._atualizar_textos()
            self._recarregar_meses()

            if self.cartao:
                self._carregar()

        finally:
            self._updating = False

    # ======================================================
    # ÍCONES
    # ======================================================
    def _icon(self, nome):
        if nome in self._icon_cache:
            return self._icon_cache[nome]

        path = IonPath.resource("assets", "icons", f"{nome}.svg")
        icon = QIcon(path) if os.path.exists(path) else QIcon()

        self._icon_cache[nome] = icon
        return icon

    # ======================================================
    # UI
    # ======================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(7)

        self.nome_cartao_label = QLabel("-")
        self.nome_cartao_label.setObjectName("pageTitle")

        self.info_label = QLabel("")
        self.info_label.setObjectName("muted")

        layout.addWidget(self.nome_cartao_label)

        self.indicators_layout = QGridLayout()
        self.indicators_layout.setSpacing(10)
        self.indicator_labels = {}
        self.indicator_widgets = []
        for index, key in enumerate(("limite", "saldo_devedor", "disponivel")):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            caption = QLabel()
            caption.setObjectName("cardTitle")
            value = QLabel()
            value.setObjectName("cardValue")
            card_layout.addWidget(caption)
            card_layout.addWidget(value)
            self.indicators_layout.addWidget(card, 0, index)
            self.indicator_widgets.append(card)
            self.indicator_labels[key] = (caption, value)
        layout.addLayout(self.indicators_layout)
        self.info_label.hide()

        # TOOLBAR
        self.toolbar = FlowLayout(horizontal_spacing=8, vertical_spacing=8)

        def btn(texto, fn):
            b = QToolButton()
            b.setText(texto)
            b.clicked.connect(fn)
            return b

        self.btn_lancar = btn("+ Lançar", self.add_transaction)
        self.btn_lancar.setIcon(self._icon("add"))

        self.btn_pagar = btn("Pagar", self.pagar_fatura)
        self.btn_pagar.setIcon(self._icon("pay"))

        self.btn_exportar = btn("PDF", self.exportar_pdf)
        self.btn_exportar.setIcon(self._icon("pdf"))
        self.btn_importar = btn("Importar fatura", self.importar_fatura)
        self.btn_importar.setIcon(self._icon("import"))
        self.btn_pagar.setObjectName("secondaryButton")
        self.btn_exportar.setObjectName("secondaryButton")

        self.toolbar.addWidget(self.btn_lancar)
        self.toolbar.addWidget(self.btn_pagar)
        self.toolbar.addWidget(self.btn_exportar)
        self.toolbar.addWidget(self.btn_importar)

        self.filtro_combo = QComboBox()
        self.filtro_combo.addItem("Todos", "Todos")
        self.filtro_combo.addItem("Abertos", "Abertos")
        self.filtro_combo.addItem("Pagos", "Pagos")
        self.filtro_combo.currentIndexChanged.connect(self._on_filtro_changed)

        self.lbl_status = QLabel("Status:")
        self.toolbar.addWidget(self.lbl_status)
        self.toolbar.addWidget(self.filtro_combo)

        layout.addLayout(self.toolbar)

        # FILTROS
        self.filters_layout = FlowLayout(horizontal_spacing=8, vertical_spacing=8)

        self.mes_combo = QComboBox()

        for i in range(1, 13):
            self.mes_combo.addItem(DateFormatter.map_nome_mes(i), i)

        self.mes_combo.setCurrentIndex(self.mes_atual - 1)
        self.mes_combo.currentIndexChanged.connect(self._reset_paginacao)

        self.ano_combo = QComboBox()
        self.ano_combo.addItems([
            str(self.ano_atual - 1),
            str(self.ano_atual),
            str(self.ano_atual + 1)
        ])
        self.ano_combo.setCurrentText(str(self.ano_atual))
        self.ano_combo.currentIndexChanged.connect(self._reset_paginacao)

        self.lbl_mes = QLabel("Mês:")
        self.lbl_ano = QLabel("Ano:")

        self.filters_layout.addWidget(self.lbl_mes)
        self.filters_layout.addWidget(self.mes_combo)
        self.filters_layout.addWidget(self.lbl_ano)
        self.filters_layout.addWidget(self.ano_combo)

        layout.addLayout(self.filters_layout)

        self.import_progress = QProgressBar()
        self.import_progress.setObjectName("importProgress")
        self.import_progress.hide()
        layout.addWidget(self.import_progress)

        # TABELA
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Data", "Descrição", "Categoria", "Valor", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._abrir_menu_acoes)
        self.table.cellDoubleClicked.connect(lambda *_: self.editar_lancamento())
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table)

        # PAGINAÇÃO
        paginacao = QHBoxLayout()

        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        for button, tip in ((self.btn_prev, "Página anterior"), (self.btn_next, "Próxima página")):
            button.setObjectName("circularNavButton")
            button.setFixedSize(38, 38)
            button.setToolTip(TranslatorApp.get(tip))
        self.label_page = QLabel()

        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)

        paginacao.addStretch()
        paginacao.addWidget(self.btn_prev)
        paginacao.addWidget(self.label_page)
        paginacao.addWidget(self.btn_next)
        paginacao.addStretch()

        layout.addLayout(paginacao)

        self.resumo_label = QLabel()
        self.resumo_label.setObjectName("cardValue")
        self.resumo_label.setWordWrap(True)
        layout.addWidget(self.resumo_label)

        self.futuras_label = QLabel()
        self.futuras_label.setObjectName("muted")
        self.futuras_label.setWordWrap(True)
        layout.addWidget(self.futuras_label)
        self.set_compact_mode(False, self.width())

    def set_compact_mode(self, compact, available_width=None):
        width = int(available_width or self.width())
        columns = 3 if width >= 680 else 2 if width >= 460 else 1
        for widget in self.indicator_widgets:
            self.indicators_layout.removeWidget(widget)
        for index, widget in enumerate(self.indicator_widgets):
            self.indicators_layout.addWidget(widget, index // columns, index % columns)
        for column in range(3):
            self.indicators_layout.setColumnStretch(column, 1 if column < columns else 0)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        if width >= 760:
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
        font_size = 9 if width < 760 else 10
        self.table.setFont(QFont(self.font().family(), font_size))
        self.table.verticalHeader().setDefaultSectionSize(28 if width < 760 else 34)
        for button in (self.btn_lancar, self.btn_pagar, self.btn_exportar,
                       self.btn_importar):
            button.setIconSize(QSize(15, 15) if width < 760 else QSize(18, 18))
            button.setToolButtonStyle(
                Qt.ToolButtonIconOnly if width < 600 else Qt.ToolButtonTextBesideIcon
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "indicator_widgets"):
            self.set_compact_mode(event.size().width() < 850, event.size().width())

    # ======================================================
    # MESES
    # ======================================================
    def _recarregar_meses(self):
        mes_atual = self.mes_combo.currentData()

        self.mes_combo.blockSignals(True)
        self.mes_combo.clear()

        for i in range(1, 13):
            self.mes_combo.addItem(DateFormatter.map_nome_mes(i), i)

        index = self.mes_combo.findData(mes_atual)

        if index >= 0:
            self.mes_combo.setCurrentIndex(index)

        self.mes_combo.blockSignals(False)

    # ======================================================
    # CONTROLE
    # ======================================================
    def set_cartao(self, cartao):
        self.cartao = cartao
        self.page = 0
        self._carregar()

    def set_competencia(self, mes, ano):
        """Seleciona a competência sem depender da ordem de set_cartao."""
        self.mes_combo.setCurrentIndex(max(0, min(11, int(mes) - 1)))
        texto_ano = str(int(ano))
        if self.ano_combo.findText(texto_ano) < 0:
            self.ano_combo.addItem(texto_ano)
        self.ano_combo.setCurrentText(texto_ano)
        self.page = 0

    def _reset_paginacao(self):
        self.page = 0
        self._carregar()

    def _on_filtro_changed(self):
        self.filtro_status = self.filtro_combo.currentData()
        self._reset_paginacao()

    def _next_page(self):
        if self.table.rowCount() == self.limit:
            self.page += 1
            self._carregar()

    def _prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._carregar()

    # ======================================================
    # CARREGAR
    # ======================================================
    def _carregar(self):
        if not self.cartao or self._updating:
            return

        mes = int(self.mes_combo.currentData())
        ano = int(self.ano_combo.currentText())

        painel = self.controller.get_painel_cartao(
            id_cartao=self.cartao["ID_Cartao"],
            mes=mes,
            ano=ano,
            page=self.page,
            limit=self.limit,
            status=self.filtro_status
        ) or {}

        self._render_header(painel.get("resumo", {}), mes, ano)
        self._render_tabela(painel.get("lancamentos", []))
        self._render_resumo(painel.get("fatura", {}))
        self._render_futuras(painel.get("futuras", {}))

        total = painel.get("total_registros", 0)
        total_paginas = max(1, (total + self.limit - 1) // self.limit)

        self.label_page.setText(f"{self.page + 1} / {total_paginas}")

    # ======================================================
    # RENDER
    # ======================================================
    def _render_header(self, resumo, mes, ano):
        nome_mes = DateFormatter.map_nome_mes(mes)

        self.nome_cartao_label.setText(
            f"{self.cartao.get('Nome', '')} - {nome_mes} {ano}"
        )

        self.info_label.setText(
            f"{TranslatorApp.get('Limite')}: "
            f"{CurrencyFormatter.format(resumo.get('limite', 0))} | "
            f"{TranslatorApp.get('Usado')}: "
            f"{CurrencyFormatter.format(resumo.get('saldo_devedor', 0))} | "
            f"{TranslatorApp.get('Disponível')}: "
            f"{CurrencyFormatter.format(resumo.get('disponivel', 0))}"
        )
        captions = {
            "limite": "Limite", "saldo_devedor": "Usado", "disponivel": "Disponível"
        }
        for key, (caption, value) in self.indicator_labels.items():
            caption.setText(TranslatorApp.get(captions[key]))
            value.setText(CurrencyFormatter.format(resumo.get(key, 0)))
        self.indicator_labels["saldo_devedor"][1].setObjectName("warning")
        self.indicator_labels["disponivel"][1].setObjectName("positivo")

    def _render_resumo(self, fatura):
        self.resumo_label.setText(
            f"{TranslatorApp.get('Fatura')}: "
            f"{CurrencyFormatter.format(fatura.get('total', 0))} | "
            f"{TranslatorApp.get('Abertos')}: "
            f"{CurrencyFormatter.format(fatura.get('abertos', 0))} | "
            f"{TranslatorApp.get('Pagos')}: "
            f"{CurrencyFormatter.format(fatura.get('pagos', 0))}"
        )

    def _render_futuras(self, futuras):
        texto = f"{TranslatorApp.get('Próximas faturas')}:\n"

        if not futuras:
            texto += TranslatorApp.get("Nenhuma")
        else:
            for mes, valor in futuras.items():
                texto += f"{mes} → {CurrencyFormatter.format(valor)}\n"

        self.futuras_label.setText(texto)

    def _render_tabela(self, dados):
        self.table.setRowCount(0)

        for item in dados:
            row = self.table.rowCount()
            self.table.insertRow(row)

            valor = float(item.get("Valor", 0))
            pago = item.get("Paga")

            cor = (
                ThemeManager.get_color("success")
                if pago else ThemeManager.get_color("danger")
            )

            status = (
                TranslatorApp.get("Pago")
                if pago else TranslatorApp.get("Aberto")
            )

            descricao = item.get("Descricao", "")

            if item.get("Parcela_Atual") and item.get("Num_Parcelas"):
                descricao += f" ({item['Parcela_Atual']}/{item['Num_Parcelas']})"

            data_item = QTableWidgetItem(
                DateFormatter.iso_to_br(item.get("Data", ""))
            )
            data_item.setData(Qt.UserRole, int(item["ID_Lancamento"]))
            self.table.setItem(
                row,
                0,
                data_item
            )

            self.table.setItem(row, 1, QTableWidgetItem(descricao))
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(str(item.get("Categoria", "")))
            )

            valor_item = QTableWidgetItem(CurrencyFormatter.format(valor))
            valor_item.setForeground(QColor(cor))
            self.table.setItem(row, 3, valor_item)

            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(cor))
            self.table.setItem(row, 4, status_item)

    # ======================================================
    # AÇÕES
    # ======================================================
    def _abrir_menu_acoes(self, pos=None):
        if pos is not None:
            item = self.table.itemAt(pos)
            if item:
                self.table.selectRow(item.row())
        menu = QMenu(self)
        copiar = menu.addAction(self._icon("copy"), TranslatorApp.get("Copiar"))
        colar = menu.addAction(self._icon("add"), TranslatorApp.get("Colar"))
        menu.addSeparator()
        editar = menu.addAction(self._icon("edit"), TranslatorApp.get("Editar"))
        excluir = menu.addAction(self._icon("delete"), TranslatorApp.get("Excluir"))
        copiar.setEnabled(self._id_selecionado() is not None)
        editar.setEnabled(self._id_selecionado() is not None)
        excluir.setEnabled(self._id_selecionado() is not None)
        colar.setEnabled(bool(QApplication.clipboard().text().strip()))
        global_pos = (
            self.table.viewport().mapToGlobal(pos)
            if pos is not None else self.table.mapToGlobal(self.table.rect().center())
        )
        escolhido = menu.exec_(global_pos)
        if escolhido is copiar:
            self.copiar_lancamento()
        elif escolhido is colar:
            self.colar_lancamento()
        elif escolhido is editar:
            self.editar_lancamento()
        elif escolhido is excluir:
            self.excluir_lancamento()

    def _id_selecionado(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def copiar_lancamento(self):
        identificador = self._id_selecionado()
        if identificador is None:
            return False
        item = self.controller.obter_lancamento(identificador)
        if not item:
            return False
        QApplication.clipboard().setText(json.dumps(dict(item), ensure_ascii=False))
        return True

    def colar_lancamento(self):
        if not self.cartao:
            return False
        try:
            item = json.loads(QApplication.clipboard().text())
            if not isinstance(item, dict) or not item.get("Descricao"):
                raise ValueError("A área de transferência não contém um lançamento de fatura.")
            for chave in ("ID_Lancamento", "ID_Usuario", "ID_Conta", "ID_Transacao", "Paga"):
                item.pop(chave, None)
            item["ID_Cartao"] = self.cartao["ID_Cartao"]
            item["Competencia_Mes"] = int(self.mes_combo.currentData())
            item["Competencia_Ano"] = int(self.ano_combo.currentText())
            item["Paga"] = 0
            self.controller.registrar_despesa_cartao(item)
            self._carregar()
            return True
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get("Não foi possível colar"), str(exc))
            return False

    def editar_lancamento(self):
        identificador = self._id_selecionado()
        if identificador is None:
            return False
        item = self.controller.obter_lancamento(identificador)
        if not item:
            return False
        dialog = EditarFaturaDialog(item, self)
        if dialog.exec_() == QDialog.Accepted:
            self._carregar()
            return True
        return False

    def excluir_lancamento(self):
        identificador = self._id_selecionado()
        if identificador is None:
            return False
        if QMessageBox.question(
            self, TranslatorApp.get("Excluir lançamento"),
            TranslatorApp.get("Deseja excluir este lançamento da fatura?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return False
        try:
            self.controller.excluir_lancamento(identificador)
            self._carregar()
            return True
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get("Não foi possível excluir"), str(exc))
            return False

    def add_transaction(self):
        if not self.cartao:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Nenhum cartão selecionado.")
            )
            return

        dialog = FaturaDialog(
            parent=self,
            id_cartao=self.cartao["ID_Cartao"]
        )

        if dialog.exec_() == QDialog.Accepted:
            self._carregar()

    def importar_fatura(self):
        if not self.cartao:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Nenhum cartão selecionado."),
            )
            return
        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            TranslatorApp.get("Selecionar fatura"),
            "",
            "Faturas PDF (*.pdf)",
        )
        if not arquivo:
            return
        try:
            senha_pdf = None
            from PyPDF2 import PdfReader
            if PdfReader(arquivo).is_encrypted:
                senha_pdf, ok = QInputDialog.getText(
                    self, TranslatorApp.get("Fatura protegida"),
                    TranslatorApp.get("Digite a senha do PDF:"),
                    QLineEdit.Password,
                )
                if not ok:
                    return
            from workers.import_worker import ImportWorker

            self.import_progress.setValue(0)
            self.import_progress.show()
            self.import_worker = ImportWorker(
                controller=self.controller,
                caminho_arquivo=arquivo,
                id_conta=self.cartao["ID_Cartao"],
                parent=self,
                tipo_destino="cartao",
                senha_pdf=senha_pdf,
            )
            self.import_worker.progress.connect(
                lambda valor, _texto: self.import_progress.setValue(valor)
            )
            self.import_worker.finished.connect(
                self._on_importacao_fatura_finalizada
            )
            self.import_worker.error.connect(self._on_importacao_fatura_erro)
            self.import_worker.start()
        except Exception as exc:
            self.import_progress.hide()
            logger.exception("Erro ao iniciar importação de fatura")
            QMessageBox.critical(self, TranslatorApp.get("Erro"), str(exc))

    def _on_importacao_fatura_finalizada(self, lancamentos):
        self.import_progress.hide()
        if not lancamentos:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Nenhum lançamento reconhecido no arquivo."),
            )
            return
        try:
            from views.importacaoTempeorariaDialog import ImportacaoTemporariaDialog

            dialog = ImportacaoTemporariaDialog(
                lancamentos=lancamentos,
                parent=self,
                tipo_destino="cartao",
            )
            if dialog.exec_() != QDialog.Accepted:
                return
            total = self.controller.salvar_lancamentos_importados(
                dialog.get_lancamentos_confirmados()
            )
            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                f"{total} {TranslatorApp.get('lançamento(s) salvo(s).')}",
            )
            self._carregar()
        except Exception as exc:
            logger.exception("Erro ao concluir importação de fatura")
            QMessageBox.critical(self, TranslatorApp.get("Erro"), str(exc))

    def _on_importacao_fatura_erro(self, mensagem):
        self.import_progress.hide()
        QMessageBox.critical(self, TranslatorApp.get("Erro"), mensagem)

    def pagar_fatura(self):
        if not self.cartao:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Nenhum cartão selecionado.")
            )
            return

        mes = int(self.mes_combo.currentData())
        ano = int(self.ano_combo.currentText())

        fatura = self.controller.obter_fatura_mes(
            self.cartao["ID_Cartao"],
            mes,
            ano
        )

        total = sum(
            float(l["Valor"])
            for l in fatura
            if not l.get("Paga")
        )

        if total <= 0:
            QMessageBox.information(
                self,
                TranslatorApp.get("Info"),
                TranslatorApp.get("Nenhum valor em aberto")
            )
            return

        contas = self.account_controller.get_all_accounts()

        if not contas:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Nenhuma conta disponível")
            )
            return

        nomes = [c["Nome_Conta"] for c in contas]

        nome, ok = QInputDialog.getItem(
            self,
            TranslatorApp.get("Pagar Fatura"),
            f"{TranslatorApp.get('Total')}: "
            f"{CurrencyFormatter.format(total)}\n"
            f"{TranslatorApp.get('Selecione a conta')}:",
            nomes,
            0,
            False
        )

        if not ok:
            return

        conta = next(c for c in contas if c["Nome_Conta"] == nome)

        confirm = QMessageBox.question(
            self,
            TranslatorApp.get("Confirmar"),
            f"{TranslatorApp.get('Pagar')} "
            f"{CurrencyFormatter.format(total)} "
            f"{TranslatorApp.get('de')} {nome}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            resultado = self.controller.pagar_fatura(
                self.cartao["ID_Cartao"],
                conta["ID_Conta"],
                mes,
                ano
            )

            if not resultado.get("sucesso"):
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Aviso"),
                    TranslatorApp.get(
                        resultado.get(
                            "mensagem",
                            "Não foi possível pagar a fatura."
                        )
                    )
                )
                return

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get(
                    resultado.get("mensagem", "Fatura paga")
                )
            )

            self._carregar()

        except Exception as e:
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    def exportar_pdf(self):
        if not self.cartao:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Nenhum cartão selecionado.")
            )
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            TranslatorApp.get("Salvar PDF"),
            "",
            "PDF (*.pdf)"
        )

        if not caminho:
            return

        mes = int(self.mes_combo.currentData())
        ano = int(self.ano_combo.currentText())

        dados = self.controller.listar_lancamentos_fatura(
            self.cartao["ID_Cartao"],
            mes,
            ano
        )

        try:
            self.controller.exportar_fatura_pdf(
                self.cartao,
                dados,
                caminho,
                mes,
                ano,
            )

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get("PDF exportado")
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    # ======================================================
    # CICLO DE VIDA
    # ======================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
