"""Edição segura de um lançamento já existente na fatura."""

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMessageBox

from core.translator_app import TranslatorApp
from views.fatura_dialog import FaturaDialog


class EditarFaturaDialog(FaturaDialog):
    def __init__(self, lancamento, parent=None, capacidade=None):
        if not lancamento:
            raise ValueError("Lançamento inválido.")
        self.capacidade = capacidade
        self.lancamento = dict(lancamento)
        super().__init__(parent=parent, id_cartao=self.lancamento["ID_Cartao"])
        self._title_key = "Editar lançamento da fatura"
        self._atualizar_textos()
        self.parcelas_spin.setRange(1, max(36, int(self.lancamento.get("Num_Parcelas") or 1)))
        self.parcelas_spin.setToolTip(
            TranslatorApp.get("A edição altera somente este lançamento; não recria as outras parcelas.")
        )
        self._preencher()
        if capacidade is not None:
            self.fatura_combo.setEnabled(False)
            self.parcelas_spin.setEnabled(False)

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
        selecionado = False
        for index in range(self.fatura_combo.count()):
            ciclo = self.fatura_combo.itemData(index)
            if ciclo and (int(ciclo["Mes"]), int(ciclo["Ano"])) == competencia:
                self.fatura_combo.setCurrentIndex(index)
                selecionado = True
                break
        if not selecionado:
            mes, ano = competencia
            self.fatura_combo.addItem(f"{mes:02d}/{ano}", {"Mes": mes, "Ano": ano})
            self.fatura_combo.setCurrentIndex(self.fatura_combo.count() - 1)
        self.parcelas_spin.setValue(int(item.get("Num_Parcelas") or 1))
        self.notas_edit.setPlainText(str(item.get("Notas") or ""))

    def salvar(self):
        try:
            dados = self.dados_formulario()
            dados.pop("Paga", None)
            dados["Parcela_Atual"] = int(self.lancamento.get("Parcela_Atual") or 1)
            dados["Previsto"] = int(self.lancamento.get("Previsto") or 0)
            if self.capacidade is None:
                self.fatura_controller.atualizar_lancamento(self.lancamento["ID_Lancamento"], dados)
            else:
                self.fatura_controller.atualizar_lancamento(
                    self.lancamento["ID_Lancamento"], dados, capacidade=self.capacidade
                )
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get("Erro"), TranslatorApp.error(exc))
