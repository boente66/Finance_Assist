import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QApplication, QDialog

import views.categoria_dialog as categoria_dialog_module
import views.fatura_dialog as fatura_module
import views.transaction_dialog_conta as transaction_module
from core.themes import get_theme
from views.animated_add_button import AnimatedAddButton


_APP = None


class CategoryControllerStub:
    def __init__(self):
        self.created = []

    def get_all_categories(self):
        return [
            {"ID_Categoria": 1, "Nome": "Moradia", "Tipo": "Despesa"},
            *[
                {"ID_Categoria": item[0], "Nome": item[1], "Tipo": item[2]}
                for item in self.created
            ],
        ]

    def add_category(self, name, category_type):
        self.created.append((7, name, category_type))
        return 7


class FavoriteControllerStub:
    def listar_favorecidos(self):
        return []


class MainControllerStub:
    def inserir_lancamento(self, data):
        return True


class InvoiceControllerStub:
    def listar_ciclos(self, card_id):
        return [{"Mes": 9, "Ano": 2026}]

    def registrar_despesa_cartao(self, data):
        return True


class CategoryDialogStub:
    def __init__(self, parent=None):
        self.parent = parent

    def exec_(self):
        return QDialog.Accepted

    def get_data(self):
        return {"Nome": "Saúde", "Tipo": "Despesa"}


def _app():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_botao_animado_e_circular_respeita_todos_os_temas():
    _app()
    button = AnimatedAddButton("Adicionar categoria")
    assert button.objectName() == "circularAddButton"
    assert button.size().width() == button.size().height() == 36
    assert button.accessibleName() == "Adicionar categoria"

    button.event(QEvent(QEvent.Enter))
    assert button._hover_animation.state() == button._hover_animation.Running
    for theme in (
        "Primavera",
        "Noite Intensa",
        "Prosperidade",
        "Verão Quente",
        "Personalizado",
    ):
        style = get_theme(theme)
        assert "QPushButton#circularAddButton" in style


def test_lancamento_conta_mantem_inclusao_de_categoria(monkeypatch):
    _app()
    monkeypatch.setattr(transaction_module, "MainController", MainControllerStub)
    monkeypatch.setattr(transaction_module, "FavorecidoController", FavoriteControllerStub)
    monkeypatch.setattr(transaction_module, "CategoryController", CategoryControllerStub)
    monkeypatch.setattr(categoria_dialog_module, "CategoriaDialog", CategoryDialogStub)

    dialog = transaction_module.TransactionDialogConta(id_conta=3)
    dialog.btn_add_cat.click()

    assert dialog.categoria_combo.currentData() == 7
    assert dialog.categoria_combo.currentText() == "Saúde"
    dialog.close()


def test_lancamento_cartao_mantem_inclusao_de_categoria(monkeypatch):
    _app()
    monkeypatch.setattr(fatura_module, "FaturaController", InvoiceControllerStub)
    monkeypatch.setattr(fatura_module, "FavorecidoController", FavoriteControllerStub)
    monkeypatch.setattr(fatura_module, "CategoryController", CategoryControllerStub)
    monkeypatch.setattr(fatura_module, "CategoriaDialog", CategoryDialogStub)

    dialog = fatura_module.FaturaDialog(id_cartao=4)
    dialog.btn_add_cat.click()

    assert dialog.categoria_combo.currentData() == 7
    assert dialog.categoria_combo.currentText() == "Saúde"
    dialog.close()
