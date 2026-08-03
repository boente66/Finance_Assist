# -*- coding: utf-8 -*-
import importlib
import logging
import os

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QDialog,
    QLabel,
    QFrame,
    QApplication,
    QScrollArea,
)
from PyQt5.QtCore import QPointF, QRectF, QTimer, Qt, QSize
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QShortcut

from core.session import Session
from core.theme_manager import ThemeManager
from core.translator_app import TranslatorApp
from core.window_manager import WindowManager
from utilitarios.ion_path import IonPath

logger = logging.getLogger(__name__)


class MainView(QMainWindow):

    def __init__(self, usuario_logado):
        super().__init__()

        Session.set_usuario(usuario_logado)
        self.usuario = usuario_logado or {}

        self._current_view_class = None
        self._current_widget = None

        self._menu_buttons = []
        self._user_menu_buttons = []

        self._user_menu_expanded = False
        self._icon_cache = {}
        default_sidebar = ThemeManager.get_theme_config()["layout"]["sidebar_width"]
        self._menu_compact_preference, self._sidebar_expanded_width = (
            WindowManager.menu_preferences(default_sidebar)
        )
        self._sidebar_compact = False
        self._manual_compact_override = False

        self.setMinimumSize(820, 600)
        self.setWindowTitle("Controle Financeiro")
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
        )

        self._init_ui()
        self._criar_marca()
        self._criar_menu()
        self._configure_shortcuts()
        self.aplicar_tema()

        Session.on_tema_change(
            lambda _: self.aplicar_tema()
        )

        TranslatorApp.bind(
            self._atualizar_textos,
            self
        )
        self._atualizar_textos()

        WindowManager.restore_main_window(self)
        self._update_sidebar_for_width()

        self._abrir_primeira_view()

    # ==================================================
    # MARCA
    # ==================================================
    def _criar_marca(self):
        self.brand = QWidget()
        self.brand.setObjectName("sidebarBrand")
        brand_layout = QHBoxLayout(self.brand)
        brand_layout.setContentsMargins(18, 12, 14, 22)
        self.brand_icon = QLabel()
        self.brand_icon.setObjectName("brandIcon")
        self.brand_icon.setPixmap(
            self._tinted_icon("finance_assist", "#20C7D4", 42).pixmap(42, 42)
        )
        self.brand_title = QLabel("Finance\nAssist")
        self.brand_title.setObjectName("brandTitle")
        brand_layout.addWidget(self.brand_icon)
        brand_layout.addWidget(self.brand_title, 1)
        self.sidebar_layout.addWidget(self.brand)

        self.sidebar_toggle = QPushButton("‹")
        self.sidebar_toggle.setObjectName("sidebarToggle")
        self.sidebar_toggle.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(self.sidebar_toggle, 0, Qt.AlignRight)

    # ==================================================
    # UI BASE
    # ==================================================
    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebarShell")
        sidebar_shell_layout = QVBoxLayout(self.sidebar)
        sidebar_shell_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_content = QWidget()
        self.sidebar_content.setObjectName("sidebar")
        self.sidebar_scroll.setWidget(self.sidebar_content)
        sidebar_shell_layout.addWidget(self.sidebar_scroll)

        self.sidebar_layout = QVBoxLayout(self.sidebar_content)
        self.sidebar_layout.setContentsMargins(0, 15, 0, 15)
        self.sidebar_layout.setSpacing(4)

        main_layout.addWidget(self.sidebar, 1)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)

        main_layout.addWidget(self.content, 4)

    # ==================================================
    # UTIL
    # ==================================================
    def _is_admin(self):
        return (
            self.usuario.get("Nivel_Acesso") or ""
        ).lower() == "admin"

    def _icon(self, nome):
        if nome in self._icon_cache:
            return self._icon_cache[nome]

        try:
            path = IonPath.resource(
                "assets",
                "icons",
                f"{nome}.svg"
            )

            icon = QIcon(path) if os.path.exists(path) else QIcon()
            self._icon_cache[nome] = icon

            return icon

        except Exception:
            logger.exception(
                "Erro ao carregar ícone: %s",
                nome
            )
            return QIcon()

    def _tinted_icon(self, name, color, size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color), max(1.6, size / 12), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        s = float(size)
        if name in ("resumo", "relatorios", "finance_assist"):
            painter.drawLine(QPointF(.18*s, .82*s), QPointF(.18*s, .58*s))
            painter.drawLine(QPointF(.42*s, .82*s), QPointF(.42*s, .38*s))
            painter.drawLine(QPointF(.66*s, .82*s), QPointF(.66*s, .18*s))
            if name == "relatorios":
                painter.drawLine(QPointF(.12*s, .86*s), QPointF(.86*s, .86*s))
        elif name == "transacoes":
            painter.drawRoundedRect(QRectF(.10*s, .24*s, .80*s, .56*s), 2, 2)
            painter.drawLine(QPointF(.10*s, .42*s), QPointF(.90*s, .42*s))
            painter.drawEllipse(QRectF(.67*s, .57*s, .10*s, .10*s))
        elif name == "metas":
            painter.drawEllipse(QRectF(.13*s, .13*s, .68*s, .68*s))
            painter.drawEllipse(QRectF(.34*s, .34*s, .28*s, .28*s))
            painter.drawLine(QPointF(.52*s, .48*s), QPointF(.88*s, .12*s))
        elif name == "categorias":
            path = QPainterPath()
            path.moveTo(.10*s, .30*s); path.lineTo(.38*s, .30*s)
            path.lineTo(.47*s, .40*s); path.lineTo(.90*s, .40*s)
            path.lineTo(.84*s, .80*s); path.lineTo(.14*s, .80*s); path.closeSubpath()
            painter.drawPath(path)
        elif name in ("favorecidos", "perfil", "gerenciar_usuarios"):
            painter.drawEllipse(QRectF(.36*s, .12*s, .28*s, .28*s))
            arc = QPainterPath(); arc.moveTo(.18*s, .86*s)
            arc.cubicTo(.20*s, .50*s, .80*s, .50*s, .82*s, .86*s)
            painter.drawPath(arc)
        elif name == "agendamentos":
            painter.drawRoundedRect(QRectF(.13*s, .22*s, .74*s, .65*s), 2, 2)
            painter.drawLine(QPointF(.13*s, .42*s), QPointF(.87*s, .42*s))
            painter.drawLine(QPointF(.30*s, .10*s), QPointF(.30*s, .30*s))
            painter.drawLine(QPointF(.70*s, .10*s), QPointF(.70*s, .30*s))
        elif name == "configuracoes":
            painter.drawEllipse(QRectF(.31*s, .31*s, .38*s, .38*s))
            for start, end in (((.50,.08),(.50,.25)),((.50,.75),(.50,.92)),
                               ((.08,.50),(.25,.50)),((.75,.50),(.92,.50)),
                               ((.20,.20),(.32,.32)),((.68,.68),(.80,.80))):
                painter.drawLine(QPointF(start[0]*s,start[1]*s), QPointF(end[0]*s,end[1]*s))
        elif name == "backup":
            painter.drawRoundedRect(QRectF(.14*s, .48*s, .72*s, .38*s), 2, 2)
            painter.drawLine(QPointF(.50*s, .12*s), QPointF(.50*s, .60*s))
            painter.drawLine(QPointF(.32*s, .32*s), QPointF(.50*s, .12*s))
            painter.drawLine(QPointF(.68*s, .32*s), QPointF(.50*s, .12*s))
        elif name == "login":
            painter.drawRoundedRect(QRectF(.12*s, .16*s, .48*s, .70*s), 2, 2)
            painter.drawLine(QPointF(.40*s, .50*s), QPointF(.90*s, .50*s))
            painter.drawLine(QPointF(.72*s, .32*s), QPointF(.90*s, .50*s))
            painter.drawLine(QPointF(.72*s, .68*s), QPointF(.90*s, .50*s))
        else:
            painter.drawRoundedRect(QRectF(.16*s, .16*s, .68*s, .68*s), 3, 3)
        painter.end()
        return QIcon(pixmap)

    # ==================================================
    # MENU PRINCIPAL
    # ==================================================
    def _criar_menu(self):

        def add_btn(attr_name, texto, view_ref, icon_name):
            btn = QPushButton(texto)

            btn.setObjectName("menuButton")
            btn.setProperty("active", False)
            btn.setCursor(Qt.PointingHandCursor)

            btn.setIcon(self._icon(icon_name))
            btn.setIconSize(QSize(18, 18))
            btn.setContentsMargins(15, 8, 10, 8)
            btn.setProperty("fullText", texto)
            btn.setProperty("iconName", icon_name)
            btn.setToolTip(texto)

            btn.clicked.connect(
                lambda _, b=btn, v=view_ref:
                self._handle_menu_click(b, v)
            )

            setattr(self, attr_name, btn)

            self.sidebar_layout.addWidget(btn)
            self._menu_buttons.append((btn, view_ref))

        add_btn(
            "btn_resumo",
            "Resumo Financeiro",
            ("views.resumo_financeiro_view", "ResumoFinanceiroView"),
            "resumo"
        )

        add_btn(
            "btn_transacoes",
            "Contas e Lançamentos",
            ("views.transacao_view", "TransacaoView"),
            "transacoes"
        )

        add_btn(
            "btn_metas",
            "Metas Financeiras",
            ("views.meta_view", "MetaView"),
            "metas"
        )

        add_btn(
            "btn_categorias",
            "Lista de Categorias",
            ("views.lista_categorias_view", "ListaCategoriasView"),
            "categorias"
        )

        add_btn(
            "btn_relatorios",
            "Relatórios",
            ("views.relatorio_view", "RelatorioView"),
            "relatorios"
        )

        add_btn(
            "btn_favorecidos",
            "Favorecidos",
            ("views.favorecido_view", "FavorecidoView"),
            "favorecidos"
        )

        add_btn(
            "btn_agendamentos",
            "Agendamentos",
            ("views.agendamento_view", "AgendamentoView"),
            "agendamentos"
        )

        add_btn(
            "btn_configuracoes",
            "Configurações",
            ("views.configuracoes_view", "ConfiguracoesView"),
            "configuracoes"
        )

        self.sidebar_layout.addStretch()

        divisor = QFrame()
        divisor.setFrameShape(QFrame.HLine)
        divisor.setFrameShadow(QFrame.Sunken)
        self.sidebar_layout.addWidget(divisor)

        self._criar_bloco_usuario()

    # ==================================================
    # BLOCO USUÁRIO
    # ==================================================
    def _criar_bloco_usuario(self):
        nome = (
            self.usuario.get("Nome")
            or TranslatorApp.get("Usuário")
        )

        self.user_card = QFrame()
        self.user_card.setObjectName("sidebarUserCard")
        self.user_card_layout = QHBoxLayout(self.user_card)
        self.user_card_layout.setContentsMargins(14, 10, 12, 10)
        self.user_card_layout.setSpacing(10)
        initials = "".join(part[0] for part in nome.split()[:2]).upper() or "U"
        self.user_avatar = QLabel(initials)
        self.user_avatar.setObjectName("sidebarAvatar")
        self.user_avatar.setAlignment(Qt.AlignCenter)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        self.lbl_usuario = QLabel(nome)
        self.lbl_usuario.setObjectName("sidebarUser")
        self.lbl_usuario_detail = QLabel(
            self.usuario.get("Email") or self.usuario.get("Nivel_Acesso") or ""
        )
        self.lbl_usuario_detail.setObjectName("sidebarUserDetail")
        copy.addWidget(self.lbl_usuario)
        copy.addWidget(self.lbl_usuario_detail)
        self.user_toggle = QLabel("⌄")
        self.user_toggle.setObjectName("sidebarUserToggle")
        self.user_card_layout.addWidget(self.user_avatar)
        self.user_card_layout.addLayout(copy, 1)
        self.user_card_layout.addWidget(self.user_toggle)
        self.user_card.setCursor(Qt.PointingHandCursor)
        self.user_card.setToolTip(TranslatorApp.get("Abrir opções do usuário"))
        self.user_card.mousePressEvent = self._toggle_user_menu

        self.sidebar_layout.addWidget(self.user_card)

        self.user_menu_container = QWidget()
        self.user_menu_container.setObjectName("sidebarSubmenu")

        self.user_menu_layout = QVBoxLayout(
            self.user_menu_container
        )
        self.user_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.user_menu_layout.setSpacing(2)

        self.user_menu_container.setVisible(False)

        self.sidebar_layout.addWidget(
            self.user_menu_container
        )

        self._criar_menu_usuario()

        self.btn_logout = QPushButton("Sair")
        self.btn_logout.setObjectName("menuButton")
        self.btn_logout.setIcon(self._icon("login"))
        self.btn_logout.setIconSize(QSize(17, 17))
        self.btn_logout.setProperty("fullText", "Sair")
        self.btn_logout.setProperty("iconName", "login")
        self.btn_logout.setToolTip("Sair")
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.clicked.connect(self._logout)
        self.sidebar_layout.addWidget(self.btn_logout)

    # ==================================================
    # MENU USUÁRIO
    # ==================================================
    def _criar_menu_usuario(self):

        def add_user_btn(attr_name, texto, view_ref, icon_name):
            btn = QPushButton(texto)

            btn.setObjectName("menuButton")
            btn.setCursor(Qt.PointingHandCursor)

            btn.setIcon(self._icon(icon_name))
            btn.setIconSize(QSize(16, 16))
            btn.setContentsMargins(30, 8, 10, 8)
            btn.setProperty("fullText", texto)
            btn.setProperty("iconName", icon_name)
            btn.setToolTip(texto)

            btn.clicked.connect(
                lambda _, v=view_ref:
                self._carregar_view(v)
            )

            setattr(self, attr_name, btn)

            self.user_menu_layout.addWidget(btn)
            self._user_menu_buttons.append((btn, view_ref))

        add_user_btn(
            "btn_perfil",
            "Perfil",
            ("views.perfil_view", "PerfilView"),
            "perfil"
        )

        if self._is_admin():
            add_user_btn(
                "btn_gerenciar",
                "Gerenciamento de Usuários",
                (
                    "views.gerenciamento_usuarios_view",
                    "GerenciamentoUsuariosView"
                ),
                "gerenciar_usuarios"
            )

        if self._is_admin():
            add_user_btn(
                "btn_backup",
                "Backup e Restauração",
                ("views.backup_view", "BackupView"),
                "backup"
            )

    # ==================================================
    # TRADUÇÃO
    # ==================================================
    def _atualizar_textos(self, *_):
        self.setWindowTitle(
            TranslatorApp.get("Controle Financeiro")
        )
        self.brand_title.setText("Finance\nAssist")

        self.btn_resumo.setText(
            TranslatorApp.get("Resumo Financeiro")
        )

        self.btn_transacoes.setText(
            TranslatorApp.get("Contas e Lançamentos")
        )

        self.btn_metas.setText(
            TranslatorApp.get("Metas Financeiras")
        )

        self.btn_categorias.setText(
            TranslatorApp.get("Lista de Categorias")
        )

        self.btn_relatorios.setText(
            TranslatorApp.get("Relatórios")
        )

        self.btn_favorecidos.setText(
            TranslatorApp.get("Favorecidos")
        )

        self.btn_agendamentos.setText(
            TranslatorApp.get("Agendamentos")
        )

        self.btn_configuracoes.setText(
            TranslatorApp.get("Configurações")
        )

        nome = (
            self.usuario.get("Nome")
            or TranslatorApp.get("Usuário")
        )

        self.lbl_usuario.setText(nome)

        if hasattr(self, "btn_perfil"):
            self.btn_perfil.setText(
                TranslatorApp.get("Perfil")
            )

        if hasattr(self, "btn_gerenciar"):
            self.btn_gerenciar.setText(
                TranslatorApp.get("Gerenciamento de Usuários")
            )

        if hasattr(self, "btn_backup"):
            self.btn_backup.setText(
                TranslatorApp.get("Backup e Restauração")
            )

        if hasattr(self, "btn_logout"):
            self.btn_logout.setText(TranslatorApp.get("Sair"))

        for button, _ in self._menu_buttons + self._user_menu_buttons:
            button.setProperty("fullText", button.text())
            button.setToolTip(button.text())
        if hasattr(self, "btn_logout"):
            self.btn_logout.setProperty("fullText", self.btn_logout.text())
            self.btn_logout.setToolTip(self.btn_logout.text())
        if hasattr(self, "sidebar_toggle"):
            self.sidebar_toggle.setToolTip(
                TranslatorApp.get("Expandir menu" if self._sidebar_compact else "Recolher menu")
            )
        self._apply_sidebar_mode(self._sidebar_compact)

    # ==================================================
    # RESPONSIVIDADE E ATALHOS
    # ==================================================
    def _configure_shortcuts(self):
        self.shortcut_maximize = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.shortcut_maximize.activated.connect(self.toggle_maximized)
        self.shortcut_sidebar = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        self.shortcut_sidebar.activated.connect(self.toggle_sidebar)

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def toggle_sidebar(self):
        if self._sidebar_compact:
            self._menu_compact_preference = False
            self._manual_compact_override = self.width() < 1080
            self._apply_sidebar_mode(False)
        else:
            self._menu_compact_preference = True
            self._manual_compact_override = False
            self._apply_sidebar_mode(True)

    def _update_sidebar_for_width(self):
        auto_compact = self.width() < 1080 and not self._manual_compact_override
        self._apply_sidebar_mode(self._menu_compact_preference or auto_compact)

    def _apply_sidebar_mode(self, compact):
        self._sidebar_compact = bool(compact)
        width = 72 if compact else self._sidebar_expanded_width
        self.sidebar.setMinimumWidth(width)
        self.sidebar.setMaximumWidth(width)
        self.sidebar.setProperty("compact", compact)
        self.sidebar_content.setProperty("compact", compact)
        self.brand_title.setVisible(not compact)
        self.lbl_usuario.setVisible(not compact)
        self.lbl_usuario_detail.setVisible(not compact)
        self.user_toggle.setVisible(not compact)
        self.user_card_layout.setContentsMargins(12 if compact else 14, 10, 12, 10)
        buttons = [button for button, _ in self._menu_buttons + self._user_menu_buttons]
        buttons.append(self.btn_logout)
        for button in buttons:
            full_text = button.property("fullText") or button.toolTip()
            icon_name = button.property("iconName")
            if icon_name:
                button.setIcon(self._tinted_icon(icon_name, "#E9F0FA", 20))
            button.setText("" if compact else full_text)
            button.setToolTip(full_text)
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)
        self.sidebar_toggle.setText("›" if compact else "‹")
        self.sidebar_toggle.setToolTip(TranslatorApp.get(
            "Expandir menu" if compact else "Recolher menu"
        ))
        self.sidebar.style().unpolish(self.sidebar)
        self.sidebar.style().polish(self.sidebar)
        self.sidebar_content.style().unpolish(self.sidebar_content)
        self.sidebar_content.style().polish(self.sidebar_content)
        self._notify_responsive_view()

    def _notify_responsive_view(self):
        if self._current_widget and hasattr(self._current_widget, "set_compact_mode"):
            self._current_widget.set_compact_mode(
                self._sidebar_compact,
                max(0, self.content.width()),
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self._update_sidebar_for_width()
            self._notify_responsive_view()

    # ==================================================
    # TOGGLE MENU
    # ==================================================
    def _toggle_user_menu(self, event=None):
        self._user_menu_expanded = not self._user_menu_expanded

        self.user_menu_container.setVisible(
            self._user_menu_expanded
        )
        self.user_toggle.setText("⌃" if self._user_menu_expanded else "⌄")
        if self._user_menu_expanded:
            QTimer.singleShot(
                0,
                lambda: self.sidebar_scroll.ensureWidgetVisible(
                    self.user_menu_container, 0, 24
                ),
            )

    # ==================================================
    # NAVEGAÇÃO
    # ==================================================
    def _abrir_primeira_view(self):
        if self._menu_buttons:
            btn, view_cls = self._menu_buttons[0]
            self._handle_menu_click(btn, view_cls)

    def _handle_menu_click(self, clicked_button, view_cls):
        resolved_view = self._resolve_view_class(view_cls)

        if self._current_view_class == resolved_view:
            return

        self._ativar_botao(clicked_button)
        self._carregar_view(resolved_view)

    def _ativar_botao(self, clicked_button):
        for btn, _ in self._menu_buttons:
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if clicked_button:
            clicked_button.setProperty("active", True)
            clicked_button.style().unpolish(clicked_button)
            clicked_button.style().polish(clicked_button)

    def _resolve_view_class(self, view_ref):
        if isinstance(view_ref, tuple):
            module_name, class_name = view_ref
            module = importlib.import_module(module_name)

            return getattr(module, class_name)

        return view_ref

    # ==================================================
    # TROCA DE VIEW
    # ==================================================
    def _carregar_view(self, view_cls):
        try:
            view_cls = self._resolve_view_class(view_cls)

            if self._current_widget:
                if self._current_widget.parent() is not None:
                    self.content_layout.removeWidget(
                        self._current_widget
                    )

                self._current_widget.setParent(None)
                self._current_widget.deleteLater()
                self._current_widget = None

            view = view_cls(parent=self)

            if hasattr(view, "usuario"):
                view.usuario = self.usuario

            if hasattr(view, "logout_requested"):
                view.logout_requested.connect(
                    self._logout
                )

            if hasattr(view, "open_invoice_requested"):
                view.open_invoice_requested.connect(self.open_invoice)

            if hasattr(view, "profile_updated"):
                view.profile_updated.connect(self._update_sidebar_user)

            if hasattr(view, "on_load"):
                view.on_load()

            self.content_layout.addWidget(view)

            self._current_widget = view
            self._current_view_class = view_cls
            self._notify_responsive_view()

        except Exception:
            view_name = getattr(
                view_cls,
                "__name__",
                str(view_cls)
            )

            logger.exception(
                "Erro ao carregar view %s",
                view_name
            )

    def _update_sidebar_user(self, usuario):
        """Reflete a autoedição do perfil sem reconstruir a navegação."""
        self.usuario = dict(usuario or {})
        name = self.usuario.get("Nome") or TranslatorApp.get("Usuário")
        initials = "".join(part[0] for part in name.split()[:2]).upper() or "U"
        self.user_avatar.setText(initials)
        self.lbl_usuario.setText(name)
        self.lbl_usuario_detail.setText(
            self.usuario.get("Email") or self.usuario.get("Nivel_Acesso") or ""
        )

    def open_invoice(self, id_cartao, mes, ano):
        """Abre o cartão e a competência vindos da projeção financeira."""
        from views.transacao_view import TransacaoView

        self._ativar_botao(self.btn_transacoes)
        self._carregar_view(TransacaoView)
        if isinstance(self._current_widget, TransacaoView):
            self._current_widget.abrir_fatura(id_cartao, mes, ano)

    # ==================================================
    # LOGOUT
    # ==================================================
    def _logout(self):
        self.close()

        try:
            from views.login_dialog import LoginDialog

            login = LoginDialog()

            if login.exec_() == QDialog.Accepted:
                nova_main = MainView(login.usuario_logado)
                nova_main.show()

        except Exception:
            logger.exception(
                "Erro ao realizar logout"
            )

    # ==================================================
    # TEMA
    # ==================================================
    def aplicar_tema(self):
        try:
            tema = Session.get_config(
                "tema",
                ThemeManager.DEFAULT
            )

            app = QApplication.instance()

            ThemeManager.aplicar_tema(
                tema,
                app
            )
            if hasattr(self, "sidebar"):
                self._apply_sidebar_mode(self._sidebar_compact)

        except Exception:
            logger.exception(
                "Erro ao aplicar tema"
            )

    # ==================================================
    # CICLO DE VIDA
    # ==================================================
    def closeEvent(self, event):
        WindowManager.save_main_window(
            self,
            menu_compact=self._menu_compact_preference,
            sidebar_width=self._sidebar_expanded_width,
        )
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass

        super().closeEvent(event)
