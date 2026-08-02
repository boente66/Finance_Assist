# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QProgressBar,
    QMessageBox,
)
from PyQt5.QtCore import Qt

from controllers.meta_controller import MetaController
from views.meta_dialog import MetaDialog

from utilitarios.currency_formatter import CurrencyFormatter
from core.translator_app import TranslatorApp

logger = logging.getLogger(__name__)


class MetaView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = MetaController()

        self.setWindowTitle("Metas Financeiras")

        self._init_ui()
        self._connect_events()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

        self.carregar_metas()

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):
        self.layout_principal = QVBoxLayout(self)

        self.titulo = QLabel()
        self.titulo.setObjectName("pageTitle")
        self.layout_principal.addWidget(self.titulo)
        self.subtitulo = QLabel()
        self.subtitulo.setObjectName("pageSubtitle")
        self.layout_principal.addWidget(self.subtitulo)

        self.btn_nova = QPushButton()
        self.btn_nova.setObjectName("addButton")

        self.layout_principal.addWidget(self.btn_nova)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)

        self.scroll.setWidget(self.container)
        self.layout_principal.addWidget(self.scroll)

        self.layout_principal.addStretch()

    # ==================================================
    # EVENTOS
    # ==================================================
    def _connect_events(self):
        self.btn_nova.clicked.connect(
            self._nova_meta
        )

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Metas Financeiras")
        )

        self.titulo.setText(
            TranslatorApp.get("Metas Financeiras")
        )
        self.subtitulo.setText(
            TranslatorApp.get("Acompanhe objetivos, prazos e valores acumulados")
        )

        self.btn_nova.setText(
            TranslatorApp.get("Nova Meta")
        )

        self.carregar_metas()

    # ==================================================
    # LIMPAR CONTAINER
    # ==================================================
    def _limpar_container(self):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

            layout = item.layout()

            if layout:
                self._limpar_layout(layout)

    def _limpar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

            child_layout = item.layout()

            if child_layout:
                self._limpar_layout(child_layout)

    # ==================================================
    # CARREGAR METAS
    # ==================================================
    def carregar_metas(self):
        self._limpar_container()

        try:
            metas = self.controller.listar_metas_ativas() or []

        except Exception:
            logger.exception("Erro ao carregar metas")

            label = QLabel(
                TranslatorApp.get("Erro ao carregar metas.")
            )
            self.container_layout.addWidget(label)
            self.container_layout.addStretch()
            return

        if not metas:
            label = QLabel(
                TranslatorApp.get("Nenhuma meta cadastrada")
            )
            label.setAlignment(Qt.AlignCenter)

            self.container_layout.addWidget(label)
            self.container_layout.addStretch()
            return

        for meta in metas:
            card = self._criar_card(meta)
            self.container_layout.addWidget(card)

        self.container_layout.addStretch()

    # ==================================================
    # CARD
    # ==================================================
    def _criar_card(self, meta):
        frame = QFrame()
        frame.setObjectName("metaCard")
        frame.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(frame)

        nome = QLabel(
            meta.get("Nome", "")
        )
        nome.setObjectName("title")
        layout.addWidget(nome)

        progresso = meta.get("Progresso") or {}

        valor_atual = float(
            progresso.get("valor_atual", 0) or 0
        )
        valor_alvo = float(
            progresso.get("valor_alvo", 0) or 0
        )
        percentual = float(
            progresso.get("percentual", 0) or 0
        )
        restante = float(
            progresso.get("restante", 0) or 0
        )

        valor_texto = QLabel(
            f"{CurrencyFormatter.format(valor_atual)} / "
            f"{CurrencyFormatter.format(valor_alvo)}"
        )
        layout.addWidget(valor_texto)

        progress_bar = QProgressBar()
        progress_bar.setValue(
            min(int(percentual), 100)
        )
        layout.addWidget(progress_bar)

        restante_label = QLabel(
            f"{TranslatorApp.get('Restante')}: "
            f"{CurrencyFormatter.format(restante)}"
        )
        layout.addWidget(restante_label)

        if percentual >= 100:
            nome.setObjectName("positivo")

        elif percentual >= 80:
            nome.setObjectName("warning")

        else:
            nome.setObjectName("negativo")

        nome.style().unpolish(nome)
        nome.style().polish(nome)

        botoes_layout = QHBoxLayout()

        btn_concluir = QPushButton(
            TranslatorApp.get("Concluir")
        )
        btn_concluir.clicked.connect(
            lambda _, id_meta=meta.get("ID_Meta"):
            self._concluir(id_meta)
        )

        btn_excluir = QPushButton(
            TranslatorApp.get("Excluir")
        )
        btn_excluir.setObjectName("deleteButton")
        btn_excluir.clicked.connect(
            lambda _, id_meta=meta.get("ID_Meta"):
            self._excluir(id_meta)
        )

        botoes_layout.addWidget(btn_concluir)
        botoes_layout.addWidget(btn_excluir)

        layout.addLayout(botoes_layout)

        return frame

    # ==================================================
    # AÇÕES
    # ==================================================
    def _nova_meta(self):
        dialog = MetaDialog(self)

        if dialog.exec_() == dialog.Accepted:
            self.carregar_metas()

    def _concluir(self, id_meta):
        if not id_meta:
            return

        try:
            self.controller.concluir_meta(id_meta)
            self.carregar_metas()

        except Exception:
            logger.exception("Erro ao concluir meta")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro ao concluir meta.")
            )

    def _excluir(self, id_meta):
        if not id_meta:
            return

        confirm = QMessageBox.question(
            self,
            TranslatorApp.get("Confirmar Exclusão"),
            TranslatorApp.get("Deseja realmente excluir esta meta?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            self.controller.excluir_meta(id_meta)
            self.carregar_metas()

        except Exception:
            logger.exception("Erro ao excluir meta")

            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro ao excluir meta.")
            )

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
