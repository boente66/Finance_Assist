"""Gerenciador visual de dívidas e empréstimos."""

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QInputDialog, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from controllers.divida_controller import DividaController
from utilitarios.currency_formatter import CurrencyFormatter
from views.divida_dialog import DividaDialog
from views.agendamento_divida_dialog import AgendamentoDividaDialog
from views.pagamento_divida_dialog import PagamentoDividaDialog
from views.parcelas_divida_view import ParcelasDividaView


class DividaView(QWidget):
    COLUMNS = (
        "Credor", "Contrato", "Descrição", "Tipo", "Contratado",
        "Saldo devedor", "Parcelas", "Valor parcela", "Juros",
        "Próximo vencimento", "Status",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = DividaController(); self.items = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(14, 12, 14, 14); root.setSpacing(12)
        head = QHBoxLayout(); titles = QVBoxLayout()
        title = QLabel("Dívidas e empréstimos"); title.setObjectName("pageTitle")
        subtitle = QLabel("Acompanhe contratos, parcelas, vencimentos e pagamentos reais."); subtitle.setObjectName("pageSubtitle")
        titles.addWidget(title); titles.addWidget(subtitle); head.addLayout(titles); head.addStretch()
        self.new_btn = QPushButton("＋ Nova dívida"); self.new_btn.setObjectName("primaryButton")
        self.pay_btn = QPushButton("Registrar pagamento"); self.schedule_btn = QPushButton("Agendar pagamento"); self.finish_btn = QPushButton("Encerrar"); self.details_btn = QPushButton("Ver parcelas")
        head.addWidget(self.details_btn); head.addWidget(self.finish_btn); head.addWidget(self.schedule_btn); head.addWidget(self.pay_btn); head.addWidget(self.new_btn); root.addLayout(head)

        self.alert = QLabel(); self.alert.setObjectName("infoBanner"); self.alert.setWordWrap(True); root.addWidget(self.alert)
        cards = QGridLayout(); self.total_card = self._card("Saldo devedor"); self.active_card = self._card("Dívidas ativas"); self.overdue_card = self._card("Parcelas atrasadas"); self.next_card = self._card("Próximo compromisso")
        for i, card in enumerate((self.total_card, self.active_card, self.overdue_card, self.next_card)): cards.addWidget(card[0], 0, i)
        root.addLayout(cards)

        filters = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Buscar credor, contrato ou descrição...")
        self.status = QComboBox(); self.status.addItem("Todos os status", None)
        for value in ("ATIVA", "ATRASADA", "QUITADA", "RENEGOCIADA", "CANCELADA"): self.status.addItem(value.title(), value)
        self.order = QComboBox(); self.order.addItem("Ordenar: vencimento", "due"); self.order.addItem("Credor: A–Z", "az"); self.order.addItem("Maior saldo", "balance")
        filters.addWidget(self.search, 1); filters.addWidget(self.status); filters.addWidget(self.order); root.addLayout(filters)

        self.table = QTableWidget(0, len(self.COLUMNS)); self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True); root.addWidget(self.table, 1)
        self.new_btn.clicked.connect(self.nova); self.pay_btn.clicked.connect(self.pagar); self.schedule_btn.clicked.connect(self.agendar); self.finish_btn.clicked.connect(self.encerrar); self.details_btn.clicked.connect(self.detalhes)
        self.table.doubleClicked.connect(self.detalhes); self.search.textChanged.connect(self.render); self.status.currentIndexChanged.connect(self.render); self.order.currentIndexChanged.connect(self.render)

    @staticmethod
    def _card(label):
        frame = QFrame(); frame.setObjectName("metricCard"); box = QVBoxLayout(frame)
        caption = QLabel(label); caption.setObjectName("metricLabel"); value = QLabel("—"); value.setObjectName("metricValue")
        box.addWidget(caption); box.addWidget(value); return frame, value

    def on_load(self):
        self.load_data()

    def load_data(self):
        try:
            self.items = self.controller.listar()
            self._summary(); self.render()
        except Exception as exc:
            QMessageBox.warning(self, "Dívidas", str(exc))

    def _summary(self):
        total = sum(float(x["Saldo_Devedor"]) for x in self.items if x["Status"] not in ("QUITADA", "CANCELADA"))
        active = sum(x["Status"] in ("ATIVA", "ATRASADA") for x in self.items)
        overdue = sum(max(0, int(x.get("Total_Parcelas") or 0) - int(x.get("Parcelas_Pagas") or 0)) for x in self.items if x["Status"] == "ATRASADA")
        pending = [x for x in self.items if x["Status"] in ("ATIVA", "ATRASADA") and (x.get("Proximo_Vencimento") or x.get("Primeiro_Vencimento"))]
        next_item = min(pending, key=lambda x: x.get("Proximo_Vencimento") or x["Primeiro_Vencimento"], default=None)
        self.total_card[1].setText(CurrencyFormatter.format(total)); self.active_card[1].setText(str(active)); self.overdue_card[1].setText(str(overdue))
        self.next_card[1].setText((next_item.get("Proximo_Vencimento") or next_item["Primeiro_Vencimento"]) if next_item else "Sem vencimento")
        if next_item:
            self.alert.setText(f"Próximo compromisso: {next_item['Descricao']} · saldo {CurrencyFormatter.format(next_item['Saldo_Devedor'])} · vencimento {(next_item.get('Proximo_Vencimento') or next_item['Primeiro_Vencimento'])}.")
        else:
            self.alert.setText("Nenhuma dívida pendente. Pagamentos e previsões permanecem disponíveis no histórico.")

    def _filtered(self):
        text = self.search.text().strip().casefold(); status = self.status.currentData()
        rows = [x for x in self.items if (not status or x["Status"] == status) and (not text or text in " ".join(str(x.get(k) or "") for k in ("Favorecido", "Numero_Contrato", "Descricao")).casefold())]
        if self.order.currentData() == "az": rows.sort(key=lambda x: (x.get("Favorecido") or "").casefold())
        elif self.order.currentData() == "balance": rows.sort(key=lambda x: float(x["Saldo_Devedor"]), reverse=True)
        else: rows.sort(key=lambda x: x.get("Proximo_Vencimento") or x.get("Primeiro_Vencimento") or "9999-12-31")
        return rows

    def render(self, *_):
        rows = self._filtered(); self.table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            progress = f"{int(item.get('Parcelas_Pagas') or 0)}/{int(item.get('Total_Parcelas') or 0)}" if item["Tipo_Parcelamento"] == "FIXO" else "Livre"
            values = (item.get("Favorecido") or "—", item.get("Numero_Contrato") or "—", item["Descricao"], item["Tipo_Divida"], CurrencyFormatter.format(item["Valor_Total_Contrato"]), CurrencyFormatter.format(item["Saldo_Devedor"]), progress, CurrencyFormatter.format(item.get("Valor_Parcela") or 0), f"{float(item.get('Taxa_Juros') or 0):.2f}%", item.get("Proximo_Vencimento") or item.get("Primeiro_Vencimento") or "Livre", item["Status"])
            for c, value in enumerate(values): self.table.setItem(r, c, QTableWidgetItem(str(value)))
            self.table.item(r, 0).setData(Qt.UserRole, item["ID_Divida"])
        self.table.resizeColumnsToContents()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0: raise ValueError("Selecione uma dívida.")
        return self.table.item(row, 0).data(Qt.UserRole)

    def nova(self):
        if DividaDialog(self).exec_() == DividaDialog.Accepted: self.load_data()

    def detalhes(self, *_):
        try: ParcelasDividaView(self.controller.obter(self._selected_id()), self).exec_()
        except Exception as exc: QMessageBox.information(self, "Dívidas", str(exc))

    def pagar(self):
        try:
            debt = self.controller.obter(self._selected_id())
            if PagamentoDividaDialog(debt, self).exec_() == PagamentoDividaDialog.Accepted: self.load_data()
        except Exception as exc: QMessageBox.warning(self, "Pagamento", str(exc))

    def agendar(self):
        try:
            debt = self.controller.obter(self._selected_id())
            if AgendamentoDividaDialog(debt, self).exec_() == AgendamentoDividaDialog.Accepted:
                QMessageBox.information(self, "Agendamento criado", "A previsão aparecerá em Agendamentos. O saldo da dívida só muda após a execução.")
                self.load_data()
        except Exception as exc: QMessageBox.warning(self, "Agendamento", str(exc))

    def encerrar(self):
        try:
            debt_id = self._selected_id()
            label, ok = QInputDialog.getItem(
                self, "Encerrar dívida", "Motivo do encerramento",
                ["Renegociada", "Cancelada"], 0, False,
            )
            if not ok: return
            status = "RENEGOCIADA" if label == "Renegociada" else "CANCELADA"
            if QMessageBox.question(
                self, "Confirmar encerramento",
                "As parcelas e previsões pendentes serão canceladas. Continuar?",
            ) == QMessageBox.Yes:
                self.controller.encerrar(debt_id, status); self.load_data()
        except Exception as exc: QMessageBox.warning(self, "Encerramento", str(exc))
