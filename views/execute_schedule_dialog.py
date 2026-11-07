from core.regional_format import RegionalFormat
# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QMessageBox, QDateEdit, QDoubleSpinBox
)
from PyQt5.QtCore import QDate

from controllers.account_controller import AccountController
from controllers.category_controller import CategoryController
from controllers.favorecido_controller import FavorecidoController
from controllers.schedule_controller import ScheduleController

from core.translator_app import TranslatorApp
from utilitarios.currency_formatter import CurrencyFormatter

logger = logging.getLogger(__name__)


class ExecuteScheduleDialog(QDialog):
    """
    Dialog de baixa individual de agendamento.

    Apenas monta dados_execucao.
    A regra pesada fica no PaymentService.
    """

    TIPO_PAGAR = "Contas a Pagar"
    TIPO_RECEBER = "Contas a Receber"
    TIPO_TRANSFERENCIA = "Transferências"

    def __init__(self, parent=None, agendamento_id=None, agendamento=None):
        super().__init__(parent)

        if not agendamento_id and not agendamento:
            raise ValueError("Agendamento obrigatório.")

        self.agendamento_id = agendamento_id
        self.agendamento = agendamento or {}
        self.dados_execucao = None

        self.schedule_controller = ScheduleController()
        self.account_controller = AccountController()
        self.category_controller = CategoryController()
        self.favorecido_controller = FavorecidoController()

        self.setMinimumSize(739, 535)

        self._init_ui()
        self._carregar_dados()
        self._connect_events()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setObjectName("pageTitle")
        layout.addWidget(self.label)

        self.detalhesDoPagamentoLabel = QLabel()
        self.detalhesDoPagamentoLabel.setObjectName("sectionTitle")
        layout.addWidget(self.detalhesDoPagamentoLabel)

        detalhes_layout = QHBoxLayout()
        form_esq = QFormLayout()
        form_dir = QFormLayout()

        self.lbl_tipo = QLabel()
        self.tipo_combox = QComboBox()
        self.tipo_combox.addItem("Contas a Pagar", self.TIPO_PAGAR)
        self.tipo_combox.addItem("Contas a Receber", self.TIPO_RECEBER)
        self.tipo_combox.setEnabled(False)

        self.lab_pag = QLabel()
        self.pag_combox = QComboBox()
        self.pag_combox.setEnabled(False)

        self.lb_desc = QLabel()
        self.edit_desc = QLineEdit()
        self.edit_desc.setReadOnly(True)

        form_esq.addRow(self.lbl_tipo, self.tipo_combox)
        form_esq.addRow(self.lab_pag, self.pag_combox)
        form_esq.addRow(self.lb_desc, self.edit_desc)

        self.lb_Data_venc = QLabel()
        self.edit_data_venc = QDateEdit()
        self.edit_data_venc.setCalendarPopup(True)
        self.edit_data_venc.setEnabled(False)

        self.lbl_valor_previsto = QLabel()
        self.valor_previsto_edit = QDoubleSpinBox()
        self.valor_previsto_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.valor_previsto_edit)
        self.valor_previsto_edit.setDecimals(2)
        self.valor_previsto_edit.setRange(0, 1_000_000)
        self.valor_previsto_edit.setReadOnly(True)

        form_dir.addRow(self.lb_Data_venc, self.edit_data_venc)
        form_dir.addRow(self.lbl_valor_previsto, self.valor_previsto_edit)

        detalhes_layout.addLayout(form_esq)
        detalhes_layout.addLayout(form_dir)
        layout.addLayout(detalhes_layout)

        self.Dado_pag = QLabel()
        self.Dado_pag.setObjectName("sectionTitle")
        layout.addWidget(self.Dado_pag)

        dados_layout = QHBoxLayout()
        form_pag_esq = QFormLayout()
        form_pag_dir = QFormLayout()

        self.lbl_conta = QLabel()
        self.conta_combo = QComboBox()

        self.lb_desc_pg = QLabel()
        self.desc_pg_edit = QLineEdit()

        self.lbl_categoria = QLabel()
        self.categoria_combo = QComboBox()

        self.lbl_notas = QLabel()
        self.notas_edit = QTextEdit()
        self.notas_edit.setFixedHeight(90)

        form_pag_esq.addRow(self.lbl_conta, self.conta_combo)
        form_pag_esq.addRow(self.lb_desc_pg, self.desc_pg_edit)
        form_pag_esq.addRow(self.lbl_categoria, self.categoria_combo)
        form_pag_esq.addRow(self.lbl_notas, self.notas_edit)

        self.lbl_datapg = QLabel()
        self.datapg_edit = QDateEdit(QDate.currentDate())
        self.datapg_edit.setCalendarPopup(True)

        self.lbl_desconto = QLabel()
        self.desconto_edit = QDoubleSpinBox()
        self.desconto_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.desconto_edit)
        self.desconto_edit.setDecimals(2)
        self.desconto_edit.setRange(0, 1_000_000)

        self.lgbl_multa = QLabel()
        self.multa_edit = QDoubleSpinBox()
        self.multa_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.multa_edit)
        self.multa_edit.setDecimals(2)
        self.multa_edit.setRange(0, 1_000_000)

        self.lbl_juros = QLabel()
        self.jurus_edit = QDoubleSpinBox()
        self.jurus_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.jurus_edit)
        self.jurus_edit.setDecimals(2)
        self.jurus_edit.setRange(0, 1_000_000)

        self.lbl_valor_pago = QLabel()
        self.valor_pago_edit = QDoubleSpinBox()
        self.valor_pago_edit.setPrefix("R$ "); RegionalFormat.configure_widget(self.valor_pago_edit)
        self.valor_pago_edit.setDecimals(2)
        self.valor_pago_edit.setRange(0.01, 1_000_000)

        form_pag_dir.addRow(self.lbl_datapg, self.datapg_edit)
        form_pag_dir.addRow(self.lbl_desconto, self.desconto_edit)
        form_pag_dir.addRow(self.lgbl_multa, self.multa_edit)
        form_pag_dir.addRow(self.lbl_juros, self.jurus_edit)
        form_pag_dir.addRow(self.lbl_valor_pago, self.valor_pago_edit)

        dados_layout.addLayout(form_pag_esq)
        dados_layout.addLayout(form_pag_dir)
        layout.addLayout(dados_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancelar = QPushButton()
        self.btn_confirmar = QPushButton()

        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_confirmar)

        layout.addLayout(btn_layout)

    def _connect_events(self):
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_confirmar.clicked.connect(self.confirmar)

        self.desconto_edit.valueChanged.connect(self._recalcular_total)
        self.multa_edit.valueChanged.connect(self._recalcular_total)
        self.jurus_edit.valueChanged.connect(self._recalcular_total)

    def _carregar_dados(self):
        if self.agendamento_id:
            agendamento = self.schedule_controller.get_schedule_by_id(
                self.agendamento_id
            )

            if agendamento:
                self.agendamento = agendamento

        if not self.agendamento:
            raise ValueError("Agendamento não encontrado.")

        if self._is_transferencia():
            raise ValueError(
                "Transferência deve ser baixada pelo fluxo de transferência."
            )

        self._carregar_favorecidos()
        self._carregar_contas()
        self._carregar_categorias()
        self._preencher_agendamento()

    def _carregar_favorecidos(self):
        self.pag_combox.clear()
        self.pag_combox.addItem(TranslatorApp.get("Nenhum"), None)

        favorecidos = self.favorecido_controller.listar_favorecidos() or []

        for fav in favorecidos:
            self.pag_combox.addItem(
                fav.get("Nome", ""),
                fav.get("ID_Favorecido")
            )

    def _carregar_contas(self):
        self.conta_combo.clear()

        contas = self.account_controller.get_all_accounts() or []

        for conta in contas:
            nome = conta.get("Nome_Conta", "")
            saldo = CurrencyFormatter.format(conta.get("Saldo_Atual", 0))

            self.conta_combo.addItem(
                f"{nome} ({TranslatorApp.get('Saldo')}: {saldo})",
                conta.get("ID_Conta")
            )

    def _carregar_categorias(self):
        self.categoria_combo.clear()
        self.categoria_combo.addItem(TranslatorApp.get("Nenhuma"), None)

        categorias = self.category_controller.get_all_categories() or []

        for categoria in categorias:
            self.categoria_combo.addItem(
                categoria.get("Nome", ""),
                categoria.get("ID_Categoria")
            )

    def _preencher_agendamento(self):
        ag = self.agendamento

        tipo = ag.get("Tipo", self.TIPO_PAGAR)

        index_tipo = self.tipo_combox.findData(tipo)
        if index_tipo >= 0:
            self.tipo_combox.setCurrentIndex(index_tipo)

        self.edit_desc.setText(ag.get("Descricao", ""))
        self.desc_pg_edit.setText(ag.get("Descricao", ""))

        data = ag.get("Data")

        if data:
            data_qt = QDate.fromString(data, "yyyy-MM-dd")

            if data_qt.isValid():
                self.edit_data_venc.setDate(data_qt)
                self.datapg_edit.setDate(data_qt)

        valor = abs(float(ag.get("Valor", 0)))

        self.valor_previsto_edit.setValue(valor)
        self.valor_pago_edit.setValue(valor)

        idx_fav = self.pag_combox.findData(ag.get("ID_Favorecido"))
        if idx_fav >= 0:
            self.pag_combox.setCurrentIndex(idx_fav)

        idx_conta = self.conta_combo.findData(ag.get("ID_Conta"))
        if idx_conta >= 0:
            self.conta_combo.setCurrentIndex(idx_conta)

        idx_categoria = self.categoria_combo.findData(
            ag.get("ID_Categoria")
        )
        if idx_categoria >= 0:
            self.categoria_combo.setCurrentIndex(idx_categoria)

        self._recalcular_total()

    def _atualizar_textos(self, *_):
        self.setWindowTitle(TranslatorApp.get("Baixa de Agendamento"))

        self.label.setText(TranslatorApp.get("Baixa de Agendamento"))

        self.detalhesDoPagamentoLabel.setText(
            TranslatorApp.get("Detalhes do Agendamento:")
        )

        self.Dado_pag.setText(
            TranslatorApp.get(self._titulo_dados_execucao())
        )

        self.lbl_tipo.setText(TranslatorApp.get("Tipo:"))
        self.lab_pag.setText(TranslatorApp.get(self._label_favorecido()))
        self.lb_desc.setText(TranslatorApp.get("Descrição:"))

        self.lb_Data_venc.setText(
            TranslatorApp.get("Data do Vencimento:")
        )

        self.lbl_valor_previsto.setText(
            TranslatorApp.get("Valor previsto:")
        )

        self.lbl_conta.setText(TranslatorApp.get(self._label_conta()))

        self.lb_desc_pg.setText(
            TranslatorApp.get(self._label_descricao_execucao())
        )

        self.lbl_categoria.setText(TranslatorApp.get("Categoria:"))
        self.lbl_notas.setText(TranslatorApp.get("Notas:"))

        self.lbl_datapg.setText(
            TranslatorApp.get(self._label_data_execucao())
        )

        self.lbl_desconto.setText(TranslatorApp.get("Desconto:"))
        self.lgbl_multa.setText(TranslatorApp.get("Multa:"))
        self.lbl_juros.setText(TranslatorApp.get("Juros:"))

        self.lbl_valor_pago.setText(
            TranslatorApp.get(self._label_total())
        )

        self.btn_confirmar.setText(
            TranslatorApp.get(self._texto_botao())
        )

        self.btn_cancelar.setText(
            TranslatorApp.get("Cancelar")
        )

    def _tipo(self):
        return self.tipo_combox.currentData() or self.agendamento.get("Tipo")

    def _is_receita(self):
        return self._tipo() == self.TIPO_RECEBER

    def _is_despesa(self):
        return self._tipo() == self.TIPO_PAGAR

    def _is_transferencia(self):
        return self.agendamento.get("Tipo") == self.TIPO_TRANSFERENCIA

    def _titulo_dados_execucao(self):
        return (
            "Dados do Recebimento:"
            if self._is_receita()
            else "Dados do Pagamento:"
        )

    def _label_favorecido(self):
        return (
            "Receber de:"
            if self._is_receita()
            else "Pagar para:"
        )

    def _label_conta(self):
        return (
            "Conta para recebimento:"
            if self._is_receita()
            else "Conta para pagamento:"
        )

    def _label_descricao_execucao(self):
        return (
            "Descrição do recebimento:"
            if self._is_receita()
            else "Descrição do pagamento:"
        )

    def _label_data_execucao(self):
        return (
            "Data do Recebimento:"
            if self._is_receita()
            else "Data do Pagamento:"
        )

    def _label_total(self):
        return (
            "Total recebido:"
            if self._is_receita()
            else "Total a pagar:"
        )

    def _texto_botao(self):
        return "Receber" if self._is_receita() else "Pagar"

    def _recalcular_total(self):
        previsto = self.valor_previsto_edit.value()
        desconto = self.desconto_edit.value()
        multa = self.multa_edit.value()
        juros = self.jurus_edit.value()

        total = previsto + multa + juros - desconto

        if total < 0:
            total = 0

        self.valor_pago_edit.blockSignals(True)
        self.valor_pago_edit.setValue(total)
        self.valor_pago_edit.blockSignals(False)

    def get_dados_execucao(self):
        return self.dados_execucao

    def confirmar(self):
        try:
            id_conta = self.conta_combo.currentData()

            if not id_conta:
                raise ValueError(
                    TranslatorApp.get("Conta obrigatória.")
                )

            descricao = self.desc_pg_edit.text().strip()

            if not descricao:
                raise ValueError(
                    TranslatorApp.get("Descrição obrigatória.")
                )

            valor_final = self.valor_pago_edit.value()

            if valor_final <= 0:
                raise ValueError(
                    TranslatorApp.get("Valor inválido.")
                )

            self.dados_execucao = {
                "ID_Agendamento": self.agendamento.get(
                    "ID_Agendamento",
                    self.agendamento_id
                ),
                "Tipo_Agendamento": self._tipo(),
                "Tipo": "Receita" if self._is_receita() else "Despesa",
                "ID_Conta": id_conta,
                "Descricao": descricao,
                "Data": self.datapg_edit.date().toString("yyyy-MM-dd"),
                "Valor_Final": valor_final,
                "Valor_Previsto": self.valor_previsto_edit.value(),
                "Desconto": self.desconto_edit.value(),
                "Multa": self.multa_edit.value(),
                "Juros": self.jurus_edit.value(),
                "ID_Categoria": self.categoria_combo.currentData(),
                "ID_Favorecido": self.pag_combox.currentData(),
                "Notas": self.notas_edit.toPlainText(),
            }

            self.accept()

        except Exception as e:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)