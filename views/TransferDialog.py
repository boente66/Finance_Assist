import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QMessageBox,
    QDateEdit,
)
from PyQt5.QtCore import QDate

from controllers.transaction_controller import TransactionController
from controllers.account_controller import AccountController

from core.translator_app import TranslatorApp


logger = logging.getLogger(__name__)


class TransferDialog(QDialog):
    """
    Diálogo responsável por coletar dados da UI
    e delegar a transferência ao controller.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.transaction_controller = TransactionController()
        self.account_controller = AccountController()

        self.setMinimumWidth(320)
        self.setWindowTitle("Transferir Saldo")

        self._init_ui()
        self._carregar_contas()

        # 🔥 precisa (labels + combos dinâmicos)
        TranslatorApp.bind(self._on_translate,self)
        self._on_translate()

    # --------------------------------------------------
    # REATIVIDADE
    # --------------------------------------------------
    def _on_translate(self, *_):

        self.setWindowTitle(TranslatorApp.get("Transferir Saldo"))

        self.lbl_origem.setText(TranslatorApp.get("Conta de origem"))
        self.lbl_destino.setText(TranslatorApp.get("Conta de destino"))
        self.lbl_valor.setText(TranslatorApp.get("Valor"))
        self.lbl_data.setText(TranslatorApp.get("Data"))
        self.btn_transferir.setText(TranslatorApp.get("Transferir"))

        self._carregar_contas()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ORIGEM
        self.lbl_origem = QLabel()
        layout.addWidget(self.lbl_origem)

        self.origem_combo = QComboBox()
        layout.addWidget(self.origem_combo)

        # DESTINO
        self.lbl_destino = QLabel()
        layout.addWidget(self.lbl_destino)

        self.destino_combo = QComboBox()
        layout.addWidget(self.destino_combo)

        # VALOR
        self.lbl_valor = QLabel()
        layout.addWidget(self.lbl_valor)

        self.valor_input = QDoubleSpinBox()
        self.valor_input.setRange(0.01, 1_000_000.00)
        self.valor_input.setDecimals(2)
        layout.addWidget(self.valor_input)

        # DATA
        self.lbl_data = QLabel()
        layout.addWidget(self.lbl_data)

        self.data_input = QDateEdit(QDate.currentDate())
        self.data_input.setCalendarPopup(True)
        layout.addWidget(self.data_input)

        # BOTÃO
        self.btn_transferir = QPushButton()
        self.btn_transferir.clicked.connect(self._transferir)
        layout.addWidget(self.btn_transferir)

    # --------------------------------------------------
    # DADOS
    # --------------------------------------------------
    def _carregar_contas(self):
        self.origem_combo.clear()
        self.destino_combo.clear()

        contas = self.account_controller.get_all_accounts()

        for conta in contas:
            saldo = float(conta.get("Saldo_Atual", 0))

            texto = (
                f"{conta.get('Nome_Conta')} "
                f"({TranslatorApp.get('Saldo')}: {saldo:,.2f})"
            )

            # formato BR
            texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

            self.origem_combo.addItem(texto, conta["ID_Conta"])
            self.destino_combo.addItem(texto, conta["ID_Conta"])

    # --------------------------------------------------
    # AÇÃO
    # --------------------------------------------------
    def _transferir(self):

        id_origem = self.origem_combo.currentData()
        id_destino = self.destino_combo.currentData()
        valor = self.valor_input.value()
        data = self.data_input.date().toString("yyyy-MM-dd")

        if id_origem == id_destino:
            QMessageBox.warning(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Selecione contas diferentes."),
            )
            return

        if valor <= 0:
            QMessageBox.warning(
                self, TranslatorApp.get("Erro"), TranslatorApp.get("Valor inválido.")
            )
            return

        try:
            resultado = self.transaction_controller.transferir_saldo(
                id_origem=id_origem, id_destino=id_destino, valor=valor, data=data
            )

            if not resultado.get("sucesso"):
                QMessageBox.warning(
                    self,
                    TranslatorApp.get("Atenção"),
                    TranslatorApp.get(
                        resultado.get(
                            "mensagem",
                            "Não foi possível realizar a transferência."
                        )
                    )
                )
                return

            QMessageBox.information(
                self,
                TranslatorApp.get("Sucesso"),
                TranslatorApp.get(
                    resultado.get(
                        "mensagem",
                        "Transferência realizada com sucesso."
                    )
                ),
            )

            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, TranslatorApp.get("Atenção"), str(e))

        except Exception:
            logger.exception("Erro ao transferir saldo")
            QMessageBox.critical(
                self,
                TranslatorApp.get("Erro"),
                TranslatorApp.get("Erro inesperado ao realizar transferência."),
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
