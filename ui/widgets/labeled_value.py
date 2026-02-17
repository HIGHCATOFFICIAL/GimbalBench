"""Label + value + unit display widget."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from ui.styles import SUBTEXT0, TEXT


class LabeledValue(QWidget):
    """Displays a label, a value, and an optional unit."""

    def __init__(self, label: str, unit: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel(label + ":")
        self._label.setStyleSheet(f"color: {SUBTEXT0}; font-size: 12px;")
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._value = QLabel("---")
        self._value.setStyleSheet(f"color: {TEXT}; font-weight: bold; font-size: 13px;")
        self._value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._value.setMinimumWidth(60)

        layout.addWidget(self._label)
        layout.addWidget(self._value)

        if unit:
            self._unit_label = QLabel(unit)
            self._unit_label.setStyleSheet(f"color: {SUBTEXT0}; font-size: 11px;")
            layout.addWidget(self._unit_label)
        else:
            self._unit_label = None

        layout.addStretch()

    def set_value(self, value, color: str | None = None):
        if isinstance(value, float):
            self._value.setText(f"{value:.1f}")
        else:
            self._value.setText(str(value))
        if color:
            self._value.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
        else:
            self._value.setStyleSheet(f"color: {TEXT}; font-weight: bold; font-size: 13px;")
