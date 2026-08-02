# -*- coding: utf-8 -*-
"""Layout de fluxo reutilizável para barras e filtros Qt."""

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtWidgets import QLayout, QSizePolicy, QStyle


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, horizontal_spacing=8, vertical_spacing=8):
        super().__init__(parent)
        self._items = []
        self._h_space = horizontal_spacing
        self._v_space = vertical_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Horizontal)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _spacing(self, orientation):
        explicit = self._h_space if orientation == Qt.Horizontal else self._v_space
        if explicit >= 0:
            return explicit
        parent = self.parentWidget()
        if parent is None:
            return 6
        metric = QStyle.PM_LayoutHorizontalSpacing if orientation == Qt.Horizontal else QStyle.PM_LayoutVerticalSpacing
        return parent.style().pixelMetric(metric, None, parent)

    def _do_layout(self, rect, test_only):
        x, y = rect.x(), rect.y()
        line_height = 0
        h_space = self._spacing(Qt.Horizontal)
        v_space = self._spacing(Qt.Vertical)
        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible() and not test_only:
                continue
            hint = item.sizeHint()
            next_x = x + hint.width() + h_space
            if next_x - h_space > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + v_space
                next_x = x + hint.width() + h_space
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()
