from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QCalendarWidget,
    QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt
from core.window_manager import WindowManager


class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Selecionar intervalo de datas")
        self.setMinimumSize(420, 360)
        self.resize(760, 440)

        # --------------------------
        # Layout principal
        # --------------------------
        layout = QVBoxLayout(self)

        title = QLabel("Selecione a Data Inicial e Final")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --------------------------
        # Calendários
        # --------------------------
        self.cal_layout = QGridLayout()

        self.calendar_start = QCalendarWidget()
        self.calendar_start.setGridVisible(True)

        self.calendar_end = QCalendarWidget()
        self.calendar_end.setGridVisible(True)

        self.cal_layout.addWidget(self.calendar_start, 0, 0)
        self.cal_layout.addWidget(self.calendar_end, 0, 1)

        layout.addLayout(self.cal_layout)

        # --------------------------
        # Botões
        # --------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        self.btn_ok = QPushButton("Confirmar")
        self.btn_cancel = QPushButton("Cancelar")

        self.btn_ok.clicked.connect(self.confirmar)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

        # Resultado
        self.data_inicial = None
        self.data_final = None

    def _aplicar_layout_responsivo(self):
        compacto = self.width() < 650
        self.cal_layout.removeWidget(self.calendar_start)
        self.cal_layout.removeWidget(self.calendar_end)
        self.cal_layout.addWidget(self.calendar_start, 0, 0)
        self.cal_layout.addWidget(
            self.calendar_end,
            1 if compacto else 0,
            0 if compacto else 1,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._aplicar_layout_responsivo()

    def showEvent(self, event):
        super().showEvent(event)
        WindowManager.fit_dialog(self, self.parentWidget())

    # ============================================
    # Validação e retorno
    # ============================================
    def confirmar(self):
        data_ini = self.calendar_start.selectedDate()
        data_fim = self.calendar_end.selectedDate()

        if data_ini > data_fim:
            QMessageBox.warning(
                self,
                "Intervalo inválido",
                "A data inicial não pode ser maior que a data final."
            )
            return

        self.data_inicial = data_ini.toString("yyyy-MM-dd")
        self.data_final = data_fim.toString("yyyy-MM-dd")

        self.accept()

    # ============================================
    # Método para obter o resultado no Controller
    # ============================================
    def get_date_range(self):
        return self.data_inicial, self.data_final
