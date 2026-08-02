# -*- coding: utf-8 -*-
"""Tela de acesso do Finance Assist."""

import logging
import os

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, pyqtSlot
from PyQt5.QtGui import (
    QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSizePolicy, QToolButton,
    QVBoxLayout, QWidget,
)

from controllers.user_controller import UserController
from core.translator_app import TranslatorApp
from core.theme_manager import ThemeManager
from core.window_manager import WindowManager
from utilitarios.ion_path import IonPath
from views.cadastro_usuario_dialog import CadastroUsuarioDialog

logger = logging.getLogger(__name__)


class FinanceHeroWidget(QWidget):
    """Ilustração vetorial leve; não conhece autenticação nem dados do usuário."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loginHero")
        self.setMinimumWidth(330)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        background = QLinearGradient(rect.topLeft(), rect.bottomRight())
        background.setColorAt(0, QColor("#061A33"))
        background.setColorAt(1, QColor("#063D61"))
        painter.fillRect(rect, background)

        accent = QPainterPath()
        accent.moveTo(rect.width() * .78, 0)
        accent.cubicTo(rect.width() * .66, rect.height() * .18,
                       rect.width() * .98, rect.height() * .34,
                       rect.width() * .79, rect.height() * .56)
        accent.lineTo(rect.width(), rect.height() * .70)
        accent.lineTo(rect.width(), 0)
        accent.closeSubpath()
        wave = QLinearGradient(0, 0, rect.width(), rect.height())
        wave.setColorAt(0, QColor(16, 192, 207, 210))
        wave.setColorAt(1, QColor(15, 91, 142, 90))
        painter.fillPath(accent, wave)

        margin = max(34, int(rect.width() * .09))
        painter.setPen(QColor("#F7FAFC"))
        painter.setFont(QFont("Sans Serif", 19, QFont.Bold))
        painter.drawText(QRectF(margin, 72, rect.width() - margin * 2, 34),
                         Qt.AlignLeft | Qt.AlignVCenter, "Tenha controle total")
        painter.setPen(QColor("#1DD0D8"))
        painter.drawText(QRectF(margin, 104, rect.width() - margin * 2, 40),
                         Qt.AlignLeft | Qt.AlignVCenter, "das suas finanças")
        painter.setPen(QColor("#D9E6F3"))
        painter.setFont(QFont("Sans Serif", 11))
        painter.drawText(QRectF(margin, 158, rect.width() - margin * 2, 82),
                         Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                         "Organize seus gastos, planeje seus objetivos e alcance "
                         "uma vida financeira melhor.")

        chart = QRectF(margin, rect.height() * .42, rect.width() - margin * 1.4,
                       min(245, rect.height() * .34))
        painter.setBrush(QColor(3, 32, 62, 210))
        painter.setPen(QPen(QColor(40, 137, 188, 150), 1))
        painter.drawRoundedRect(chart, 18, 18)
        painter.setPen(QColor("#E7F2FA"))
        painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
        painter.drawText(chart.adjusted(22, 16, -20, -10), Qt.AlignTop, "Resumo financeiro")
        painter.setFont(QFont("Sans Serif", 9))
        painter.setPen(QColor("#82E6E9"))
        painter.drawText(chart.adjusted(22, 48, -20, -10), Qt.AlignTop, "Receitas  •  Planejamento  •  Metas")

        graph = chart.adjusted(28, 92, -28, -30)
        painter.setPen(QPen(QColor(71, 129, 173, 80), 1))
        for index in range(4):
            y = graph.top() + graph.height() * index / 3
            painter.drawLine(QPointF(graph.left(), y), QPointF(graph.right(), y))
        points = [
            QPointF(graph.left() + graph.width() * ratio, graph.bottom() - graph.height() * value)
            for ratio, value in ((0, .18), (.16, .36), (.32, .31), (.48, .54),
                                 (.64, .46), (.80, .76), (1, .67))
        ]
        painter.setPen(QPen(QColor("#19C9D3"), 3))
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)
        painter.setBrush(QColor("#19C9D3"))
        painter.setPen(Qt.NoPen)
        for point in points:
            painter.drawEllipse(point, 4, 4)

        card = QRectF(margin + 18, chart.bottom() - 20, chart.width() * .54, 92)
        card_gradient = QLinearGradient(card.topLeft(), card.bottomRight())
        card_gradient.setColorAt(0, QColor("#0B6D8F"))
        card_gradient.setColorAt(1, QColor("#10B8C1"))
        painter.setBrush(QBrush(card_gradient))
        painter.setPen(QPen(QColor(164, 238, 242, 170), 1))
        painter.drawRoundedRect(card, 14, 14)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
        painter.drawText(card.adjusted(18, 14, -12, -10), Qt.AlignTop, "FINANCE ASSIST")
        painter.setFont(QFont("Monospace", 9))
        painter.drawText(card.adjusted(18, 46, -12, -10), Qt.AlignTop, "••••  ••••  ••••  3456")


class LoginDialog(QDialog):
    """Autenticação preservada com apresentação responsiva em card central."""

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller or UserController()
        self.usuario_logado = None
        self._icon_cache = {}

        self.setObjectName("loginRoot")
        self.setWindowIcon(self._icon("finance_assist"))
        self.setModal(True)
        self.setMinimumSize(720, 540)
        self.resize(1120, 720)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._connect_events()
        self._configure_accessibility()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()
        self.login_input.setFocus()

    def _icon(self, name):
        if name not in self._icon_cache:
            try:
                path = IonPath.resource("assets", "icons", f"{name}.svg")
                self._icon_cache[name] = QIcon(path) if os.path.exists(path) else QIcon()
            except Exception:
                logger.exception("Erro ao carregar ícone: %s", name)
                self._icon_cache[name] = QIcon()
        return self._icon_cache[name]

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.hero = FinanceHeroWidget()
        body.addWidget(self.hero, 44)

        form_area = QWidget()
        form_area.setObjectName("loginFormArea")
        center = QHBoxLayout(form_area)
        center.setContentsMargins(40, 40, 40, 40)
        center.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setMinimumWidth(420)
        self.card.setMaximumWidth(590)
        self.card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 35, 65, 45))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 28)
        card_layout.setSpacing(0)

        content = QWidget()
        content.setObjectName("loginContent")
        form = QVBoxLayout(content)
        form.setContentsMargins(36, 28, 36, 0)
        form.setSpacing(13)

        brand = QHBoxLayout()
        brand.setSpacing(18)
        self.logo_label = QLabel()
        self.logo_label.setObjectName("loginLogo")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setPixmap(self._brand_pixmap(68))
        brand_text = QVBoxLayout()
        brand_text.setSpacing(3)
        self.brand_title = QLabel()
        self.brand_title.setObjectName("loginBrandTitle")
        self.brand_subtitle = QLabel()
        self.brand_subtitle.setObjectName("loginBrandSubtitle")
        brand_text.addWidget(self.brand_title)
        brand_text.addWidget(self.brand_subtitle)
        brand.addStretch()
        brand.addWidget(self.logo_label)
        brand.addLayout(brand_text)
        brand.addStretch()
        form.addLayout(brand)

        self.card_title = QLabel()
        self.card_title.setObjectName("loginDialogTitle")
        self.card_title.setAlignment(Qt.AlignCenter)
        form.addWidget(self.card_title)
        accent = QFrame()
        accent.setObjectName("loginAccent")
        accent.setFixedSize(58, 3)
        form.addWidget(accent, 0, Qt.AlignCenter)
        form.addSpacing(14)

        self.lbl_login = QLabel()
        self.lbl_login.setObjectName("loginFieldLabel")
        form.addWidget(self.lbl_login)
        self.login_container, self.login_input, self.login_icon = self._create_field(
            "user", password=False
        )
        form.addWidget(self.login_container)

        form.addSpacing(4)
        self.lbl_senha = QLabel()
        self.lbl_senha.setObjectName("loginFieldLabel")
        form.addWidget(self.lbl_senha)
        self.password_container, self.senha_input, self.password_icon = self._create_field(
            "lock", password=True
        )
        self.btn_toggle = QToolButton()
        self.btn_toggle.setObjectName("loginIconButton")
        self.btn_toggle.setIcon(self._eye_icon(False, 22))
        self.btn_toggle.setIconSize(QSize(22, 22))
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.password_container.layout().addWidget(self.btn_toggle)
        form.addWidget(self.password_container)

        form.addSpacing(15)
        self.btn_login = QPushButton()
        self.btn_login.setObjectName("loginPrimary")
        self.btn_login.setIcon(self._tinted_icon("login", "#FFFFFF", 21))
        self.btn_login.setIconSize(QSize(21, 21))
        self.btn_login.setDefault(True)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        form.addWidget(self.btn_login)

        self.btn_cadastrar = QPushButton()
        self.btn_cadastrar.setObjectName("loginSecondary")
        register_icon = "register" if not self._icon("register").isNull() else "user"
        self.btn_cadastrar.setIcon(self._tinted_icon(
            register_icon, ThemeManager.get_color("primary"), 21
        ))
        self.btn_cadastrar.setIconSize(QSize(21, 21))
        self.btn_cadastrar.setCursor(Qt.PointingHandCursor)
        form.addWidget(self.btn_cadastrar)

        self.btn_recuperar = QPushButton()
        self.btn_recuperar.setObjectName("linkButton")
        self.btn_recuperar.setFlat(True)
        self.btn_recuperar.setCursor(Qt.PointingHandCursor)
        form.addWidget(self.btn_recuperar, 0, Qt.AlignCenter)

        card_layout.addWidget(content)
        center.addWidget(self.card)
        center.addStretch(1)
        body.addWidget(form_area, 56)
        root.addLayout(body, 1)

        footer = QFrame()
        footer.setObjectName("loginFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(42, 14, 42, 14)
        for symbol, title, detail in (
            ("✓", "Seus dados protegidos", "Segurança e privacidade em primeiro lugar"),
            ("◔", "Insights inteligentes", "Relatórios para melhores decisões"),
            ("◎", "Alcance seus objetivos", "Planeje, acompanhe e conquiste mais"),
        ):
            item = QHBoxLayout()
            icon = QLabel(symbol)
            icon.setObjectName("loginBenefitIcon")
            copy = QVBoxLayout()
            copy.setSpacing(1)
            title_label = QLabel(title)
            title_label.setObjectName("loginBenefitTitle")
            detail_label = QLabel(detail)
            detail_label.setObjectName("loginBenefitDetail")
            copy.addWidget(title_label)
            copy.addWidget(detail_label)
            item.addWidget(icon)
            item.addLayout(copy)
            footer_layout.addLayout(item)
            footer_layout.addStretch(1)
        root.addWidget(footer)

    def _create_field(self, icon_name, password=False):
        container = QWidget()
        container.setObjectName("loginField")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setObjectName("loginFieldIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setPixmap(self._field_pixmap(icon_name, 20))

        field = QLineEdit()
        field.setObjectName("loginInput")
        field.setClearButtonEnabled(not password)
        if password:
            field.setEchoMode(QLineEdit.Password)

        layout.addWidget(icon)
        layout.addWidget(field, 1)
        return container, field, icon

    def _tinted_icon(self, name, color, size):
        pixmap = self._icon(name).pixmap(size, size)
        if pixmap.isNull():
            return QIcon()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _brand_pixmap(size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor("#0BA9B6")
        painter.setPen(QPen(color, max(2, size // 24), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        outline = QPainterPath()
        outline.moveTo(size * .22, size * .28)
        outline.lineTo(size * .22, size * .69)
        outline.quadTo(size * .22, size * .82, size * .38, size * .82)
        outline.lineTo(size * .66, size * .82)
        outline.quadTo(size * .80, size * .82, size * .80, size * .68)
        outline.lineTo(size * .80, size * .31)
        painter.drawPath(outline)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        bar_width = size * .12
        for x, top in ((.35, .52), (.50, .37), (.65, .22)):
            painter.drawRoundedRect(QRectF(size * x, size * top, bar_width,
                                           size * .68 - size * top), 2, 2)
        painter.end()
        return pixmap

    @staticmethod
    def _field_pixmap(kind, size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#64748B"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if kind == "user":
            painter.drawEllipse(QRectF(size * .34, size * .08, size * .32, size * .32))
            path = QPainterPath()
            path.moveTo(size * .18, size * .92)
            path.cubicTo(size * .20, size * .56, size * .80, size * .56, size * .82, size * .92)
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(QRectF(size * .20, size * .44, size * .60, size * .48), 2, 2)
            path = QPainterPath()
            path.moveTo(size * .34, size * .44)
            path.lineTo(size * .34, size * .30)
            path.cubicTo(size * .34, size * .02, size * .66, size * .02,
                         size * .66, size * .30)
            path.lineTo(size * .66, size * .44)
            painter.drawPath(path)
        painter.end()
        return pixmap

    @staticmethod
    def _eye_icon(hidden, size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#64748B"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        eye = QPainterPath()
        eye.moveTo(size * .08, size * .50)
        eye.cubicTo(size * .26, size * .18, size * .74, size * .18, size * .92, size * .50)
        eye.cubicTo(size * .74, size * .82, size * .26, size * .82, size * .08, size * .50)
        painter.drawPath(eye)
        painter.drawEllipse(QRectF(size * .39, size * .39, size * .22, size * .22))
        if hidden:
            painter.drawLine(QPointF(size * .14, size * .14), QPointF(size * .86, size * .86))
        painter.end()
        return QIcon(pixmap)

    def _connect_events(self):
        self.login_input.returnPressed.connect(self._autenticar)
        self.senha_input.returnPressed.connect(self._autenticar)
        self.login_input.textChanged.connect(lambda: self._set_invalid(self.login_container, False))
        self.senha_input.textChanged.connect(lambda: self._set_invalid(self.password_container, False))
        self.btn_toggle.clicked.connect(self._toggle_password)
        self.btn_login.clicked.connect(self._autenticar)
        self.btn_cadastrar.clicked.connect(self._abrir_cadastro)
        self.btn_recuperar.clicked.connect(self._recuperar_senha)

    def _configure_accessibility(self):
        self.setTabOrder(self.login_input, self.senha_input)
        self.setTabOrder(self.senha_input, self.btn_toggle)
        self.setTabOrder(self.btn_toggle, self.btn_login)
        self.setTabOrder(self.btn_login, self.btn_cadastrar)
        self.setTabOrder(self.btn_cadastrar, self.btn_recuperar)

    def _atualizar_textos(self, *_):
        self.setWindowTitle(TranslatorApp.get("Finance Assist"))
        self.card_title.setText(TranslatorApp.get("Entre para continuar"))
        self.brand_title.setText(TranslatorApp.get("Finance Assist"))
        self.brand_subtitle.setText(TranslatorApp.get("Sua gestão financeira, simplificada."))
        self.lbl_login.setText(TranslatorApp.get("Usuário ou e-mail:"))
        self.login_input.setPlaceholderText(TranslatorApp.get("Login ou e-mail"))
        self.lbl_senha.setText(TranslatorApp.get("Senha:"))
        self.senha_input.setPlaceholderText(TranslatorApp.get("Digite sua senha"))
        self.btn_login.setText(TranslatorApp.get("Entrar"))
        self.btn_cadastrar.setText(TranslatorApp.get("Cadastrar"))
        self.btn_recuperar.setText(TranslatorApp.get("Esqueci minha senha"))
        self.btn_toggle.setToolTip(TranslatorApp.get("Mostrar ou ocultar senha"))
        self.login_input.setAccessibleName(TranslatorApp.get("Usuário ou e-mail"))
        self.senha_input.setAccessibleName(TranslatorApp.get("Senha"))

    @staticmethod
    def _set_invalid(widget, invalid):
        widget.setProperty("invalid", bool(invalid))
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _toggle_password(self):
        visible = self.senha_input.echoMode() == QLineEdit.Password
        self.senha_input.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.btn_toggle.setIcon(self._eye_icon(visible, 22))

    @pyqtSlot()
    def _autenticar(self):
        login = self.login_input.text().strip()
        senha = self.senha_input.text().strip()
        self._set_invalid(self.login_container, not login)
        self._set_invalid(self.password_container, not senha)

        if not login or not senha:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Por favor, preencha todos os campos."),
            )
            (self.login_input if not login else self.senha_input).setFocus()
            return

        try:
            usuario = self.controller.authenticate_user(login, senha)
            if usuario:
                self.usuario_logado = usuario
                self.accept()
                return
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Usuário ou senha inválidos."),
            )
        except Exception:
            logger.exception("Erro ao autenticar usuário")
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro interno ao autenticar usuário."),
            )

    def _abrir_cadastro(self):
        dialog = CadastroUsuarioDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.login_input.clear()
            self.senha_input.clear()
            self.login_input.setFocus()

    def _recuperar_senha(self):
        login_or_email, ok = QInputDialog.getText(
            self,
            TranslatorApp.get("Recuperar Senha"),
            TranslatorApp.get("Digite seu login ou e-mail:"),
        )
        if not ok or not login_or_email.strip():
            return
        try:
            token = self.controller.request_password_reset(login_or_email.strip())
            if not token:
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Erro"),
                    TranslatorApp.get("Usuário não encontrado ou erro ao gerar token."),
                )
                return
            QMessageBox.information(
                self,
                TranslatorApp.get("Token Gerado"),
                f"{TranslatorApp.get('Token gerado')}: \n\n{token}",
            )
            token_digitado, ok = QInputDialog.getText(
                self,
                TranslatorApp.get("Confirmar Token"),
                TranslatorApp.get("Digite o token recebido:"),
            )
            if not ok:
                return
            nova_senha, ok = QInputDialog.getText(
                self,
                TranslatorApp.get("Nova Senha"),
                TranslatorApp.get("Digite sua nova senha:"),
                QLineEdit.Password,
            )
            if not ok:
                return
            sucesso = self.controller.reset_password_with_token(
                token_digitado.strip(), nova_senha.strip()
            )
            if sucesso:
                QMessageBox.information(
                    self,
                    TranslatorApp.get("Sucesso"),
                    TranslatorApp.get("Senha redefinida com sucesso."),
                )
            else:
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Erro"),
                    TranslatorApp.get("Token inválido ou expirado."),
                )
        except Exception:
            logger.exception("Erro ao recuperar senha")
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro interno ao recuperar senha."),
            )

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        WindowManager.fit_dialog(self, self.parentWidget())
