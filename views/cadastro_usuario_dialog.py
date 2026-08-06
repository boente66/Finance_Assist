import re

from PyQt5.QtCore import QDate, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from controllers.user_controller import UserController
from core.translator_app import TranslatorApp
from core.window_manager import WindowManager
from utilitarios.ion_path import IonPath


class CadastroUsuarioDialog(QDialog):
    """Cadastro e edição administrativa de usuários."""

    MODO_CADASTRO = "cadastro"
    MODO_EDICAO = "edicao"
    LIMITE_LAYOUT_COMPACTO = 640
    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        self.setObjectName("userDialog")
        self.resize(720, 620)
        self.setMinimumSize(600, 520)

        self.controller = controller or UserController()
        self.usuario_edicao = None
        self._modo = self.MODO_CADASTRO
        self._layout_compacto = None
        self._field_containers = {}
        self._error_labels = {}
        self._focus_widgets = {}

        self._init_ui()

        TranslatorApp.bind(self._atualizar_textos, self)
        self._atualizar_textos()

    # ==================================================
    # UI
    # ==================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        layout.addWidget(self._criar_cabecalho())

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("userDialogScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("userDialogContent")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 4, 0)
        self.scroll_layout.setSpacing(14)

        self.scroll_layout.addWidget(self._criar_card_dados_pessoais())
        self.scroll_layout.addWidget(self._criar_card_acesso())
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        layout.addWidget(self._criar_rodape())

        self._configurar_icones_senha()
        self._aplicar_layout_responsivo(force=True)

    def _criar_cabecalho(self):
        header = QFrame()
        header.setObjectName("profileFooter")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 12)
        header_layout.setSpacing(14)

        self.header_icon = QLabel("👤")
        self.header_icon.setObjectName("profileHeaderIcon")
        self.header_icon.setAlignment(Qt.AlignCenter)
        self.header_icon.setAccessibleName("Usuário")
        self._definir_icone_label(self.header_icon, "user", 34)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(2)
        self.lbl_titulo = QLabel()
        self.lbl_titulo.setObjectName("pageTitle")
        self.lbl_subtitulo = QLabel()
        self.lbl_subtitulo.setObjectName("pageSubtitle")
        self.lbl_subtitulo.setWordWrap(True)
        textos.addWidget(self.lbl_titulo)
        textos.addWidget(self.lbl_subtitulo)

        header_layout.addWidget(self.header_icon, 0, Qt.AlignTop)
        header_layout.addLayout(textos, 1)
        return header

    def _criar_card_dados_pessoais(self):
        card, card_layout, self.lbl_card_pessoais = self._criar_card()
        self.grid_pessoais = QGridLayout()
        self.grid_pessoais.setHorizontalSpacing(16)
        self.grid_pessoais.setVerticalSpacing(10)
        card_layout.addLayout(self.grid_pessoais)

        self.nome_input = QLineEdit()
        self.nome_input.setPlaceholderText("Digite o nome completo")

        self.nascimento_input = QDateEdit(QDate.currentDate())
        self.nascimento_input.setCalendarPopup(True)
        self.nascimento_input.setDisplayFormat("dd/MM/yyyy")

        self.sexo_input = QComboBox()
        self.sexo_input.addItem("Masculino", "Masculino")
        self.sexo_input.addItem("Feminino", "Feminino")
        self.sexo_input.addItem("Outro", "Outro")

        self.cpf_input = QLineEdit()
        self.cpf_input.setPlaceholderText("000.000.000-00")
        self.telefone_input = QLineEdit()
        self.telefone_input.setPlaceholderText("(00) 0000-0000")
        self.celular_input = QLineEdit()
        self.celular_input.setPlaceholderText("(00) 00000-0000")

        self.lbl_nome = self._adicionar_campo(
            "nome", self.grid_pessoais, "Nome", self.nome_input, obrigatorio=True
        )
        self.lbl_nascimento = self._adicionar_campo(
            "nascimento", self.grid_pessoais, "Data de nascimento", self.nascimento_input
        )
        self.lbl_sexo = self._adicionar_campo(
            "sexo", self.grid_pessoais, "Sexo", self.sexo_input
        )
        self.lbl_cpf = self._adicionar_campo(
            "cpf", self.grid_pessoais, "CPF", self.cpf_input
        )
        self.lbl_tel = self._adicionar_campo(
            "telefone", self.grid_pessoais, "Telefone", self.telefone_input
        )
        self.lbl_cel = self._adicionar_campo(
            "celular", self.grid_pessoais, "Celular", self.celular_input
        )
        self._campos_pessoais = [
            "nome", "nascimento", "sexo", "cpf", "telefone", "celular"
        ]
        return card

    def _criar_card_acesso(self):
        card, card_layout, self.lbl_card_acesso = self._criar_card()
        self.grid_acesso = QGridLayout()
        self.grid_acesso.setHorizontalSpacing(16)
        self.grid_acesso.setVerticalSpacing(10)
        card_layout.addLayout(self.grid_acesso)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("exemplo@email.com")
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Digite o login")
        self.senha_input = QLineEdit()
        self.senha_input.setEchoMode(QLineEdit.Password)
        self.confirmar_senha_input = QLineEdit()
        self.confirmar_senha_input.setEchoMode(QLineEdit.Password)

        self.nivel_input = QComboBox()
        self.nivel_input.addItem("Usuário", "usuario")
        self.nivel_input.addItem("Admin", "admin")

        self.lbl_email = self._adicionar_campo(
            "email", self.grid_acesso, "E-mail", self.email_input, obrigatorio=True
        )
        self.lbl_login = self._adicionar_campo(
            "login", self.grid_acesso, "Login", self.login_input, obrigatorio=True
        )
        self.lbl_senha = self._adicionar_campo(
            "senha", self.grid_acesso, "Senha", self.senha_input, obrigatorio=True
        )
        self.lbl_confirmar_senha = self._adicionar_campo(
            "confirmar_senha",
            self.grid_acesso,
            "Confirmar senha",
            self.confirmar_senha_input,
            obrigatorio=True,
        )
        self.lbl_nivel = self._adicionar_campo(
            "nivel", self.grid_acesso, "Nível de acesso", self.nivel_input
        )
        self._campos_acesso = [
            "email", "login", "senha", "confirmar_senha", "nivel"
        ]

        self.lbl_password_policy = QLabel()
        self.lbl_password_policy.setObjectName("secondary")
        self.lbl_password_policy.setWordWrap(True)
        card_layout.addWidget(self.lbl_password_policy)
        return card

    def _criar_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 16)
        card_layout.setSpacing(12)

        titulo = QLabel()
        titulo.setObjectName("panelTitle")
        card_layout.addWidget(titulo)
        return card, card_layout, titulo

    def _adicionar_campo(self, chave, grid, texto, widget, obrigatorio=False):
        container = QWidget()
        container.setAttribute(Qt.WA_StyledBackground, False)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        campo_layout = QVBoxLayout(container)
        campo_layout.setContentsMargins(0, 0, 0, 0)
        campo_layout.setSpacing(4)

        label = QLabel()
        label.setProperty("baseText", texto)
        label.setProperty("required", obrigatorio)
        campo_layout.addWidget(label)
        campo_layout.addWidget(widget)

        erro = QLabel()
        erro.setObjectName("negativo")
        erro.setWordWrap(True)
        erro.hide()
        campo_layout.addWidget(erro)

        self._field_containers[chave] = container
        self._error_labels[chave] = erro
        self._focus_widgets[chave] = widget
        grid.addWidget(container, 0, 0)
        return label

    def _criar_rodape(self):
        footer = QFrame()
        footer.setObjectName("profileFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 12, 8, 0)
        footer_layout.setSpacing(10)

        self.lbl_obrigatorios = QLabel()
        self.lbl_obrigatorios.setObjectName("muted")
        self.btn_cancelar = QPushButton()
        self.btn_cancelar.setObjectName("secondaryButton")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_salvar = QPushButton()
        self.btn_salvar.setObjectName("primaryButton")
        self.btn_salvar.clicked.connect(self.salvar_usuario)

        self._definir_icone_botao(self.btn_cancelar, "cancel")
        self._definir_icone_botao(self.btn_salvar, "register")

        footer_layout.addWidget(self.lbl_obrigatorios)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_cancelar)
        footer_layout.addWidget(self.btn_salvar)
        return footer

    def _configurar_icones_senha(self):
        self.senha_toggle_action = self.senha_input.addAction(
            self._icone("eye"), QLineEdit.TrailingPosition
        )
        self.confirmar_senha_toggle_action = self.confirmar_senha_input.addAction(
            self._icone("eye"), QLineEdit.TrailingPosition
        )
        self.senha_toggle_action.triggered.connect(
            lambda: self._alternar_visibilidade_senha(
                self.senha_input, self.senha_toggle_action
            )
        )
        self.confirmar_senha_toggle_action.triggered.connect(
            lambda: self._alternar_visibilidade_senha(
                self.confirmar_senha_input, self.confirmar_senha_toggle_action
            )
        )

    # ==================================================
    # TEXTOS E RESPONSIVIDADE
    # ==================================================
    def _atualizar_textos(self, *_):
        edicao = self._modo == self.MODO_EDICAO
        titulo = "Editar usuário" if edicao else "Novo usuário"
        subtitulo = (
            "Atualize os dados pessoais e o acesso ao sistema."
            if edicao
            else "Cadastre os dados pessoais e o acesso ao sistema."
        )
        texto_salvar = "Salvar alterações" if edicao else "Cadastrar usuário"

        self.setWindowTitle(TranslatorApp.get(titulo))
        self.lbl_titulo.setText(TranslatorApp.get(titulo))
        self.lbl_subtitulo.setText(TranslatorApp.get(subtitulo))
        self.lbl_card_pessoais.setText(TranslatorApp.get("Dados pessoais"))
        self.lbl_card_acesso.setText(TranslatorApp.get("Acesso ao sistema"))

        textos = {
            "nome": "Nome",
            "nascimento": "Data de nascimento",
            "sexo": "Sexo",
            "cpf": "CPF",
            "telefone": "Telefone",
            "celular": "Celular",
            "email": "E-mail",
            "login": "Login",
            "senha": "Senha",
            "confirmar_senha": "Confirmar senha",
            "nivel": "Nível de acesso",
        }
        for chave, texto in textos.items():
            label = self._field_containers[chave].layout().itemAt(0).widget()
            obrigatorio = bool(label.property("required"))
            if edicao and chave in {"senha", "confirmar_senha"}:
                obrigatorio = False
            sufixo = " *" if obrigatorio else ""
            label.setText(TranslatorApp.get(texto) + sufixo)

        self.sexo_input.setItemText(0, TranslatorApp.get("Masculino"))
        self.sexo_input.setItemText(1, TranslatorApp.get("Feminino"))
        self.sexo_input.setItemText(2, TranslatorApp.get("Outro"))
        self.nivel_input.setItemText(0, TranslatorApp.get("Usuário"))
        self.nivel_input.setItemText(1, TranslatorApp.get("Admin"))

        if edicao:
            self.senha_input.setPlaceholderText(
                TranslatorApp.get("Deixe em branco para manter a senha atual")
            )
            self.confirmar_senha_input.setPlaceholderText(
                TranslatorApp.get("Confirme a nova senha")
            )
        else:
            self.senha_input.setPlaceholderText(TranslatorApp.get("Digite a senha"))
            self.confirmar_senha_input.setPlaceholderText(
                TranslatorApp.get("Confirme a senha")
            )

        self.lbl_obrigatorios.setText(TranslatorApp.get("* Campos obrigatórios"))
        self.lbl_password_policy.setText(
            TranslatorApp.get(
                "Segurança: use de 8 a 128 caracteres. Frases-senha longas são recomendadas."
            )
        )
        self.btn_cancelar.setText(TranslatorApp.get("Cancelar"))
        self.btn_salvar.setText(TranslatorApp.get(texto_salvar))
        self.senha_toggle_action.setToolTip(TranslatorApp.get("Mostrar senha"))
        self.confirmar_senha_toggle_action.setToolTip(
            TranslatorApp.get("Mostrar confirmação de senha")
        )

    def _aplicar_layout_responsivo(self, force=False):
        largura = self.scroll_area.viewport().width() if self.scroll_area else self.width()
        compacto = largura < self.LIMITE_LAYOUT_COMPACTO
        if not force and compacto == self._layout_compacto:
            return
        self._layout_compacto = compacto

        self._reorganizar_grid(
            self.grid_pessoais, self._campos_pessoais, 1 if compacto else 2
        )
        self._reorganizar_grid(
            self.grid_acesso, self._campos_acesso, 1 if compacto else 2
        )

    def _reorganizar_grid(self, grid, chaves, colunas):
        for chave in chaves:
            grid.removeWidget(self._field_containers[chave])
        for indice, chave in enumerate(chaves):
            linha, coluna = divmod(indice, colunas)
            grid.addWidget(self._field_containers[chave], linha, coluna)
        for coluna in range(2):
            grid.setColumnStretch(coluna, 1 if coluna < colunas else 0)

    # ==================================================
    # MODO E DADOS
    # ==================================================
    def preencher_dados(self, usuario):
        if not usuario:
            return

        self.usuario_edicao = usuario
        self._modo = self.MODO_EDICAO
        self.senha_input.clear()
        self.confirmar_senha_input.clear()

        self.nome_input.setText(usuario.get("Nome", "") or "")
        self.cpf_input.setText(usuario.get("CPF", "") or "")
        self.telefone_input.setText(usuario.get("Telefone", "") or "")
        self.celular_input.setText(usuario.get("Celular", "") or "")
        self.email_input.setText(usuario.get("Email", "") or "")
        self.login_input.setText(usuario.get("Login", "") or "")

        data = QDate.fromString(
            usuario.get("DataNascimento", "") or "", "yyyy-MM-dd"
        )
        if data.isValid():
            self.nascimento_input.setDate(data)

        self._selecionar_combo_por_data(self.sexo_input, usuario.get("Sexo"))
        self._selecionar_combo_por_data(
            self.nivel_input, usuario.get("Nivel_Acesso")
        )
        self._limpar_erros()
        self._atualizar_textos()

    @staticmethod
    def _selecionar_combo_por_data(combo, valor):
        index = combo.findData(valor)
        if index >= 0:
            combo.setCurrentIndex(index)

    # ==================================================
    # VALIDAÇÃO E PERSISTÊNCIA
    # ==================================================
    def _validar_formulario(self):
        self._limpar_erros()
        primeiro_invalido = None

        def invalido(chave, mensagem):
            nonlocal primeiro_invalido
            self._mostrar_erro(chave, mensagem)
            if primeiro_invalido is None:
                primeiro_invalido = chave

        nome = self.nome_input.text().strip()
        email = self.email_input.text().strip()
        login = self.login_input.text().strip()
        senha = self.senha_input.text()
        confirmacao = self.confirmar_senha_input.text()

        if not nome:
            invalido("nome", "Informe o nome do usuário.")
        if not email:
            invalido("email", "Informe o e-mail.")
        elif not self.EMAIL_PATTERN.fullmatch(email):
            invalido("email", "Informe um e-mail válido.")
        if not login:
            invalido("login", "Informe o login.")

        if self._modo == self.MODO_CADASTRO:
            if not senha:
                invalido("senha", "Informe a senha.")
            else:
                erro_senha = self.controller.password_validation_error(senha)
                if erro_senha:
                    invalido("senha", erro_senha)
            if not confirmacao:
                invalido("confirmar_senha", "Confirme a senha.")
            elif senha and senha != confirmacao:
                invalido("confirmar_senha", "As senhas não coincidem.")
        elif senha or confirmacao:
            if not senha:
                invalido("senha", "Informe a nova senha.")
            else:
                erro_senha = self.controller.password_validation_error(senha)
                if erro_senha:
                    invalido("senha", erro_senha)
            if not confirmacao:
                invalido("confirmar_senha", "Confirme a nova senha.")
            elif senha and senha != confirmacao:
                invalido("confirmar_senha", "As senhas não coincidem.")

        if primeiro_invalido is not None:
            widget = self._focus_widgets[primeiro_invalido]
            self.scroll_area.ensureWidgetVisible(
                self._field_containers[primeiro_invalido], 20, 20
            )
            widget.setFocus(Qt.OtherFocusReason)
            return False
        return True

    def _mostrar_erro(self, chave, mensagem):
        label = self._error_labels[chave]
        label.setText(TranslatorApp.get(mensagem))
        label.show()
        widget = self._focus_widgets[chave]
        widget.setProperty("invalid", True)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _limpar_erros(self):
        for chave, label in self._error_labels.items():
            label.clear()
            label.hide()
            widget = self._focus_widgets[chave]
            widget.setProperty("invalid", False)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def salvar_usuario(self):
        if not self._validar_formulario():
            return

        dados = {
            "Nome": self.nome_input.text().strip(),
            "DataNascimento": self.nascimento_input.date().toString("yyyy-MM-dd"),
            "Sexo": self.sexo_input.currentData(),
            "CPF": self.cpf_input.text().strip(),
            "Telefone": self.telefone_input.text().strip(),
            "Celular": self.celular_input.text().strip(),
            "Email": self.email_input.text().strip(),
            "Login": self.login_input.text().strip(),
            "Senha": self.senha_input.text(),
            "Nivel_Acesso": self.nivel_input.currentData(),
        }

        try:
            if self._modo == self.MODO_EDICAO and self.usuario_edicao:
                sucesso = self.controller.update_user(
                    self.usuario_edicao["ID_Usuario"], dados
                )
                mensagem_sucesso = "Usuário atualizado com sucesso"
            else:
                sucesso = self.controller.register_user(dados)
                mensagem_sucesso = "Usuário cadastrado com sucesso"

            if sucesso:
                QMessageBox.information(
                    self,
                    TranslatorApp.get("Sucesso"),
                    TranslatorApp.get(mensagem_sucesso),
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Usuário Existente"),
                    TranslatorApp.get(
                        "Já existe um usuário com este login ou e-mail"
                    ),
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                f"{TranslatorApp.get('Erro ao cadastrar usuário')}:\n{exc}",
            )

    # ==================================================
    # ÍCONES E CICLO DE VIDA
    # ==================================================
    @staticmethod
    def _icone(nome):
        caminho = IonPath.resource("assets", "icons", f"{nome}.svg")
        return QIcon(caminho) if caminho else QIcon()

    def _definir_icone_label(self, label, nome, tamanho):
        icone = self._icone(nome)
        if not icone.isNull():
            label.setText("")
            label.setPixmap(icone.pixmap(tamanho, tamanho))

    def _definir_icone_botao(self, botao, nome):
        icone = self._icone(nome)
        if not icone.isNull():
            botao.setIcon(icone)

    def _alternar_visibilidade_senha(self, campo, action):
        visivel = campo.echoMode() == QLineEdit.Normal
        campo.setEchoMode(QLineEdit.Password if visivel else QLineEdit.Normal)
        action.setIcon(self._icone("eye" if visivel else "eye_off"))
        action.setToolTip(
            TranslatorApp.get("Mostrar senha" if visivel else "Ocultar senha")
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._aplicar_layout_responsivo)

    def showEvent(self, event):
        super().showEvent(event)
        WindowManager.fit_dialog(self, self.parentWidget())
        QTimer.singleShot(0, lambda: self._aplicar_layout_responsivo(force=True))

    def closeEvent(self, event):
        try:
            TranslatorApp.unbind(self)
        except Exception:
            pass
        super().closeEvent(event)
