"""Motor health tab with per-axis cards, system checks, and overall verdict."""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QGridLayout, QLabel, QProgressBar, QPushButton,
                              QScrollArea)
from PyQt6.QtCore import Qt

from core.health_checker import (analyze_health, HealthReport, AxisHealth,
                                  MOTOR_POWER_CRIT, BALANCE_ERROR_CRIT)
from ui.widgets.led_indicator import LedIndicator
from ui.styles import (COLOR_OK, COLOR_WARN, COLOR_FAIL, TEXT, SUBTEXT0,
                        SURFACE0, GREEN, YELLOW, RED)


STATUS_COLORS = {
    "OK": "green",
    "WARN": "yellow",
    "FAIL": "red",
}


class AxisCard(QGroupBox):
    """Health card for one axis."""

    def __init__(self, axis_name: str, parent=None):
        super().__init__(axis_name, parent)
        layout = QGridLayout(self)

        # Motor power
        layout.addWidget(QLabel("Motor Power:"), 0, 0)
        self._power_bar = QProgressBar()
        self._power_bar.setRange(0, 255)
        self._power_bar.setTextVisible(True)
        layout.addWidget(self._power_bar, 0, 1)
        self._power_led = LedIndicator("gray", 12)
        layout.addWidget(self._power_led, 0, 2)

        # Balance error
        layout.addWidget(QLabel("Balance Error:"), 1, 0)
        self._balance_bar = QProgressBar()
        self._balance_bar.setRange(0, 100)
        self._balance_bar.setTextVisible(True)
        layout.addWidget(self._balance_bar, 1, 1)
        self._balance_led = LedIndicator("gray", 12)
        layout.addWidget(self._balance_led, 1, 2)

        # Stator-Rotor
        layout.addWidget(QLabel("Stator-Rotor:"), 2, 0)
        self._stator_label = QLabel("---")
        self._stator_label.setStyleSheet(f"color: {TEXT}; font-weight: bold;")
        layout.addWidget(self._stator_label, 2, 1)

        # Motor output
        layout.addWidget(QLabel("Motor Output:"), 3, 0)
        self._output_label = QLabel("---")
        self._output_label.setStyleSheet(f"color: {TEXT}; font-weight: bold;")
        layout.addWidget(self._output_label, 3, 1)

    def update_data(self, ax: AxisHealth):
        self._power_bar.setValue(ax.motor_power)
        self._power_bar.setFormat(f"{ax.motor_power}")
        self._power_led.set_color(STATUS_COLORS.get(ax.power_status, "gray"))

        self._balance_bar.setValue(min(ax.balance_error, 100))
        self._balance_bar.setFormat(f"{ax.balance_error}")
        self._balance_led.set_color(STATUS_COLORS.get(ax.balance_status, "gray"))

        self._stator_label.setText(str(ax.stator_rotor_angle))
        self._output_label.setText(str(ax.motor_out))

        # Color the progress bars
        if ax.power_status == "FAIL":
            self._power_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {RED}; }}")
        elif ax.power_status == "WARN":
            self._power_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {YELLOW}; }}")
        else:
            self._power_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {GREEN}; }}")

        if ax.balance_status == "FAIL":
            self._balance_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {RED}; }}")
        elif ax.balance_status == "WARN":
            self._balance_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {YELLOW}; }}")
        else:
            self._balance_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {GREEN}; }}")


class MotorHealthTab(QWidget):
    """Motor health analysis with per-axis cards and system checks."""

    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)

        # Overall verdict
        verdict_layout = QHBoxLayout()
        verdict_layout.addWidget(QLabel("Overall Verdict:"))
        self._verdict_led = LedIndicator("gray", 20)
        verdict_layout.addWidget(self._verdict_led)
        self._verdict_label = QLabel("No Data")
        self._verdict_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {SUBTEXT0};")
        verdict_layout.addWidget(self._verdict_label)
        verdict_layout.addStretch()
        layout.addLayout(verdict_layout)

        # Axis cards
        cards_layout = QHBoxLayout()
        self._axis_cards = {}
        for axis in ["Roll", "Pitch", "Yaw"]:
            card = AxisCard(axis)
            cards_layout.addWidget(card)
            self._axis_cards[axis] = card
        layout.addLayout(cards_layout)

        # System checks
        sys_group = QGroupBox("System Checks")
        sys_grid = QGridLayout(sys_group)
        self._sys_checks = {}

        checks = [
            ("System Error", "system_status"),
            ("I2C Bus", "i2c_status"),
            ("Cycle Time", "cycle_status"),
            ("Battery", "battery_status"),
            ("Temperature", "temp_status"),
        ]
        for i, (label, key) in enumerate(checks):
            lbl = QLabel(label + ":")
            lbl.setStyleSheet(f"color: {SUBTEXT0};")
            sys_grid.addWidget(lbl, i, 0)

            led = LedIndicator("gray", 12)
            sys_grid.addWidget(led, i, 1)

            val = QLabel("---")
            val.setStyleSheet(f"color: {TEXT};")
            sys_grid.addWidget(val, i, 2)

            self._sys_checks[key] = (led, val)

        layout.addWidget(sys_group)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._last_report = None

    def update_telemetry(self, data):
        """Analyze telemetry and update health display."""
        report = analyze_health(data)
        self._last_report = report

        # Overall verdict
        verdict_colors = {"PASS": "green", "WARNING": "yellow", "FAIL": "red"}
        self._verdict_led.set_color(verdict_colors.get(report.overall, "gray"))
        self._verdict_label.setText(report.overall)
        label_colors = {"PASS": COLOR_OK, "WARNING": COLOR_WARN, "FAIL": COLOR_FAIL}
        self._verdict_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {label_colors.get(report.overall, SUBTEXT0)};"
        )

        # Axis cards
        for ax in report.axes:
            if ax.name in self._axis_cards:
                self._axis_cards[ax.name].update_data(ax)

        # System checks
        sys = report.system
        self._update_check("system_status", sys.system_status,
                           f"Error: {sys.system_error} Sub: {sys.system_sub_error}")
        self._update_check("i2c_status", sys.i2c_status,
                           f"{sys.i2c_errors} errors, {sys.serial_errors} serial errs")
        self._update_check("cycle_status", sys.cycle_status,
                           f"{sys.cycle_time} us")
        self._update_check("battery_status", sys.battery_status,
                           f"Level: {sys.battery}")
        self._update_check("temp_status", sys.temp_status,
                           f"IMU: {sys.imu_temperature} C")

    def _update_check(self, key: str, status: str, detail: str):
        if key in self._sys_checks:
            led, val = self._sys_checks[key]
            led.set_color(STATUS_COLORS.get(status, "gray"))
            val.setText(f"{status} - {detail}")
