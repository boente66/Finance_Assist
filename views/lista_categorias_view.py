import logging

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMenu,
    QAction,
    QDialog,
    QMessageBox,
    QApplication,
    QLineEdit,
    QComboBox,
)
from PyQt5.QtCore import Qt

from controllers.category_controller import CategoryController
from views.categoria_dialog import CategoriaDialog
from views.subcategoria_dialog import SubcategoriaDialog

from core.translator_app import TranslatorApp
from views.responsive_layout import FlowLayout

logging.basicConfig(level=logging.ERROR)


class ListaCategoriasView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = CategoryController()

        # 🔥 título base
        self.setWindowTitle("Listas e Categorias")

        self.resize(600, 400)

        self._init_ui()
        
        self.load_categorias()
       
        # 🔥 tradução automática global
        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Listas e Categorias")
        )

        self.title.setText(
            TranslatorApp.get("Categorias")
        )
        self.subtitle.setText(
            TranslatorApp.get("Organize receitas e despesas por grupos e subcategorias")
        )

        self.btn_nova.setText(
            TranslatorApp.get("Nova Categoria")
        )

        self.btn_sub.setText(
            TranslatorApp.get("Nova Subcategoria")
        )

        self.btn_excluir.setText(
            TranslatorApp.get("Excluir")
        )
        self.search_input.setPlaceholderText(
            TranslatorApp.get("Buscar categoria")
        )
        self.type_filter.setItemText(0, TranslatorApp.get("Todas"))
        self.type_filter.setItemText(1, TranslatorApp.get("Receita"))
        self.type_filter.setItemText(2, TranslatorApp.get("Despesa"))

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ---------------- TÍTULO ----------------
        self.title = QLabel("Listas e Categorias")
        self.title.setObjectName("pageTitle")
        layout.addWidget(self.title)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")
        layout.addWidget(self.subtitle)

        # ---------------- BOTÕES ----------------
        buttons = FlowLayout(horizontal_spacing=8, vertical_spacing=8)

        self.btn_nova = QPushButton("Nova Categoria")
        self.btn_sub = QPushButton("Nova Subcategoria")
        self.btn_excluir = QPushButton("Excluir")
        self.btn_sub.setObjectName("secondaryButton")
        self.btn_excluir.setObjectName("dangerButton")

        self.btn_nova.clicked.connect(self.add_categoria_dialog)
        self.btn_sub.clicked.connect(self.add_subcategoria_dialog)
        self.btn_excluir.clicked.connect(self.excluir_categoria)

        buttons.addWidget(self.btn_nova)
        buttons.addWidget(self.btn_sub)
        buttons.addWidget(self.btn_excluir)

        layout.addLayout(buttons)

        filters = FlowLayout(horizontal_spacing=8, vertical_spacing=8)
        self.search_input = QLineEdit()
        self.search_input.setMinimumWidth(240)
        self.type_filter = QComboBox()
        self.type_filter.addItem("Todas", None)
        self.type_filter.addItem("Receita", "Receita")
        self.type_filter.addItem("Despesa", "Despesa")
        self.search_input.textChanged.connect(self.apply_filter)
        self.type_filter.currentIndexChanged.connect(self.apply_filter)
        filters.addWidget(self.search_input)
        filters.addWidget(self.type_filter)
        layout.addLayout(filters)

        # ---------------- TABELA ----------------
        self.table = QTableWidget()
        self.table.setColumnCount(3)

        self.table.setHorizontalHeaderLabels([
            "Categoria",
            "Tipo",
            "ID"
        ])

        self.table.setColumnHidden(2, True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

    # ==================================================
    # CARREGAR
    # ==================================================
    def load_categorias(self):
        try:
            self.table.setRowCount(0)

            categorias = self.controller.get_all_categories()
            self._categorias = categorias or []

            if not categorias:
                self.table.setRowCount(1)
                self.table.setItem(
                    0, 0,
                    QTableWidgetItem(
                        TranslatorApp.get("Nenhum registro encontrado")
                    )
                )
                self.table.setSpan(0, 0, 1, 3)
                return

            self._popular_tabela(categorias)

        except Exception as e:
            logging.error(e)
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                f"{TranslatorApp.get('Erro ao carregar categorias')}:\n{e}",
            )

    def apply_filter(self, *_):
        categorias = getattr(self, "_categorias", [])
        termo = self.search_input.text().strip().casefold()
        tipo = self.type_filter.currentData()
        ids = {
            c["ID_Categoria"] for c in categorias
            if (not tipo or c.get("Tipo") == tipo)
            and (not termo or termo in (c.get("Nome") or "").casefold())
        }
        # Mantém o contexto hierárquico dos resultados filhos.
        parents = {c["ID_Categoria"]: c.get("ID_Categoria_Pai") for c in categorias}
        for category_id in tuple(ids):
            parent_id = parents.get(category_id)
            while parent_id:
                ids.add(parent_id)
                parent_id = parents.get(parent_id)
        self.table.setRowCount(0)
        self._popular_tabela(categorias, allowed_ids=ids)

    # ==================================================
    # POPULAR TABELA
    # ==================================================
    def _popular_tabela(self, categorias, pai_id=None, indent="", allowed_ids=None):

        for categoria in categorias:

            if categoria["ID_Categoria_Pai"] == pai_id and (
                allowed_ids is None or categoria["ID_Categoria"] in allowed_ids
            ):

                row = self.table.rowCount()
                self.table.insertRow(row)

                item_nome = QTableWidgetItem(indent + categoria["Nome"])
                self.table.setItem(row, 0, item_nome)

                self.table.setItem(
                    row, 1,
                    QTableWidgetItem(categoria["Tipo"])
                )

                id_item = QTableWidgetItem(str(categoria["ID_Categoria"]))
                id_item.setData(Qt.UserRole, categoria["ID_Categoria"])
                self.table.setItem(row, 2, id_item)

                self._popular_tabela(
                    categorias,
                    categoria["ID_Categoria"],
                    indent + "    └ ",
                    allowed_ids,
                )

    # ==================================================
    # NOVA CATEGORIA
    # ==================================================
    def add_categoria_dialog(self):

        dialog = CategoriaDialog(self)

        if dialog.exec_() == QDialog.Accepted:

            data = dialog.get_data()

            try:
                self.controller.add_category(
                    data["Nome"],
                    data["Tipo"]
                )
                self.load_categorias()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    TranslatorApp.get("Erro"),
                    str(e)
                )

    # ==================================================
    # NOVA SUBCATEGORIA
    # ==================================================
    def add_subcategoria_dialog(self):

        dialog = SubcategoriaDialog(
            parent=self,
            controller=self.controller,
            categoria_pai_id=None
        )

        if dialog.exec_() == QDialog.Accepted:

            data = dialog.get_data()

            try:
                categoria_pai = self.controller.get_category_by_id(
                    data["ID_Categoria_Pai"]
                )

                if not categoria_pai:
                    QMessageBox.warning(
                        self,
                        TranslatorApp.get("Erro"),
                        TranslatorApp.get("Categoria pai não encontrada"),
                    )
                    return

                tipo = categoria_pai["Tipo"]

                self.controller.add_subcategory(
                    data["Nome"],
                    tipo,
                    data["ID_Categoria_Pai"]
                )

                self.load_categorias()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    TranslatorApp.get("Erro"),
                    str(e)
                )

    # ==================================================
    # EXCLUIR
    # ==================================================
    def excluir_categoria(self):

        row = self.table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Selecione uma categoria"),
            )
            return

        item_id = self.table.item(row, 2)

        if not item_id:
            return

        categoria_id = item_id.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self,
            TranslatorApp.get("Confirmar Exclusão"),
            TranslatorApp.get("Deseja realmente excluir esta categoria?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            ok, msg = self.controller.delete_category(categoria_id)

            if not ok:
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Aviso"),
                    msg
                )
            else:
                self.load_categorias()

        except Exception as e:
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                str(e)
            )

    # ==================================================
    # MENU CONTEXTO
    # ==================================================
    def show_context_menu(self, position):

        if self.table.currentRow() < 0:
            return

        menu = QMenu(self)

        copiar = QAction("Copiar", self)
        editar = QAction("Editar", self)
        excluir = QAction("Excluir", self)

        copiar.triggered.connect(self.copiar_categoria)
        editar.triggered.connect(self.editar_categoria)
        excluir.triggered.connect(self.excluir_categoria)

        menu.addAction(copiar)
        menu.addAction(editar)
        menu.addAction(excluir)

        menu.exec_(self.table.viewport().mapToGlobal(position))

    # ==================================================
    # COPIAR
    # ==================================================
    def copiar_categoria(self):

        item = self.table.currentItem()

        if item:
            QApplication.clipboard().setText(
                item.text().replace("└ ", "").strip()
            )

    # ==================================================
    # EDITAR
    # ==================================================
    def editar_categoria(self):

        row = self.table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Selecione uma categoria"),
            )
            return

        item_id = self.table.item(row, 2)

        if not item_id:
            return

        categoria_id = item_id.data(Qt.UserRole)

        nome = self.table.item(row, 0).text().replace("└ ", "").strip()
        tipo = self.table.item(row, 1).text()

        dialog = CategoriaDialog(self, nome=nome, tipo=tipo)

        if dialog.exec_() == QDialog.Accepted:

            data = dialog.get_data()

            try:
                self.controller.update_category(
                    categoria_id,
                    data["Nome"],
                    data["Tipo"]
                )
                self.load_categorias()

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
