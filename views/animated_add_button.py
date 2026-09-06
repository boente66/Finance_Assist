# -*- coding: utf-8 -*-
"""Componente visual reutilizável para ações rápidas de inclusão."""

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton


class AnimatedAddButton(QPushButton):
    """Botão circular cujo feedback não interfere na regra de negócio."""

    def __init__(self, tooltip, icon=None, parent=None):
        super().__init__(parent)
        self.setObjectName("circularAddButton")
        self.setText("+")
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(36, 36)

        if isinstance(icon, QIcon) and not icon.isNull():
            self.setIcon(icon)
            self.setText("")

        self.setIconSize(QSize(17, 17))
        self._hover_animation = QPropertyAnimation(self, b"iconSize", self)
        self._hover_animation.setDuration(150)
        self._hover_animation.setStartValue(QSize(17, 17))
        self._hover_animation.setEndValue(QSize(21, 21))
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

    def enterEvent(self, event):
        self._hover_animation.setDirection(QPropertyAnimation.Forward)
        self._hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_animation.setDirection(QPropertyAnimation.Backward)
        self._hover_animation.start()
        super().leaveEvent(event)
