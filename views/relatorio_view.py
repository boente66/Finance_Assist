# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QListWidget,
    QStackedWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QFrame,
    QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from controllers.relatorio_controller import RelatorioController
from utilitarios.makepdf import MakePDF
from utilitarios.currency_formatter import CurrencyFormatter
from core.translator_app import TranslatorApp
from core.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class RelatorioView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = RelatorioController()
        self.figure = None
        self.canvas = None

        self.setWindowTitle("Relatórios")

        self._init_ui()
        self._connect_events()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self.on_load()

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("pageSubtitle")
        root_layout.addWidget(self.page_title)
        root_layout.addWidget(self.page_subtitle)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        root_layout.addWidget(self.main_splitter, 1)

        sidebar = QFrame()
        sidebar.setObjectName("card")

        sidebar_layout = QVBoxLayout(sidebar)

        self.titulo = QLabel()
        self.titulo.setObjectName("pageTitle")
        self.titulo.setAlignment(Qt.AlignCenter)

        self.sections = QListWidget()

        sidebar_layout.addWidget(self.titulo)
        sidebar_layout.addWidget(self.sections)
        sidebar_layout.addStretch()

        sidebar.setMinimumWidth(170)
        self.main_splitter.addWidget(sidebar)

        self.stacked = QStackedWidget()

        self.w_diario = self._build_diario()
        self.w_anual = self._build_anual()
        self.w_informe = self._build_informe()

        self.stacked.addWidget(self.w_diario)
        self.stacked.addWidget(self.w_anual)
        self.stacked.addWidget(self.w_informe)

        self.main_splitter.addWidget(self.stacked)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([220, 900])

        self.sections.setCurrentRow(0)

    def set_compact_mode(self, compact, available_width=None):
        width = int(available_width or self.width())
        self.main_splitter.setSizes([180 if width < 900 else 220, max(380, width - 220)])

    # ==================================================
    # EVENTOS
    # ==================================================
    def _connect_events(self):
        self.sections.currentRowChanged.connect(
            self._change_section
        )
        self.btn_gerar_anual.clicked.connect(self.load_anual)
        self.combo_anual.currentIndexChanged.connect(self.load_anual)
        self.combo_inf.currentIndexChanged.connect(self.preview)

        self.btn_gerar_diario.clicked.connect(
            self.load_diario
        )

        self.btn_preview.clicked.connect(
            self.preview
        )

        self.btn_pdf.clicked.connect(
            self.export_pdf
        )

        self.btn_print.clicked.connect(
            self.print_pdf
        )

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Relatórios")
        )

        self.titulo.setText(
            TranslatorApp.get("Tipos de Relatório")
        )
        self.page_title.setText(TranslatorApp.get("Relatórios"))
        self.page_subtitle.setText(
            TranslatorApp.get("Analise receitas, despesas e desempenho financeiro")
        )

        atual = self.sections.currentRow()

        self.sections.blockSignals(True)
        self.sections.clear()
        self.sections.addItems([
            TranslatorApp.get("Relatório Diário"),
            TranslatorApp.get("Relatório Anual"),
            TranslatorApp.get("Informe de Rendimentos"),
        ])

        if atual >= 0:
            self.sections.setCurrentRow(atual)
        else:
            self.sections.setCurrentRow(0)

        self.sections.blockSignals(False)

        self.lbl_dias.setText(
            TranslatorApp.get("Dias:")
        )

        self.btn_gerar_diario.setText(
            TranslatorApp.get("Gerar")
        )

        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("Data"),
            TranslatorApp.get("Categoria"),
            TranslatorApp.get("Receita"),
            TranslatorApp.get("Despesa"),
            TranslatorApp.get("Economia"),
        ])

        self.table_anual.setHorizontalHeaderLabels([
            TranslatorApp.get("Mês"),
            TranslatorApp.get("Categoria"),
            TranslatorApp.get("Receita"),
            TranslatorApp.get("Despesa"),
            TranslatorApp.get("Economia"),
        ])

        self.lbl_ano_base.setText(
            TranslatorApp.get("Ano Base:")
        )
        self.lbl_ano_anual.setText(TranslatorApp.get("Ano:"))
        self.btn_gerar_anual.setText(TranslatorApp.get("Gerar"))
        self.input_days.setItemText(self.input_days.count() - 1, TranslatorApp.get("Todo histórico"))

        self.btn_preview.setText(
            TranslatorApp.get("Visualizar")
        )

        self.btn_pdf.setText(
            TranslatorApp.get("PDF")
        )

        self.btn_print.setText(
            TranslatorApp.get("Imprimir")
        )

        self._atualizar_cards_textos()

    def _atualizar_cards_textos(self):
        self.lbl_card_receita_title.setText(
            TranslatorApp.get("Receitas")
        )

        self.lbl_card_despesa_title.setText(
            TranslatorApp.get("Despesas")
        )

        self.lbl_card_saldo_title.setText(
            TranslatorApp.get("Saldo")
        )

    # ==================================================
    # CARDS
    # ==================================================
    def _create_cards(self):
        layout = QHBoxLayout()

        def create_card():
            card = QFrame()
            card.setObjectName("card")

            v = QVBoxLayout(card)

            lbl_title = QLabel()
            lbl_value = QLabel("R$ 0,00")

            lbl_title.setObjectName("cardTitle")
            lbl_value.setObjectName("cardValue")

            v.addWidget(lbl_title)
            v.addWidget(lbl_value)

            return card, lbl_title, lbl_value

        (
            self.card_receita,
            self.lbl_card_receita_title,
            self.lbl_receita,
        ) = create_card()

        (
            self.card_despesa,
            self.lbl_card_despesa_title,
            self.lbl_despesa,
        ) = create_card()

        (
            self.card_saldo,
            self.lbl_card_saldo_title,
            self.lbl_saldo,
        ) = create_card()

        layout.addWidget(self.card_receita)
        layout.addWidget(self.card_despesa)
        layout.addWidget(self.card_saldo)

        return layout

    # ==================================================
    # GRÁFICO
    # ==================================================
    def _create_chart(self):
        try:
            from matplotlib.backends.backend_qt5agg import (
                FigureCanvasQTAgg as FigureCanvas
            )
            from matplotlib.figure import Figure

            self.figure = Figure(figsize=(8, 4))
            self.canvas = FigureCanvas(self.figure)

            return self.canvas

        except Exception:
            self.figure = None
            self.canvas = QLabel()
            self.canvas.setWordWrap(True)
            self.canvas.setObjectName("infoLabel")
            self.canvas.setText(
                TranslatorApp.get(
                    "Gráficos indisponíveis neste ambiente. "
                    "Os relatórios continuam funcionando sem visualização gráfica."
                )
            )

            return self.canvas

    def _update_chart(self, dados):
        if not self.figure or not hasattr(self.canvas, "draw"):
            return

        self.figure.clear()

        receitas = [
            float(d.get("Receita", 0) or 0)
            for d in dados
        ]
        despesas = [
            float(d.get("Despesa", 0) or 0)
            for d in dados
        ]

        colors = ThemeManager.get_chart_colors()

        ax1 = self.figure.add_subplot(131)
        ax1.bar(
            [
                TranslatorApp.get("Receitas"),
                TranslatorApp.get("Despesas"),
            ],
            [
                sum(receitas),
                sum(despesas),
            ],
            color=[
                colors["receita"],
                colors["despesa"],
            ],
        )
        ax1.set_title(
            TranslatorApp.get("Resumo"),
            color=colors["text"]
        )
        ax1.grid(
            color=colors["grid"],
            linestyle="--",
            alpha=0.3
        )

        ax2 = self.figure.add_subplot(132)

        saldo = []
        total = 0

        for r, d in zip(receitas, despesas):
            total += r - d
            saldo.append(total)

        ax2.plot(
            saldo,
            color=colors["saldo"]
        )
        ax2.set_title(
            TranslatorApp.get("Evolução"),
            color=colors["text"]
        )
        ax2.grid(
            color=colors["grid"],
            linestyle="--",
            alpha=0.3
        )

        ax3 = self.figure.add_subplot(133)
        if sum(receitas) + sum(despesas) > 0:
            ax3.pie(
                [sum(receitas), sum(despesas)],
                labels=[TranslatorApp.get("Receitas"), TranslatorApp.get("Despesas")],
                autopct="%1.1f%%"
            )
        else:
            ax3.text(0.5, 0.5, TranslatorApp.get("Sem movimentação"), ha='center')
        ax3.set_title(
            TranslatorApp.get("Distribuição")
        )

        self.figure.tight_layout()
        self.canvas.draw()

    # ==================================================
    # INSIGHTS
    # ==================================================
    def _create_insights(self):
        self.lbl_insights = QLabel()
        self.lbl_insights.setObjectName("infoLabel")

        return self.lbl_insights

    def _update_insights(self, receitas, despesas):
        if despesas > receitas:
            texto = "⚠️ " + TranslatorApp.get(
                "Gastos maiores que receitas"
            )

        elif receitas > despesas * 2:
            texto = "🔥 " + TranslatorApp.get(
                "Excelente controle financeiro"
            )

        else:
            texto = "✔️ " + TranslatorApp.get(
                "Situação equilibrada"
            )

        self.lbl_insights.setText(texto)

    # ==================================================
    # DIÁRIO
    # ==================================================
    def _build_diario(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addLayout(self._create_cards())
        layout.addWidget(self._create_chart())
        layout.addWidget(self._create_insights())

        ctrl = QHBoxLayout()

        self.lbl_dias = QLabel()
        self.input_days = QComboBox()
        for dias in (7, 15, 30, 90):
            self.input_days.addItem(str(dias), dias)
        self.input_days.addItem(TranslatorApp.get("Todo histórico"), None)
        self.input_days.setCurrentIndex(2)

        self.btn_gerar_diario = QPushButton()

        ctrl.addWidget(self.lbl_dias)
        ctrl.addWidget(self.input_days)
        ctrl.addWidget(self.btn_gerar_diario)
        ctrl.addStretch()

        layout.addLayout(ctrl)

        self.table = QTableWidget()
        self.table.setColumnCount(5)

        layout.addWidget(self.table)

        return w

    def load_diario(self):
        try:
            dias = self.input_days.currentData()

            data = self.controller.relatorio_diario(dias)

            if data is None:
                self._reset_summary()
                self._error(
                    self.table,
                    TranslatorApp.get("Não foi possível gerar o relatório."),
                )
                return

            if not data:
                self._reset_summary()
                self._empty(self.table)
                return

            receitas = sum(
                float(r.get("Receita", 0) or 0)
                for r in data
            )
            despesas = sum(
                float(r.get("Despesa", 0) or 0)
                for r in data
            )
            saldo = receitas - despesas

            self.lbl_receita.setText(
                CurrencyFormatter.format(receitas)
            )
            self.lbl_despesa.setText(
                CurrencyFormatter.format(despesas)
            )
            self.lbl_saldo.setText(
                CurrencyFormatter.format(saldo)
            )

            self._fill_table(self.table, data)
            self._update_insights(receitas, despesas)
            try:
                self._update_chart(data)
            except Exception:
                logger.warning("Gráfico indisponível; tabela preservada", exc_info=True)

        except Exception:
            logger.exception(
                "Erro relatório diário"
            )
            self._reset_summary()
            self._error(self.table, TranslatorApp.get("Não foi possível gerar o relatório."))

    # ==================================================
    # ANUAL
    # ==================================================
    def _build_anual(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        controls = QHBoxLayout()
        self.lbl_ano_anual = QLabel()
        self.combo_anual = QComboBox()
        self.btn_gerar_anual = QPushButton()
        controls.addWidget(self.lbl_ano_anual)
        controls.addWidget(self.combo_anual)
        controls.addWidget(self.btn_gerar_anual)
        controls.addStretch()
        layout.addLayout(controls)

        self.table_anual = QTableWidget()
        self.table_anual.setColumnCount(5)

        layout.addWidget(self.table_anual)

        return w

    def _reset_summary(self):
        for label in (self.lbl_receita, self.lbl_despesa, self.lbl_saldo):
            label.setText(CurrencyFormatter.format(0))
        self.lbl_insights.setText(TranslatorApp.get("Sem movimentação no período selecionado"))
        if self.figure is not None:
            self.figure.clear()
            self.canvas.draw()

    def load_anual(self):
        try:
            data = self.controller.relatorio_anual(int(self.combo_anual.currentText()))
            if data is None:
                self._error(self.table_anual, TranslatorApp.get("Não foi possível gerar o relatório."))
            elif data:
                self._fill_table(self.table_anual, data)
            else:
                self._empty(self.table_anual)
        except Exception:
            logger.exception("Erro relatório anual")
            self._error(self.table_anual, TranslatorApp.get("Não foi possível gerar o relatório."))

    def _change_section(self, index):
        if index not in (0, 1, 2):
            return
        self.stacked.setCurrentIndex(index)
        (self.load_diario, self.load_anual, self.preview)[index]()

    def on_load(self):
        try:
            anos = sorted(set(self.controller.anos_disponiveis()) | {datetime.now().year}, reverse=True)
            for combo in (self.combo_anual, self.combo_inf):
                selected = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItems([str(ano) for ano in anos])
                if selected in [str(ano) for ano in anos]:
                    combo.setCurrentText(selected)
                combo.blockSignals(False)
            self._change_section(self.sections.currentRow())
        except Exception:
            logger.exception("Erro ao atualizar períodos dos relatórios")
            self._reset_summary()
            self._error(self.table, TranslatorApp.get("Não foi possível carregar os períodos."))
            self._error(self.table_anual, TranslatorApp.get("Não foi possível carregar os períodos."))
            self.text.setPlainText(TranslatorApp.get("Não foi possível carregar os períodos."))
            self.btn_pdf.setEnabled(False)
            self.btn_print.setEnabled(False)

    # ==================================================
    # INFORME
    # ==================================================
    def _build_informe(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()

        self.lbl_ano_base = QLabel()

        self.combo_inf = QComboBox()
        ano = datetime.now().year
        self.combo_inf.addItems([
            str(a)
            for a in range(ano, ano - 6, -1)
        ])

        self.btn_preview = QPushButton()
        self.btn_pdf = QPushButton()
        self.btn_print = QPushButton()

        ctrl.addWidget(self.lbl_ano_base)
        ctrl.addWidget(self.combo_inf)
        ctrl.addWidget(self.btn_preview)
        ctrl.addWidget(self.btn_pdf)
        ctrl.addWidget(self.btn_print)

        layout.addLayout(ctrl)

        self.text = QTextEdit()
        self.text.setReadOnly(True)

        layout.addWidget(self.text)

        return w

    def preview(self):
        try:
            txt = self.controller.gerar_texto_informe(int(self.combo_inf.currentText()))
        except Exception:
            logger.exception("Erro ao carregar informe")
            txt = None
        self.text.setPlainText(txt if txt is not None else TranslatorApp.get("Não foi possível gerar o informe."))
        self.btn_pdf.setEnabled(txt is not None)
        self.btn_print.setEnabled(txt is not None)
        return txt is not None

    def export_pdf(self):
        if not self.preview():
            return
        txt = self.text.toPlainText()

        if not txt:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            TranslatorApp.get("Salvar"),
            "informe.pdf",
            "PDF (*.pdf)"
        )

        if path:
            MakePDF.gerar_pdf(
                path,
                TranslatorApp.get("Informe de Rendimentos"),
                txt
            )

    def print_pdf(self):
        if not self.preview():
            return
        printer = QPrinter()
        dlg = QPrintDialog(printer, self)

        if dlg.exec_():
            self.text.print_(printer)

    # ==================================================
    # UTIL
    # ==================================================
    def _fill_table(self, table, data):
        table.setRowCount(0)
        table.setColumnCount(5)
        keys = ('Mes' if table is self.table_anual else 'Data', 'Categoria', 'Receita', 'Despesa', 'Economia')
        table.setHorizontalHeaderLabels([TranslatorApp.get('Mês' if key == 'Mes' else key) for key in keys])

        for i, row in enumerate(data):
            table.insertRow(i)

            values = [row.get(key, '') for key in keys]

            for j, val in enumerate(values):
                if isinstance(val, (int, float)):
                    val = CurrencyFormatter.format(val)

                table.setItem(
                    i,
                    j,
                    QTableWidgetItem(str(val))
                )

    def _empty(self, table):
        table.setRowCount(1)
        table.setColumnCount(1)
        table.setHorizontalHeaderLabels([
            TranslatorApp.get("Resultado")
        ])
        table.setItem(
            0,
            0,
            QTableWidgetItem(
                "📭 " + TranslatorApp.get("Nenhum dado")
            )
        )

    def _error(self, table, message):
        table.setRowCount(1)
        table.setColumnCount(1)
        table.setHorizontalHeaderLabels([TranslatorApp.get("Erro")])
        item = QTableWidgetItem(message)
        table.setItem(0, 0, item)

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
