# -*- coding: utf-8 -*-

import unicodedata

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QDialog,
    QAbstractItemView,
    QComboBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from views.FavorecidoDialog import FavorecidoDialog
from controllers.favorecido_controller import FavorecidoController
from utilitarios.ion_path import IonPath
from core.translator_app import TranslatorApp


class FavorecidoView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = FavorecidoController()

        self.setMinimumSize(820, 600)

        self.data_original = []
        self.data_filtrada = []

        self.state = {
            "busca": "",
            "tipo": "ALL",
            "ordem": "AZ",
        }

        self.search_timer = QTimer()
        self.search_timer.setInterval(300)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)

        self._init_ui()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self.load_favorecidos()

    # =====================================================
    # UI
    # =====================================================
    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        main_layout.addWidget(self.title_label)
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("pageSubtitle")
        main_layout.addWidget(self.subtitle_label)

        button_layout = QHBoxLayout()

        self.add_btn = self._create_button(
            "Adicionar",
            "add",
            self.open_add_favorecido_dialog,
            "primaryButton",
        )

        self.edit_btn = self._create_button(
            "Editar",
            "edit",
            self.edit_favorecido,
            "primaryButton",
        )

        self.delete_btn = self._create_button(
            "Excluir",
            "delete",
            self.delete_favorecido,
            "deleteButton",
        )

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        filtro_layout = QHBoxLayout()

        self.search_label = QLabel()
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self._on_busca_change)

        self.tipo_label = QLabel()

        self.tipo_filtro = QComboBox()
        self.tipo_filtro.addItem("Todos", "ALL")
        self.tipo_filtro.addItem("Pessoa Física", "PF")
        self.tipo_filtro.addItem("Pessoa Jurídica", "PJ")
        self.tipo_filtro.currentIndexChanged.connect(self._on_tipo_change)

        filtro_layout.addWidget(self.search_label)
        filtro_layout.addWidget(self.search_input)
        filtro_layout.addWidget(self.tipo_label)
        filtro_layout.addWidget(self.tipo_filtro)

        main_layout.addLayout(filtro_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_favorecido)

        main_layout.addWidget(self.table)

    def _create_button(self, texto, icon, fn, style):
        btn = QPushButton()
        btn.setObjectName(style)
        btn.setIcon(self._icon(icon))
        btn.clicked.connect(fn)
        btn._texto_base = texto
        return btn

    # =====================================================
    # TRADUÇÃO
    # =====================================================
    def _atualizar_textos(self):
        self.setWindowTitle(
            TranslatorApp.get("Favorecidos")
        )

        self.title_label.setText(
            TranslatorApp.get("Favorecidos")
        )
        self.subtitle_label.setText(
            TranslatorApp.get("Gerencie pessoas e empresas vinculadas às transações")
        )

        self.add_btn.setText(
            TranslatorApp.get("Adicionar")
        )

        self.edit_btn.setText(
            TranslatorApp.get("Editar")
        )

        self.delete_btn.setText(
            TranslatorApp.get("Excluir")
        )

        self.search_label.setText(
            TranslatorApp.get("Buscar:")
        )

        self.search_input.setPlaceholderText(
            TranslatorApp.get("Nome, tipo, CPF/CNPJ, contato...")
        )

        self.tipo_label.setText(
            TranslatorApp.get("Tipo:")
        )

        self._atualizar_combo_tipo()

        self.table.setHorizontalHeaderLabels([
            TranslatorApp.get("Nome"),
            TranslatorApp.get("Tipo"),
            TranslatorApp.get("CPF/CNPJ"),
            TranslatorApp.get("Contato"),
        ])

    def _atualizar_combo_tipo(self):
        atual = self.tipo_filtro.currentData()

        self.tipo_filtro.blockSignals(True)
        self.tipo_filtro.clear()

        self.tipo_filtro.addItem(
            TranslatorApp.get("Todos"),
            "ALL"
        )

        self.tipo_filtro.addItem(
            TranslatorApp.get("Pessoa Física"),
            "PF"
        )

        self.tipo_filtro.addItem(
            TranslatorApp.get("Pessoa Jurídica"),
            "PJ"
        )

        index = self.tipo_filtro.findData(atual)

        if index >= 0:
            self.tipo_filtro.setCurrentIndex(index)

        self.tipo_filtro.blockSignals(False)

    # =====================================================
    # ICON
    # =====================================================
    def _icon(self, nome: str):
        caminho = IonPath.resource(
            "assets",
            "icons",
            f"{nome}.svg"
        )
        return QIcon(caminho)

    # =====================================================
    # NORMALIZAÇÃO
    # =====================================================
    def normalize(self, text):
        if not text:
            return ""

        text = str(text).lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(
            c for c in text
            if unicodedata.category(c) != "Mn"
        )

        return text.replace(" ", "")

    def _tipo_exibicao(self, tipo):
        if tipo == "PF":
            return TranslatorApp.get("Pessoa Física")

        if tipo == "PJ":
            return TranslatorApp.get("Pessoa Jurídica")

        return TranslatorApp.get(str(tipo or ""))

    # =====================================================
    # LOAD
    # =====================================================
    def load_favorecidos(self):
        self.data_original = (
            self.controller.listar_favorecidos()
            or []
        )
        self.apply_filter()

    # =====================================================
    # FILTRO
    # =====================================================
    def apply_filter(self):
        termo = self.normalize(self.state["busca"])
        tipo_filtro = self.state["tipo"]
        ordem = self.state["ordem"]

        filtrados = []

        for fav in self.data_original:
            nome = fav.get("Nome", "")
            tipo = fav.get("Tipo", "")
            doc = (
                fav.get("CPF")
                or fav.get("CNPJ")
                or fav.get("Documento")
                or ""
            )
            tel = (
                fav.get("Telefone")
                or fav.get("Telefone_PF")
                or fav.get("Telefone_PJ")
                or ""
            )

            texto = self.normalize(
                f"{nome}{tipo}{doc}{tel}"
            )

            if termo and termo not in texto:
                continue

            if tipo_filtro != "ALL" and tipo != tipo_filtro:
                continue

            filtrados.append(fav)

        if ordem == "AZ":
            filtrados.sort(
                key=lambda x: self.normalize(
                    x.get("Nome", "")
                )
            )

        elif ordem == "ZA":
            filtrados.sort(
                key=lambda x: self.normalize(
                    x.get("Nome", "")
                ),
                reverse=True,
            )

        self.data_filtrada = filtrados
        self._render_table()

    # =====================================================
    # RENDER
    # =====================================================
    def _render_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        if not self.data_filtrada:
            self.table.setRowCount(1)

            item = QTableWidgetItem(
                TranslatorApp.get("Nenhum registro encontrado")
            )

            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 4)

            self.table.setSortingEnabled(True)
            return

        for row, fav in enumerate(self.data_filtrada):
            self.table.insertRow(row)

            tipo = fav.get("Tipo", "")
            icone = "👤" if tipo == "PF" else "🏢"

            doc = (
                fav.get("CPF")
                or fav.get("CNPJ")
                or fav.get("Documento")
                or ""
            )

            telefone = (
                fav.get("Telefone")
                or fav.get("Telefone_PF")
                or fav.get("Telefone_PJ")
                or ""
            )

            nome_item = QTableWidgetItem(
                f"{icone} {fav.get('Nome', '')}"
            )
            nome_item.setData(
                Qt.UserRole,
                fav.get("ID_Favorecido")
            )

            self.table.setItem(row, 0, nome_item)
            self.table.setItem(
                row,
                1,
                QTableWidgetItem(
                    self._tipo_exibicao(tipo)
                )
            )
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(str(doc))
            )
            self.table.setItem(
                row,
                3,
                QTableWidgetItem(str(telefone))
            )

        self.table.setSortingEnabled(True)

    # =====================================================
    # SELEÇÃO
    # =====================================================
    def get_selected_favorecido(self):
        row = self.table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Nenhum favorecido selecionado."),
            )
            return None

        item = self.table.item(row, 0)

        if not item:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Nenhum favorecido selecionado."),
            )
            return None

        id_fav = item.data(Qt.UserRole)

        if not id_fav:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Aviso"),
                TranslatorApp.get("Nenhum favorecido selecionado."),
            )
            return None

        return {
            "ID_Favorecido": id_fav
        }

    # =====================================================
    # AÇÕES
    # =====================================================
    def open_add_favorecido_dialog(self):
        dialog = FavorecidoDialog(parent=self)

        if dialog.exec_() == QDialog.Accepted:
            self.load_favorecidos()

    def edit_favorecido(self):
        selecionado = self.get_selected_favorecido()

        if not selecionado:
            return

        dialog = FavorecidoDialog(
            parent=self,
            favorecido=selecionado
        )

        if dialog.exec_() == QDialog.Accepted:
            self.load_favorecidos()

    def delete_favorecido(self):
        selecionado = self.get_selected_favorecido()

        if not selecionado:
            return

        confirm = QMessageBox.question(
            self,
            TranslatorApp.get("Confirmar Exclusão"),
            TranslatorApp.get("Deseja realmente excluir este favorecido?"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            sucesso = self.controller.remover_favorecido(
                selecionado["ID_Favorecido"]
            )

            if sucesso:
                self.load_favorecidos()
            else:
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Erro"),
                    TranslatorApp.get(
                        "Não foi possível excluir o favorecido."
                    ),
                )

    # =====================================================
    # STATE
    # =====================================================
    def _on_busca_change(self):
        self.state["busca"] = self.search_input.text()
        self.search_timer.start()

    def _on_tipo_change(self):
        self.state["tipo"] = self.tipo_filtro.currentData()
        self.apply_filter()

    # =====================================================
    # CICLO DE VIDA
    # =====================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
