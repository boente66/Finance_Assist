import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

import views.importacaoTempeorariaDialog as dialog_module
from services.reconciliacao_importacao_service import (
    ReconciliacaoImportacaoService,
)


class CategoryControllerStub:
    @staticmethod
    def get_nome_categoria_by_id(_id_categoria):
        return ""


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sem_banco_e_sem_mensagem_bloqueante(monkeypatch):
    monkeypatch.setattr(dialog_module, "CategoryController", CategoryControllerStub)
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok
    )


def item(status, importar, descricao):
    return {
        "Data": "2026-08-01",
        "Descricao": descricao,
        "Valor": -10,
        "Tipo": "Despesa",
        "StatusImportacao": status,
        "Importar": importar,
        "MotivoReconciliacao": "Motivo de teste",
        "CorrespondenciaImportacao": "#1 · item existente",
    }


def test_revisao_exibe_status_resumo_e_selecao_segura(app):
    service = ReconciliacaoImportacaoService
    dialog = dialog_module.ImportacaoTemporariaDialog([
        item(service.NOVO, True, "Novo"),
        item(service.DUPLICADO, False, "Duplicado"),
        item(service.POSSIVEL_DUPLICADO, False, "Possível"),
    ])
    app.processEvents()

    assert dialog.table.columnCount() == 9
    assert dialog.table.item(0, dialog.COL_STATUS).text() == "Novo"
    assert dialog.table.item(1, dialog.COL_STATUS).text() == "Duplicado"
    assert dialog.table.cellWidget(0, dialog.COL_IMPORTAR).isChecked()
    assert not dialog.table.cellWidget(1, dialog.COL_IMPORTAR).isEnabled()
    assert not dialog.table.cellWidget(2, dialog.COL_IMPORTAR).isChecked()
    assert "Novos: 1" in dialog.lbl_novos.text()
    assert "Duplicados: 1" in dialog.lbl_duplicados.text()
    dialog.close()


def test_usuario_pode_confirmar_possivel_mas_nunca_duplicado(app):
    service = ReconciliacaoImportacaoService
    dialog = dialog_module.ImportacaoTemporariaDialog([
        item(service.DUPLICADO, False, "Duplicado"),
        item(service.POSSIVEL_DUPLICADO, False, "Possível"),
    ])
    dialog.table.cellWidget(1, dialog.COL_IMPORTAR).setChecked(True)
    dialog.confirmar()

    assert dialog.result() == QDialog.Accepted
    confirmados = dialog.get_lancamentos_confirmados()
    assert len(confirmados) == 1
    assert confirmados[0]["_ConfirmadoPossivel"] is True


def test_reimportacao_total_pode_concluir_com_zero_itens(app):
    service = ReconciliacaoImportacaoService
    dialog = dialog_module.ImportacaoTemporariaDialog([
        item(service.DUPLICADO, False, "Duplicado")
    ])
    dialog.confirmar()

    assert dialog.result() == QDialog.Accepted
    assert dialog.get_lancamentos_confirmados() == []
