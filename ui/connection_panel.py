"""Connection panel with Serial/UDP selector, port config, connect/disconnect."""
import glob
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QRadioButton, QComboBox, QLineEdit, QPushButton,
                              QCheckBox, QFrame, QButtonGroup)
from PyQt6.QtCore import pyqtSignal

from ui.widgets.led_indicator import LedIndicator
from ui.styles import SUBTEXT0, COLOR_WARN

DEFAULT_PORT = "/dev/ttyUSB0"


class ConnectionPanel(QWidget):
    """Top panel for configuring and managing gimbal connection."""

    connect_serial = pyqtSignal(str, int, bool)    # port, baud, auto_detect
    connect_udp = pyqtSignal(str, int, int)         # bridge_ip, bridge_port, pc_port
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Transport type
        self._serial_radio = QRadioButton("Serial")
        self._udp_radio = QRadioButton("UDP")
        self._serial_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self._serial_radio)
        group.addButton(self._udp_radio)
        self._serial_radio.toggled.connect(self._on_transport_changed)

        layout.addWidget(self._serial_radio)
        layout.addWidget(self._udp_radio)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(sep)

        # -- Serial config --
        self._serial_frame = QWidget()
        sl = QHBoxLayout(self._serial_frame)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)

        sl.addWidget(QLabel("Port:"))
        self._port_combo = QComboBox()
        self._port_combo.setEditable(True)
        self._port_combo.setMinimumWidth(150)
        # Set default before scanning
        self._port_combo.addItem(DEFAULT_PORT)
        self._port_combo.setCurrentText(DEFAULT_PORT)
        sl.addWidget(self._port_combo)

        refresh_btn = QPushButton("Scan")
        refresh_btn.setFixedWidth(65)
        refresh_btn.clicked.connect(self._refresh_ports)
        sl.addWidget(refresh_btn)

        sl.addWidget(QLabel("Baud:"))
        self._baud_combo = QComboBox()
        for b in ["115200", "230400", "57600", "38400", "19200", "9600"]:
            self._baud_combo.addItem(b)
        self._baud_combo.setCurrentText("115200")
        sl.addWidget(self._baud_combo)

        self._auto_detect_cb = QCheckBox("Auto-detect")
        self._auto_detect_cb.setToolTip("Scan available serial ports for SBGC device")
        sl.addWidget(self._auto_detect_cb)

        layout.addWidget(self._serial_frame)

        # -- UDP config --
        self._udp_frame = QWidget()
        ul = QHBoxLayout(self._udp_frame)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.setSpacing(6)

        ul.addWidget(QLabel("Bridge IP:"))
        self._ip_edit = QLineEdit("192.168.1.50")
        self._ip_edit.setFixedWidth(120)
        ul.addWidget(self._ip_edit)

        ul.addWidget(QLabel("Bridge Port:"))
        self._bridge_port_edit = QLineEdit("41000")
        self._bridge_port_edit.setFixedWidth(60)
        ul.addWidget(self._bridge_port_edit)

        ul.addWidget(QLabel("PC Port:"))
        self._pc_port_edit = QLineEdit("41001")
        self._pc_port_edit.setFixedWidth(60)
        ul.addWidget(self._pc_port_edit)

        layout.addWidget(self._udp_frame)
        self._udp_frame.hide()

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(sep2)

        # Connect / Disconnect buttons
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setObjectName("connectBtn")
        self._connect_btn.clicked.connect(self._on_connect)
        layout.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setObjectName("disconnectBtn")
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        layout.addWidget(self._disconnect_btn)

        # LED indicator
        self._led = LedIndicator("gray")
        layout.addWidget(self._led)

        self._status_label = QLabel("Disconnected")
        self._status_label.setStyleSheet(f"color: {SUBTEXT0};")
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _on_transport_changed(self, serial_checked: bool):
        self._serial_frame.setVisible(serial_checked)
        self._udp_frame.setVisible(not serial_checked)

    def _refresh_ports(self):
        current = self._port_combo.currentText()
        self._port_combo.clear()
        # Always include the default port first
        ports = [DEFAULT_PORT]
        # Add any other detected ports
        for p in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
            if p not in ports:
                ports.append(p)
        for p in ports:
            self._port_combo.addItem(p)
        # Restore previous selection if it's still in the list
        idx = self._port_combo.findText(current)
        if idx >= 0:
            self._port_combo.setCurrentIndex(idx)
        else:
            self._port_combo.setCurrentIndex(0)

    def _on_connect(self):
        self._connect_btn.setEnabled(False)
        self._status_label.setText("Connecting...")
        self._led.set_color("yellow")
        if self._serial_radio.isChecked():
            port = self._port_combo.currentText()
            baud = int(self._baud_combo.currentText())
            auto = self._auto_detect_cb.isChecked()
            self.connect_serial.emit(port, baud, auto)
        else:
            ip = self._ip_edit.text()
            bridge_port = int(self._bridge_port_edit.text())
            pc_port = int(self._pc_port_edit.text())
            self.connect_udp.emit(ip, bridge_port, pc_port)

    def _on_disconnect(self):
        self.disconnect_requested.emit()

    def set_connected(self, probed: bool = True):
        if probed:
            self._led.set_color("green")
            self._status_label.setText("Connected")
        else:
            self._led.set_color("yellow")
            self._status_label.setText("Port open (no gimbal response)")
        self._connect_btn.setEnabled(False)
        self._disconnect_btn.setEnabled(True)

    def set_disconnected(self):
        self._led.set_color("gray")
        self._status_label.setText("Disconnected")
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)

    def set_error(self, msg: str):
        self._led.set_color("red")
        self._status_label.setText(f"Error: {msg[:50]}")
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
