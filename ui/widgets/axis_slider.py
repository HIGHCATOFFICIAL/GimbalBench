"""Axis control slider with spinbox and actual angle readout."""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QSlider, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles import SUBTEXT0, TEXT, BLUE


class AxisSlider(QWidget):
    """Slider + spinbox + actual angle readout for one axis."""

    value_changed = pyqtSignal(float)

    def __init__(self, label: str, min_val: float = -90, max_val: float = 90,
                 center_return: bool = False, parent=None):
        super().__init__(parent)
        self._center_return = center_return
        self._min = min_val
        self._max = max_val

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Label
        self._label = QLabel(label)
        self._label.setMinimumWidth(50)
        self._label.setStyleSheet(f"color: {SUBTEXT0}; font-weight: bold;")
        layout.addWidget(self._label)

        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(int(min_val * 10), int(max_val * 10))
        self._slider.setValue(0)
        self._slider.setTickInterval(int((max_val - min_val) * 10 / 8))
        layout.addWidget(self._slider, stretch=1)

        # Spinbox
        self._spinbox = QDoubleSpinBox()
        self._spinbox.setRange(min_val, max_val)
        self._spinbox.setDecimals(1)
        self._spinbox.setSingleStep(1.0)
        self._spinbox.setValue(0.0)
        self._spinbox.setFixedWidth(80)
        layout.addWidget(self._spinbox)

        # Actual value readout
        right_col = QVBoxLayout()
        right_col.setSpacing(0)
        self._actual_label = QLabel("Actual:")
        self._actual_label.setStyleSheet(f"color: {SUBTEXT0}; font-size: 10px;")
        self._actual_value = QLabel("---")
        self._actual_value.setStyleSheet(f"color: {BLUE}; font-weight: bold; font-size: 12px;")
        self._actual_value.setMinimumWidth(55)
        right_col.addWidget(self._actual_label)
        right_col.addWidget(self._actual_value)
        layout.addLayout(right_col)

        # Connect signals
        self._slider.valueChanged.connect(self._on_slider_changed)
        self._spinbox.valueChanged.connect(self._on_spinbox_changed)

        if center_return:
            self._slider.sliderReleased.connect(self._on_slider_released)

        self._updating = False

    def _on_slider_changed(self, value: int):
        if self._updating:
            return
        self._updating = True
        fval = value / 10.0
        self._spinbox.setValue(fval)
        self._updating = False
        self.value_changed.emit(fval)

    def _on_spinbox_changed(self, value: float):
        if self._updating:
            return
        self._updating = True
        self._slider.setValue(int(value * 10))
        self._updating = False
        self.value_changed.emit(value)

    def _on_slider_released(self):
        """Return to center when released (for rate mode)."""
        self._updating = True
        self._slider.setValue(0)
        self._spinbox.setValue(0.0)
        self._updating = False
        self.value_changed.emit(0.0)

    def set_actual(self, value: float):
        self._actual_value.setText(f"{value:.1f}")

    def value(self) -> float:
        return self._spinbox.value()

    def reset(self):
        self._updating = True
        self._slider.setValue(0)
        self._spinbox.setValue(0.0)
        self._updating = False
