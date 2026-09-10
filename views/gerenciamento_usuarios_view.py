# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from controllers.user_controller import UserController
from views.cadastro_usuario_dialog import CadastroUsuarioDialog
from core.translator_app import TranslatorApp


class GerenciamentoUsuariosView(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.usuario_controller = UserController()
        self.lista_completa = []

        self.setWindowTitle("Gerenciamento de Usuários")

        self._init_ui()
        self._connect_events()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self.atualizar_tabela()

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        search_layout = QtWidgets.QHBoxLayout()

        self.lbl_search = QtWidgets.QLabel()
        self.search_input = QtWidgets.QLineEdit()

        search_layout.addWidget(self.lbl_search)
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_add = QtWidgets.QPushButton()
        self.btn_add.setObjectName("primaryButton")

        self.btn_edit = QtWidgets.QPushButton()
        self.btn_edit.setObjectName("menuButton")

        self.btn_delete = QtWidgets.QPushButton()
        self.btn_delete.setObjectName("deleteButton")

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)

    # ==================================================
    # EVENTOS
    # ==================================================
    def _connect_events(self):
        self.search_input.textChanged.connect(
            self.aplicar_filtro_pesquisa
        )

        self.btn_add.clicked.connect(self.adicionar_usuario)
        self.btn_edit.clicked.connect(self.editar_usuario)
        self.btn_delete.clicked.connect(self.excluir_usuario)

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self):
        self.setWindowTitle(
            TranslatorApp.get("Gerenciamento de Usuários")
        )

        self.lbl_search.setText(
            TranslatorApp.get("Pesquisar:")
        )

        self.search_input.setPlaceholderText(
            TranslatorApp.get("Nome, e-mail ou nível")
        )

        self.btn_add.setText(
            TranslatorApp.get("Adicionar")
        )

        self.btn_edit.setText(
            TranslatorApp.get("Editar")
        )

        self.btn_delete.setText(
            TranslatorApp.get("Excluir")
        )

        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("ID"),
            TranslatorApp.get("Nome"),
            TranslatorApp.get("Email"),
            TranslatorApp.get("Administrador"),
            TranslatorApp.get("Status"),
        ])

        self.preencher_tabela(self.lista_completa)

    # ==================================================
    # CARREGAMENTO
    # ==================================================
    def atualizar_tabela(self):
        self.lista_completa = (
            self.usuario_controller.get_all_users() or []
        )

        self.preencher_tabela(self.lista_completa)

    def preencher_tabela(self, usuarios):
        self.table.setRowCount(0)

        for row, user in enumerate(usuarios):
            self.table.insertRow(row)

            self.table.setItem(
                row,
                0,
                QtWidgets.QTableWidgetItem(
                    str(user.get("ID_Usuario", ""))
                )
            )

            self.table.setItem(
                row,
                1,
                QtWidgets.QTableWidgetItem(
                    user.get("Nome", "")
                )
            )

            self.table.setItem(
                row,
                2,
                QtWidgets.QTableWidgetItem(
                    user.get("Email", "")
                )
            )

            admin = (
                TranslatorApp.get("Sim")
                if user.get("Nivel_Acesso") == "admin"
                else TranslatorApp.get("Não")
            )

            self.table.setItem(
                row,
                3,
                QtWidgets.QTableWidgetItem(admin)
            )
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(
                TranslatorApp.get('Ativo' if user.get('Ativo', 1) else 'Encerrado')))

        self.table.resizeColumnsToContents()

    # ==================================================
    # FILTRO
    # ==================================================
    def aplicar_filtro_pesquisa(self):
        termo = self.search_input.text().lower().strip()

        if not termo:
            self.preencher_tabela(self.lista_completa)
            return

        filtrados = []

        for user in self.lista_completa:
            texto = " ".join([
                str(user.get("ID_Usuario", "")),
                str(user.get("Nome", "")),
                str(user.get("Email", "")),
                str(user.get("Nivel_Acesso", "")),
            ]).lower()

            if termo in texto:
                filtrados.append(user)

        self.preencher_tabela(filtrados)

    # ==================================================
    # CRUD
    # ==================================================
    def adicionar_usuario(self):
        dialog = CadastroUsuarioDialog(self)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.atualizar_tabela()

    def editar_usuario(self):
        row = self.table.currentRow()

        if row < 0:
            QtWidgets.QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Selecione um usuário")
            )
            return

        user_id = int(self.table.item(row, 0).text())

        usuario = self.usuario_controller.get_user_by_id(user_id)

        if not usuario:
            QtWidgets.QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Usuário não encontrado")
            )
            return

        dialog = CadastroUsuarioDialog(self)
        dialog.preencher_dados(usuario)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.atualizar_tabela()

    def excluir_usuario(self):
        row = self.table.currentRow()

        if row < 0:
            QtWidgets.QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Selecione um usuário")
            )
            return

        user_id = int(self.table.item(row, 0).text())

        confirm = QtWidgets.QMessageBox.question(
            self,
            TranslatorApp.get("Confirmar Exclusão"),
            TranslatorApp.get("Deseja realmente excluir este usuário?"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if confirm != QtWidgets.QMessageBox.Yes:
            return

        if not self.usuario_controller.delete_user(user_id):
            QtWidgets.QMessageBox.critical(
                self,
                TranslatorApp.get("Restrição"),
                TranslatorApp.get(
                    "Não é possível excluir o único administrador restante"
                )
            )
            return

        self.atualizar_tabela()

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
