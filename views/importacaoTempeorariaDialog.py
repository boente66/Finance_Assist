# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QAbstractItemView,
    QCheckBox,
    QHeaderView,
    QLabel,
    QFrame,
)
from PyQt5.QtCore import Qt

from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter

from views.editar_transacao_dialog import EditTransactionDialog
from controllers.category_controller import CategoryController

from core.translator_app import TranslatorApp
from services.reconciliacao_importacao_service import (
    ReconciliacaoImportacaoService,
)

logger = logging.getLogger(__name__)


class ImportacaoTemporariaDialog(QDialog):
    """
    Tela de revisão dos lançamentos reconhecidos.

    Responsabilidade:
    - Exibir lançamentos temporários reconhecidos pela importação.
    - Permitir revisar/editar antes de salvar.
    - Retornar apenas os lançamentos selecionados.
    - NÃO grava diretamente no banco.
    """

    COL_IMPORTAR = 0
    COL_STATUS = 1
    COL_DATA = 2
    COL_DESCRICAO = 3
    COL_CATEGORIA = 4
    COL_CONFIANCA = 5
    COL_VALOR = 6
    COL_TIPO = 7
    COL_CORRESPONDENCIA = 8

    def __init__(self, lancamentos, parent=None, tipo_destino="conta"):
        super().__init__(parent)

        self.lancamentos = lancamentos or []
        self.tipo_destino = tipo_destino
        self.category_controller = CategoryController()
        self._categoria_cache = {}

        self.setWindowTitle("Revisar Lançamentos Importados")
        self.resize(1000, 500)

        self._init_ui()
        self._connect_events()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self._popular_tabela()

    # ======================================================
    # UI
    # ======================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("card")
        summary_layout = QHBoxLayout(self.summary_card)
        self.lbl_novos = QLabel()
        self.lbl_novos.setObjectName("positivo")
        self.lbl_duplicados = QLabel()
        self.lbl_duplicados.setObjectName("muted")
        self.lbl_possiveis = QLabel()
        self.lbl_possiveis.setObjectName("warning")
        self.lbl_selecionados = QLabel()
        self.lbl_selecionados.setObjectName("cardValue")
        for label in (
            self.lbl_novos, self.lbl_duplicados,
            self.lbl_possiveis, self.lbl_selecionados,
        ):
            summary_layout.addWidget(label)
        layout.addWidget(self.summary_card)

        self.table = QTableWidget(0, 9)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)

        btns = QHBoxLayout()

        self.btn_editar = QPushButton()
        self.btn_confirmar = QPushButton()
        self.btn_cancelar = QPushButton()

        self.btn_confirmar.setObjectName("addButton")

        btns.addWidget(self.btn_editar)
        btns.addStretch()
        btns.addWidget(self.btn_confirmar)
        btns.addWidget(self.btn_cancelar)

        layout.addLayout(btns)

    # ======================================================
    # EVENTOS
    # ======================================================
    def _connect_events(self):
        self.btn_editar.clicked.connect(self.editar_selecionado)
        self.btn_confirmar.clicked.connect(self.confirmar)
        self.btn_cancelar.clicked.connect(self.reject)

    # ======================================================
    # TRADUÇÃO
    # ======================================================
    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Revisar Lançamentos Importados")
        )

        self.btn_editar.setText(
            TranslatorApp.get("Editar selecionado")
        )

        self.btn_confirmar.setText(
            TranslatorApp.get("Confirmar importação")
        )

        self.btn_cancelar.setText(
            TranslatorApp.get("Cancelar")
        )

        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("Importar"),
            TranslatorApp.get("Status"),
            TranslatorApp.get("Data"),
            TranslatorApp.get("Descrição"),
            TranslatorApp.get("Categoria"),
            TranslatorApp.get("Confiança"),
            TranslatorApp.get("Valor"),
            TranslatorApp.get("Tipo"),
            TranslatorApp.get("Correspondência encontrada"),
        ])
        for row, item in enumerate(self.lancamentos):
            status_item = self.table.item(row, self.COL_STATUS)
            if status_item:
                status_item.setText(self._texto_status(
                    item.get(
                        "StatusImportacao",
                        ReconciliacaoImportacaoService.NOVO,
                    )
                ))
        self._atualizar_resumo()

    # ======================================================
    # POPULAR TABELA
    # ======================================================
    def _popular_tabela(self):
        self.table.setRowCount(0)

        for row, lanc in enumerate(self.lancamentos):
            self.table.insertRow(row)

            chk = QCheckBox()
            chk.setChecked(bool(lanc.get("Importar", True)))
            if lanc.get("StatusImportacao") == ReconciliacaoImportacaoService.DUPLICADO:
                chk.setEnabled(False)
            chk.stateChanged.connect(self._atualizar_resumo)

            self.table.setCellWidget(
                row,
                self.COL_IMPORTAR,
                chk
            )

            status = lanc.get(
                "StatusImportacao", ReconciliacaoImportacaoService.NOVO
            )
            status_item = self._set_item(
                row, self.COL_STATUS, self._texto_status(status)
            )
            status_item.setToolTip(str(lanc.get("MotivoReconciliacao", "")))

            self._set_item(
                row,
                self.COL_DATA,
                self._formatar_data(lanc.get("Data", ""))
            )

            self._set_item(
                row,
                self.COL_DESCRICAO,
                str(lanc.get("Descricao", ""))
            )

            self._set_item(
                row,
                self.COL_CATEGORIA,
                self._get_nome_categoria(
                    lanc.get("ID_Categoria")
                )
            )

            confianca = float(
                lanc.get("ConfiancaIA", 0) or 0
            )

            self._set_item(
                row,
                self.COL_CONFIANCA,
                f"{confianca * 100:.0f}%"
            )

            valor = float(
                lanc.get("Valor", 0) or 0
            )

            self._set_item(
                row,
                self.COL_VALOR,
                CurrencyFormatter.format(valor)
            )

            self._set_item(
                row,
                self.COL_TIPO,
                str(lanc.get("Tipo", ""))
            )

            correspondencia = self._set_item(
                row,
                self.COL_CORRESPONDENCIA,
                str(lanc.get("CorrespondenciaImportacao", "")),
            )
            correspondencia.setToolTip(
                str(lanc.get("MotivoReconciliacao", ""))
            )

        self._atualizar_resumo()

    def _set_item(self, row, column, value):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, column, item)
        return item

    def _texto_status(self, status):
        textos = {
            ReconciliacaoImportacaoService.NOVO: "Novo",
            ReconciliacaoImportacaoService.DUPLICADO: "Duplicado",
            ReconciliacaoImportacaoService.POSSIVEL_DUPLICADO: "Possível duplicado",
        }
        return TranslatorApp.get(textos.get(status, str(status)))

    def _atualizar_resumo(self, *_):
        contagens = {
            ReconciliacaoImportacaoService.NOVO: 0,
            ReconciliacaoImportacaoService.DUPLICADO: 0,
            ReconciliacaoImportacaoService.POSSIVEL_DUPLICADO: 0,
        }
        selecionados = 0
        for row, item in enumerate(self.lancamentos):
            status = item.get(
                "StatusImportacao", ReconciliacaoImportacaoService.NOVO
            )
            contagens[status] = contagens.get(status, 0) + 1
            checkbox = self.table.cellWidget(row, self.COL_IMPORTAR)
            if checkbox and checkbox.isChecked():
                selecionados += 1
        self.lbl_novos.setText(
            f"{TranslatorApp.get('Novos')}: {contagens[ReconciliacaoImportacaoService.NOVO]}"
        )
        self.lbl_duplicados.setText(
            f"{TranslatorApp.get('Duplicados')}: {contagens[ReconciliacaoImportacaoService.DUPLICADO]}"
        )
        self.lbl_possiveis.setText(
            f"{TranslatorApp.get('Possíveis')}: {contagens[ReconciliacaoImportacaoService.POSSIVEL_DUPLICADO]}"
        )
        self.lbl_selecionados.setText(
            f"{TranslatorApp.get('Selecionados')}: {selecionados}"
        )
        self.btn_confirmar.setText(
            f"{TranslatorApp.get('Confirmar importação')} ({selecionados})"
        )

    # ======================================================
    # FORMATADORES
    # ======================================================
    def _formatar_data(self, data_iso):
        if not data_iso:
            return ""

        try:
            return DateFormatter.iso_to_br(data_iso)
        except Exception:
            return str(data_iso)

    # ======================================================
    # CACHE DE CATEGORIA
    # ======================================================
    def _get_nome_categoria(self, id_categoria):
        if not id_categoria:
            return ""

        if id_categoria in self._categoria_cache:
            return self._categoria_cache[id_categoria]

        try:
            nome = self.category_controller.get_nome_categoria_by_id(
                id_categoria
            ) or ""

        except Exception:
            logger.exception("Erro ao buscar nome da categoria")
            nome = ""

        self._categoria_cache[id_categoria] = nome
        return nome

    # ======================================================
    # EDITAR
    # ======================================================
    def editar_selecionado(self):
        row = self.table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Selecione um lançamento.")
            )
            return

        if row >= len(self.lancamentos):
            return

        lanc = self.lancamentos[row]

        dialog = EditTransactionDialog(
            transacao=lanc,
            parent=self,
            modo_temporario=True
        )

        if dialog.exec_() == QDialog.Accepted:
            dados = getattr(dialog, "dados_editados", None)

            if not dados:
                return

            self.lancamentos[row].update(dados)
            self._atualizar_linha(row)

    def _atualizar_linha(self, row):
        if row < 0 or row >= len(self.lancamentos):
            return

        lanc = self.lancamentos[row]

        self._set_item(
            row,
            self.COL_DATA,
            self._formatar_data(lanc.get("Data", ""))
        )

        self._set_item(
            row,
            self.COL_DESCRICAO,
            lanc.get("Descricao", "")
        )

        self._set_item(
            row,
            self.COL_CATEGORIA,
            self._get_nome_categoria(
                lanc.get("ID_Categoria")
            )
        )

        self._set_item(
            row,
            self.COL_VALOR,
            CurrencyFormatter.format(
                float(lanc.get("Valor", 0) or 0)
            )
        )

        self._set_item(
            row,
            self.COL_TIPO,
            lanc.get("Tipo", "")
        )
        self._atualizar_resumo()

    # ======================================================
    # CONFIRMAR
    # ======================================================
    def confirmar(self):
        selecionados = []

        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(
                row,
                self.COL_IMPORTAR
            )

            if chk and chk.isChecked():
                item = dict(self.lancamentos[row])
                status = item.get("StatusImportacao")
                if status == ReconciliacaoImportacaoService.DUPLICADO:
                    continue
                if status == ReconciliacaoImportacaoService.POSSIVEL_DUPLICADO:
                    item["_ConfirmadoPossivel"] = True
                selecionados.append(item)

        if not selecionados:
            if self.lancamentos and all(
                item.get("StatusImportacao")
                == ReconciliacaoImportacaoService.DUPLICADO
                for item in self.lancamentos
            ):
                self.lancamentos = []
                self.accept()
                return
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Nenhum lançamento selecionado.")
            )
            return

        self.lancamentos = selecionados
        self.accept()

    # ======================================================
    # GET
    # ======================================================
    def get_lancamentos_confirmados(self):
        return self.lancamentos

    # ======================================================
    # CICLO DE VIDA
    # ======================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
