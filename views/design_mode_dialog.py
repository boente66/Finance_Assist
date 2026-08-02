# -*- coding: utf-8 -*-
"""Editor seguro de temas personalizados com pré-visualização local."""

from copy import deepcopy

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSplitter,
    QScrollArea, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from views.responsive_layout import FlowLayout


class DesignModeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(720, 520)
        self.config = ThemeManager.load_custom_theme() or ThemeManager.get_theme_config("Primavera")
        self.config["nome"] = self.config.get("nome") or "Meu Tema"
        self.config["base"] = "PERSONALIZADO"
        self.color_buttons = {}
        self._build_ui()
        self._refresh_controls()
        self._update_preview()

    def _t(self, text):
        return TranslatorApp.get(text)

    def _build_ui(self):
        self.setWindowTitle(self._t("Modo Design"))
        root = QVBoxLayout(self)
        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        properties = QWidget()
        form = QFormLayout(properties)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._changed)
        form.addRow(self._t("Nome do tema"), self.name_edit)

        self.component_combo = QComboBox()
        for item in ("Todos", "Menu lateral", "Card", "Botões", "Campos", "Tabela", "Status", "Paginação"):
            self.component_combo.addItem(self._t(item))
        form.addRow(self._t("Componente"), self.component_combo)

        color_labels = {
            "background": "Fundo principal", "surface": "Superfície dos cards",
            "surface_alt": "Superfície alternativa", "sidebar": "Menu lateral",
            "sidebar_active": "Item ativo", "primary": "Cor principal",
            "primary_hover": "Cor principal ao passar o mouse", "secondary": "Cor secundária",
            "text_primary": "Texto principal", "text_secondary": "Texto secundário",
            "border": "Bordas", "success": "Sucesso", "danger": "Perigo",
            "warning": "Aviso", "info": "Informação", "table_header": "Cabeçalho da tabela",
            "table_alternate": "Linha alternada", "input_background": "Campos de entrada",
            "disabled_background": "Fundo desabilitado", "disabled_text": "Texto desabilitado",
            "button_background": "Fundo de botões", "focus": "Cor de foco",
            "selection": "Cor de seleção",
        }
        for token in sorted(self.config["cores"]):
            button = QPushButton()
            button.clicked.connect(lambda _=False, key=token: self._pick_color(key))
            self.color_buttons[token] = button
            form.addRow(self._t(color_labels[token]), button)

        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.addItems(ThemeManager.SAFE_FONTS)
        self.font_combo.currentTextChanged.connect(self._changed)
        form.addRow(self._t("Família da fonte"), self.font_combo)

        self.spin_controls = {}
        numeric = (
            ("base_size", "Tamanho base", "fontes", 8, 24),
            ("title_size", "Tamanho de títulos", "fontes", 12, 36),
            ("subtitle_size", "Tamanho de subtítulos", "fontes", 8, 24),
            ("table_size", "Tamanho de tabelas", "fontes", 8, 24),
            ("weight", "Peso da fonte", "fontes", 300, 800),
            ("radius", "Raio das bordas", "layout", 0, 24),
            ("shadow", "Intensidade de sombra", "layout", 0, 10),
            ("padding", "Espaçamento interno", "layout", 4, 30),
            ("button_height", "Altura dos botões", "layout", 28, 64),
            ("field_height", "Altura dos campos", "layout", 28, 64),
            ("table_row_height", "Altura das linhas", "layout", 28, 72),
            ("sidebar_width", "Largura do menu", "layout", 190, 360),
            ("divider_contrast", "Contraste de divisores", "layout", 0, 100),
        )
        for key, label, group, minimum, maximum in numeric:
            spin = QSpinBox()
            spin.setRange(minimum, maximum)
            spin.valueChanged.connect(self._changed)
            spin.setProperty("configGroup", group)
            self.spin_controls[key] = spin
            form.addRow(self._t(label), spin)

        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(1.0, 2.0)
        self.line_spacing_spin.setSingleStep(0.05)
        self.line_spacing_spin.valueChanged.connect(self._changed)
        form.addRow(self._t("Espaçamento entre linhas"), self.line_spacing_spin)

        self.density_combo = QComboBox()
        for label, value in (("Compacta", "compacta"), ("Confortável", "confortavel"), ("Ampla", "ampla")):
            self.density_combo.addItem(self._t(label), value)
        self.density_combo.currentIndexChanged.connect(self._changed)
        form.addRow(self._t("Densidade da interface"), self.density_combo)

        scroll.setWidget(properties)
        body.addWidget(scroll)
        self.preview = self._build_preview()
        body.addWidget(self.preview)
        body.setStretchFactor(0, 2)
        body.setStretchFactor(1, 3)
        body.setSizes([380, 600])
        root.addWidget(body, 1)

        actions = FlowLayout(horizontal_spacing=8, vertical_spacing=8)
        self.import_btn = QPushButton(self._t("Importar"))
        self.export_btn = QPushButton(self._t("Exportar"))
        self.restore_btn = QPushButton(self._t("Restaurar"))
        self.cancel_btn = QPushButton(self._t("Cancelar"))
        self.save_as_btn = QPushButton(self._t("Salvar como novo tema"))
        self.save_btn = QPushButton(self._t("Salvar"))
        self.apply_btn = QPushButton(self._t("Aplicar"))
        self.import_btn.clicked.connect(self._import)
        self.export_btn.clicked.connect(self._export)
        self.restore_btn.clicked.connect(self._restore)
        self.cancel_btn.clicked.connect(self.reject)
        self.save_as_btn.clicked.connect(self._save)
        self.save_btn.clicked.connect(self._save)
        self.apply_btn.clicked.connect(self._apply)
        for button in (self.import_btn, self.export_btn, self.restore_btn):
            button.setObjectName("secondaryButton")
            actions.addWidget(button)
        actions.addWidget(self.cancel_btn)
        actions.addWidget(self.save_as_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.apply_btn)
        root.addLayout(actions)

    def _build_preview(self):
        def named(widget, name):
            widget.setObjectName(name)
            return widget

        panel = QFrame()
        panel.setObjectName("surface")
        layout = QVBoxLayout(panel)
        title = QLabel(self._t("Pré-visualização"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        row = QHBoxLayout()
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        side = QVBoxLayout(sidebar)
        brand = QLabel(self._t("Controle Financeiro"))
        brand.setObjectName("brandTitle")
        active = QPushButton(self._t("Resumo Financeiro"))
        active.setObjectName("menuButton")
        active.setProperty("active", True)
        side.addWidget(brand)
        side.addWidget(active)
        side.addWidget(named(QPushButton(self._t("Relatórios")), "menuButton"))
        side.addStretch()
        row.addWidget(sidebar)

        content = QVBoxLayout()
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(named(QLabel(self._t("Saldo atual")), "cardTitle"))
        card_layout.addWidget(named(QLabel("R$ 2.741,22"), "cardValue"))
        content.addWidget(card)
        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton(self._t("Principal")))
        buttons.addWidget(named(QPushButton(self._t("Secundário")), "secondaryButton"))
        buttons.addWidget(named(QPushButton(self._t("Excluir")), "dangerButton"))
        content.addLayout(buttons)
        content.addWidget(QLineEdit(self._t("Campo de texto")))
        combo = QComboBox()
        combo.addItems([self._t("Combo"), self._t("Opção")])
        content.addWidget(combo)
        table = QTableWidget(2, 2)
        table.setHorizontalHeaderLabels([self._t("Descrição"), self._t("Valor")])
        table.setItem(0, 0, QTableWidgetItem(self._t("Receita")))
        table.setItem(0, 1, QTableWidgetItem("R$ 100,00"))
        table.setItem(1, 0, QTableWidgetItem(self._t("Despesa")))
        table.setItem(1, 1, QTableWidgetItem("R$ 20,00"))
        content.addWidget(table)
        statuses = QHBoxLayout()
        statuses.addWidget(named(QLabel(self._t("Positivo")), "positivo"))
        statuses.addWidget(named(QLabel(self._t("Negativo")), "negativo"))
        statuses.addWidget(named(QLabel(self._t("Alerta")), "warning"))
        statuses.addStretch()
        statuses.addWidget(named(QPushButton("‹"), "secondaryButton"))
        statuses.addWidget(QLabel("1 / 3"))
        statuses.addWidget(named(QPushButton("›"), "secondaryButton"))
        content.addLayout(statuses)
        row.addLayout(content)
        layout.addLayout(row)
        return panel

    def _refresh_controls(self):
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.config["nome"])
        self.name_edit.blockSignals(False)
        self.font_combo.blockSignals(True)
        self.font_combo.setCurrentText(self.config["fontes"]["family"])
        self.font_combo.blockSignals(False)
        self.line_spacing_spin.blockSignals(True)
        self.line_spacing_spin.setValue(float(self.config["fontes"]["line_spacing"]))
        self.line_spacing_spin.blockSignals(False)
        self.density_combo.blockSignals(True)
        density_index = self.density_combo.findData(self.config["layout"]["density"])
        self.density_combo.setCurrentIndex(max(0, density_index))
        self.density_combo.blockSignals(False)
        for key, button in self.color_buttons.items():
            color = self.config["cores"][key]
            button.setText(color.upper())
            button.setStyleSheet(f"background:{color}; color:{'#000' if QColor(color).lightness() > 145 else '#fff'}")
        for key, spin in self.spin_controls.items():
            group = spin.property("configGroup")
            spin.blockSignals(True)
            spin.setValue(int(self.config[group][key]))
            spin.blockSignals(False)

    def _pick_color(self, token):
        color = QColorDialog.getColor(QColor(self.config["cores"][token]), self)
        if color.isValid():
            self.config["cores"][token] = color.name()
            self._refresh_controls()
            self._update_preview()

    def _changed(self, *_):
        if not hasattr(self, "preview"):
            return
        self.config["nome"] = self.name_edit.text().strip() or "Meu Tema"
        self.config["fontes"]["family"] = self.font_combo.currentText().strip() or "Sans Serif"
        self.config["fontes"]["line_spacing"] = self.line_spacing_spin.value()
        self.config["layout"]["density"] = self.density_combo.currentData()
        for key, spin in self.spin_controls.items():
            self.config[spin.property("configGroup")][key] = spin.value()
        self._update_preview()

    def _update_preview(self):
        try:
            self.preview.setStyleSheet(ThemeManager.preview_theme(self.config))
            self.apply_btn.setEnabled(True)
        except ValueError as exc:
            self.apply_btn.setEnabled(False)
            self.apply_btn.setToolTip(str(exc))

    def _save(self):
        try:
            self.config = ThemeManager.save_custom_theme(self.config)
            QMessageBox.information(self, self._t("Tema"), self._t("Tema salvo com sucesso."))
        except ValueError as exc:
            QMessageBox.warning(self, self._t("Contraste insuficiente"), str(exc))

    def _apply(self):
        try:
            self.config = ThemeManager.save_custom_theme(self.config)
            ThemeManager.definir_tema("Personalizado", QApplication.instance())
            ThemeManager.cancel_preview()
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, self._t("Contraste insuficiente"), str(exc))

    def _restore(self):
        self.config = ThemeManager.get_theme_config("Primavera")
        self.config["nome"] = "Meu Tema"
        self.config["base"] = "PERSONALIZADO"
        self._refresh_controls()
        self._update_preview()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, self._t("Importar tema"), "", "JSON (*.json)")
        if not path:
            return
        try:
            self.config = ThemeManager.import_theme(path)
            self._refresh_controls()
            self._update_preview()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, self._t("Tema inválido"), str(exc))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, self._t("Exportar tema"), "tema.json", "JSON (*.json)")
        if not path:
            return
        try:
            ThemeManager.save_custom_theme(self.config)
            ThemeManager.export_theme(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, self._t("Erro"), str(exc))

    def reject(self):
        ThemeManager.cancel_preview()
        super().reject()
