# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QDialog,
    QToolButton, QMessageBox, QPushButton, QInputDialog
)
from PyQt5.QtGui import QColor, QIcon

from controllers.fatura_controller import FaturaController
from controllers.account_controller import AccountController

from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from core.session import Session

from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter
from utilitarios.ion_path import IonPath

from views.fatura_dialog import FaturaDialog

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

        self.nome_cartao_label = QLabel("-")
        self.nome_cartao_label.setObjectName("pageTitle")

        self.info_label = QLabel("")
        self.info_label.setObjectName("muted")

        layout.addWidget(self.nome_cartao_label)
        layout.addWidget(self.info_label)

        # TOOLBAR
        toolbar = QHBoxLayout()

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

        toolbar.addWidget(self.btn_lancar)
        toolbar.addWidget(self.btn_pagar)
        toolbar.addWidget(self.btn_exportar)
        toolbar.addStretch()

        self.filtro_combo = QComboBox()
        self.filtro_combo.addItem("Todos", "Todos")
        self.filtro_combo.addItem("Abertos", "Abertos")
        self.filtro_combo.addItem("Pagos", "Pagos")
        self.filtro_combo.currentIndexChanged.connect(self._on_filtro_changed)

        self.lbl_status = QLabel("Status:")
        toolbar.addWidget(self.lbl_status)
        toolbar.addWidget(self.filtro_combo)

        layout.addLayout(toolbar)

        # FILTROS
        filtros = QHBoxLayout()

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

        filtros.addWidget(self.lbl_mes)
        filtros.addWidget(self.mes_combo)
        filtros.addWidget(self.lbl_ano)
        filtros.addWidget(self.ano_combo)

        layout.addLayout(filtros)

        # TABELA
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Data", "Descrição", "Categoria", "Valor", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        layout.addWidget(self.table)

        # PAGINAÇÃO
        paginacao = QHBoxLayout()

        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.label_page = QLabel()

        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)

        paginacao.addWidget(self.btn_prev)
        paginacao.addWidget(self.label_page)
        paginacao.addWidget(self.btn_next)

        layout.addLayout(paginacao)

        self.resumo_label = QLabel()
        layout.addWidget(self.resumo_label)

        self.futuras_label = QLabel()
        self.futuras_label.setObjectName("muted")
        layout.addWidget(self.futuras_label)

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

    def _reset_paginacao(self):
        self.page = 0
        self._carregar()

    def _on_filtro_changed(self):
        self.filtro_status = self.filtro_combo.currentData()
        self._reset_paginacao()

    def _next_page(self):
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

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(
                    DateFormatter.iso_to_br(item.get("Data", ""))
                )
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
                caminho
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
