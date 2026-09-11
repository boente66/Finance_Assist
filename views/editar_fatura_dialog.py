"""Edição segura de um lançamento já existente na fatura."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMessageBox

from views.fatura_dialog import FaturaDialog


class EditarFaturaDialog(FaturaDialog):
    def __init__(self, lancamento, parent=None):
        if not lancamento:
            raise ValueError("Lançamento inválido.")
        self.lancamento = dict(lancamento)
        super().__init__(parent=parent, id_cartao=self.lancamento["ID_Cartao"])
        self.setWindowTitle("Editar lançamento da fatura")
        self.parcelas_spin.setRange(1, max(36, int(self.lancamento.get("Num_Parcelas") or 1)))
        self.parcelas_spin.setToolTip(
            "A edição altera somente este lançamento; não recria as outras parcelas."
        )
        self._preencher()

    def _preencher(self):
        item = self.lancamento
        self.descricao_edit.setText(str(item.get("Descricao") or ""))
        self.valor_edit.setText(f"{float(item.get('Valor') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        data = QDate.fromString(str(item.get("Data") or ""), "yyyy-MM-dd")
        if data.isValid():
            self.data_edit.setDate(data)
        self._carregar_categorias(item.get("ID_Categoria"))
        self._carregar_favorecidos(item.get("ID_Favorecido"))
        competencia = (int(item.get("Competencia_Mes")), int(item.get("Competencia_Ano")))
        for index in range(self.fatura_combo.count()):
            ciclo = self.fatura_combo.itemData(index)
            if ciclo and (int(ciclo["Mes"]), int(ciclo["Ano"])) == competencia:
                self.fatura_combo.setCurrentIndex(index)
                break
        self.parcelas_spin.setValue(int(item.get("Num_Parcelas") or 1))
        self.notas_edit.setPlainText(str(item.get("Notas") or ""))

    def salvar(self):
        try:
            dados = self.dados_formulario()
            dados["Parcela_Atual"] = int(self.lancamento.get("Parcela_Atual") or 1)
            dados["Previsto"] = int(self.lancamento.get("Previsto") or 0)
            self.fatura_controller.atualizar_lancamento(
                self.lancamento["ID_Lancamento"], dados
            )
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", str(exc))
