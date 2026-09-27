"""Detalhes das parcelas e pagamentos de uma dívida."""

from PyQt5.QtWidgets import QDialog, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from utilitarios.currency_formatter import CurrencyFormatter


class ParcelasDividaView(QDialog):
    def __init__(self, divida, parent=None):
        super().__init__(parent); self.setWindowTitle(f"Detalhes · {divida['Descricao']}"); self.resize(850, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Saldo atual: {CurrencyFormatter.format(divida['Saldo_Devedor'])} · Status: {divida['Status']}"))
        tabs = QTabWidget(); layout.addWidget(tabs)
        tabs.addTab(self._table(divida.get("Parcelas", []), [
            ("Número", "Numero_Parcela"), ("Vencimento", "Data_Vencimento"),
            ("Previsto", "Valor_Previsto"), ("Pago", "Valor_Pago"), ("Status", "Status")
        ], {"Valor_Previsto", "Valor_Pago"}), "Parcelas")
        tabs.addTab(self._table(divida.get("Pagamentos", []), [
            ("Data", "Data_Pagamento"), ("Conta", "Conta"), ("Pago", "Valor_Pago"),
            ("Amortizado", "Valor_Amortizado"), ("Juros", "Valor_Juros"),
            ("Multa", "Valor_Multa"), ("Desconto", "Valor_Desconto")
        ], {"Valor_Pago", "Valor_Amortizado", "Valor_Juros", "Valor_Multa", "Valor_Desconto"}), "Pagamentos")

    @staticmethod
    def _table(rows, columns, money):
        table = QTableWidget(len(rows), len(columns)); table.setHorizontalHeaderLabels([x[0] for x in columns])
        table.setEditTriggers(QTableWidget.NoEditTriggers); table.setSelectionBehavior(QTableWidget.SelectRows)
        for row_index, row in enumerate(rows):
            for col_index, (_, key) in enumerate(columns):
                value = row.get(key, "")
                if key in money: value = CurrencyFormatter.format(value or 0)
                table.setItem(row_index, col_index, QTableWidgetItem(str(value or "")))
        table.resizeColumnsToContents(); return table
