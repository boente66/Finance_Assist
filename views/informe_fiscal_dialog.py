from datetime import date

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel,
    QComboBox, QLineEdit, QMessageBox, QScrollArea, QSpinBox, QTextEdit, QVBoxLayout,
    QWidget,
)

from core.translator_app import TranslatorApp


class InformeFiscalDialog(QDialog):
    """Cadastro explícito dos valores entregues pela fonte pagadora."""

    CAMPOS = (
        ('Rendimentos_Tributaveis', 'Rendimentos tributáveis (inclusive férias)'),
        ('Previdencia_Oficial', 'Contribuição previdenciária oficial'),
        ('Previdencia_Complementar', 'Previdência complementar'),
        ('Pensao_Alimenticia', 'Pensão alimentícia'),
        ('IRRF', 'Imposto de renda retido na fonte'),
        ('Parcela_Isenta_65', 'Parcela isenta (65 anos ou mais)'),
        ('Diarias_Ajudas_Custo', 'Diárias e ajudas de custo'),
        ('Pensao_Molestia_Grave', 'Pensão/proventos por moléstia grave'),
        ('Lucros_Dividendos', 'Lucros e dividendos'),
        ('Valores_Empresario', 'Valores pagos a titular/sócio de ME ou EPP'),
        ('Indenizacoes', 'Indenizações por rescisão ou acidente de trabalho'),
        ('Isentos_Outros', 'Outros rendimentos isentos'),
        ('Decimo_Terceiro', 'Décimo terceiro salário'),
        ('IRRF_Decimo_Terceiro', 'IRRF sobre décimo terceiro'),
        ('Exclusivos_Outros', 'Outros rendimentos exclusivos'),
        ('RRA_Rendimentos', 'RRA — rendimentos tributáveis'),
        ('RRA_Previdencia_Oficial', 'RRA — previdência oficial'),
        ('RRA_Pensao_Alimenticia', 'RRA — pensão alimentícia'),
        ('RRA_IRRF', 'RRA — imposto retido'),
        ('RRA_Despesas_Judiciais', 'RRA — despesas com ação judicial'),
    )

    def __init__(self, controller, ano=None, dados=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle(TranslatorApp.get('Dados fiscais da fonte pagadora'))
        self.resize(620, 700)
        root = QVBoxLayout(self)
        aviso = QLabel(TranslatorApp.get(
            'Transcreva os valores do comprovante recebido da fonte pagadora. '
            'O Finance Assist não calcula nem presume tributação a partir do extrato.'
        ))
        aviso.setObjectName('infoLabel')
        aviso.setWordWrap(True)
        root.addWidget(aviso)
        area = QScrollArea()
        area.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        self.ano = QSpinBox()
        self.ano.setRange(1900, 9999)
        self.ano.setValue(int(ano or date.today().year))
        self.fonte_nome = QLineEdit()
        self.fonte_documento = QLineEdit()
        self.fonte_documento.setPlaceholderText('CPF ou CNPJ')
        self.natureza = QLineEdit()
        form.addRow(TranslatorApp.get('Ano-calendário:'), self.ano)
        form.addRow(TranslatorApp.get('Fonte pagadora:'), self.fonte_nome)
        form.addRow(TranslatorApp.get('CPF/CNPJ da fonte:'), self.fonte_documento)
        form.addRow(TranslatorApp.get('Natureza do rendimento:'), self.natureza)
        self.valores = {}
        self.rra_meses = QSpinBox()
        self.rra_meses.setRange(0, 999)
        form.addRow(TranslatorApp.get('RRA — número de meses:'), self.rra_meses)
        self.rra_tributacao = QComboBox()
        self.rra_tributacao.addItem(
            TranslatorApp.get('Exclusiva na fonte'), 'EXCLUSIVA'
        )
        self.rra_tributacao.addItem(
            TranslatorApp.get('Ajuste anual'), 'AJUSTE_ANUAL'
        )
        form.addRow(TranslatorApp.get('RRA — tributação:'), self.rra_tributacao)
        for chave, rotulo in self.CAMPOS:
            campo = QDoubleSpinBox()
            campo.setRange(0, 999_999_999.99)
            campo.setDecimals(2)
            campo.setPrefix('R$ ')
            campo.setGroupSeparatorShown(True)
            self.valores[chave] = campo
            form.addRow(TranslatorApp.get(rotulo + ':'), campo)
        self.complementares = QTextEdit()
        self.complementares.setMaximumHeight(100)
        form.addRow(TranslatorApp.get('Informações complementares:'), self.complementares)
        area.setWidget(content)
        root.addWidget(area, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.salvar)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        if dados:
            self._preencher(dados)

    def _preencher(self, dados):
        self.ano.setValue(int(dados.get('Ano_Calendario') or self.ano.value()))
        self.fonte_nome.setText(dados.get('Fonte_Nome') or '')
        self.fonte_documento.setText(dados.get('Fonte_Documento') or '')
        self.natureza.setText(dados.get('Natureza_Rendimento') or '')
        self.rra_meses.setValue(int(dados.get('RRA_Meses') or 0))
        index = self.rra_tributacao.findData(
            dados.get('RRA_Tributacao') or 'EXCLUSIVA'
        )
        if index >= 0:
            self.rra_tributacao.setCurrentIndex(index)
        for chave, campo in self.valores.items():
            campo.setValue(float(dados.get(chave) or 0))
        self.complementares.setPlainText(
            dados.get('Informacoes_Complementares') or ''
        )

    def salvar(self):
        dados = {
            'Ano_Calendario': self.ano.value(),
            'Fonte_Nome': self.fonte_nome.text(),
            'Fonte_Documento': self.fonte_documento.text(),
            'Natureza_Rendimento': self.natureza.text(),
            'Informacoes_Complementares': self.complementares.toPlainText(),
            'RRA_Meses': self.rra_meses.value(),
            'RRA_Tributacao': self.rra_tributacao.currentData(),
        }
        dados.update({chave: campo.value() for chave, campo in self.valores.items()})
        try:
            self.controller.salvar_informe_fiscal(dados)
        except Exception as exc:
            QMessageBox.warning(self, TranslatorApp.get('Dados inválidos'), str(exc))
            return
        self.accept()
