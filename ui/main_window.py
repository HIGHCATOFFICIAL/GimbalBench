"""Main application window with connection panel, tabs, and status bar."""
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget,
                              QStatusBar, QLabel)
from PyQt6.QtCore import Qt

from core.connection_manager import ConnectionManager
from core.telemetry_worker import TelemetryWorker
from core.command_worker import CommandWorker
from ui.connection_panel import ConnectionPanel
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.control_tab import ControlTab
from ui.tabs.motor_health_tab import MotorHealthTab
from ui.tabs.test_suite_tab import TestSuiteTab
from ui.tabs.log_tab import LogTab
from ui.styles import DARK_STYLESHEET, SUBTEXT0

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for GimbalBench."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GimbalBench")
        self.setMinimumSize(1100, 750)
        self.resize(1280, 850)

        # Apply dark theme
        self.setStyleSheet(DARK_STYLESHEET)

        # Core components
        self._conn_manager = ConnectionManager(self)
        self._telemetry_worker = TelemetryWorker(self._conn_manager)
        self._command_worker = CommandWorker(self._conn_manager)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 0)
        main_layout.setSpacing(4)

        # Connection panel (top)
        self._conn_panel = ConnectionPanel()
        main_layout.addWidget(self._conn_panel)

        # Tab widget (center)
        self._tabs = QTabWidget()
        self._dashboard_tab = DashboardTab(self._conn_manager, self._command_worker)
        self._control_tab = ControlTab(self._conn_manager, self._command_worker)
        self._health_tab = MotorHealthTab()
        self._test_tab = TestSuiteTab(self._conn_manager)
        self._log_tab = LogTab()

        self._tabs.addTab(self._dashboard_tab, "Dashboard")
        self._tabs.addTab(self._control_tab, "Control")
        self._tabs.addTab(self._health_tab, "Motor Health")
        self._tabs.addTab(self._test_tab, "Test Suite")
        self._tabs.addTab(self._log_tab, "Log")

        main_layout.addWidget(self._tabs, stretch=1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._telemetry_rate_label = QLabel("Telemetry: --")
        self._telemetry_rate_label.setStyleSheet(f"color: {SUBTEXT0};")
        self._status_bar.addPermanentWidget(self._telemetry_rate_label)

        # Wire up connections
        self._connect_signals()

        # Start command worker
        self._command_worker.start()

        # Log startup
        self._log_tab.append("INFO", "GimbalBench started")

        # Set up logging handler to forward to log tab
        self._setup_logging()

    def _connect_signals(self):
        # Connection panel signals
        self._conn_panel.connect_serial.connect(self._on_connect_serial)
        self._conn_panel.connect_udp.connect(self._on_connect_udp)
        self._conn_panel.disconnect_requested.connect(self._on_disconnect)

        # Connection manager signals
        self._conn_manager.connected.connect(self._on_connected)
        self._conn_manager.disconnected.connect(self._on_disconnected)
        self._conn_manager.error.connect(self._on_connection_error)

        # Telemetry signals (initial worker - will be reconnected on each connect)
        self._telemetry_worker.data_received.connect(self._on_telemetry)
        self._telemetry_worker.error_occurred.connect(self._on_telemetry_error)

        # Command worker signals
        self._command_worker.command_completed.connect(self._on_command_completed)

        # Telemetry counter
        self._telem_count = 0

    def _setup_logging(self):
        """Route Python logging to the log tab."""
        handler = _QtLogHandler(self._log_tab)
        handler.setLevel(logging.DEBUG)
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.DEBUG)

    def _on_connect_serial(self, port: str, baud: int, auto_detect: bool):
        self._log_tab.append("INFO", f"Connecting serial: {port} @ {baud} (auto={auto_detect})")
        self._conn_manager.connect_serial(port, baud, auto_detect)

    def _on_connect_udp(self, ip: str, bridge_port: int, pc_port: int):
        self._log_tab.append("INFO", f"Connecting UDP: {ip}:{bridge_port} (PC port {pc_port})")
        self._conn_manager.connect_udp(ip, bridge_port, pc_port)

    def _on_disconnect(self):
        self._telemetry_worker.stop()
        self._conn_manager.disconnect()
        self._log_tab.append("INFO", "Disconnected")

    def _on_connected(self, probe_ok: bool):
        self._conn_panel.set_connected(probed=probe_ok)
        if probe_ok:
            self._status_bar.showMessage("Connected - gimbal responding", 3000)
            self._log_tab.append("INFO", "Connected to gimbal - probe OK, starting telemetry")
        else:
            self._status_bar.showMessage("Port open but gimbal not responding - will retry", 5000)
            self._log_tab.append("WARNING",
                "Port opened but gimbal did not respond to probe. "
                "Starting telemetry polling anyway - will update when gimbal responds.")

        # Recreate telemetry worker (QThread can't be restarted after finishing)
        self._telem_count = 0
        if self._telemetry_worker.isRunning():
            self._telemetry_worker.stop()
        self._telemetry_worker = TelemetryWorker(self._conn_manager)
        self._telemetry_worker.data_received.connect(self._on_telemetry)
        self._telemetry_worker.error_occurred.connect(self._on_telemetry_error)
        self._telemetry_worker.start()

    def _on_disconnected(self):
        self._conn_panel.set_disconnected()
        self._status_bar.showMessage("Disconnected", 3000)
        self._telemetry_worker.stop()

    def _on_connection_error(self, msg: str):
        self._conn_panel.set_error(msg)
        self._log_tab.append("ERROR", f"Connection error: {msg}")
        self._status_bar.showMessage(f"Error: {msg}", 5000)

    def _on_telemetry(self, data):
        """Handle incoming telemetry data - update all tabs."""
        self._telem_count += 1
        self._telemetry_rate_label.setText(f"Telemetry: {self._telem_count} frames")

        # If this is the first frame, upgrade connection status to green
        if self._telem_count == 1:
            self._conn_panel.set_connected(probed=True)
            self._log_tab.append("INFO", "First telemetry frame received - gimbal is live")

        # Update dashboard
        self._dashboard_tab.update_telemetry(data)

        # Update control tab actual angles
        self._control_tab.update_actual_angles(data)

        # Update health tab
        self._health_tab.update_telemetry(data)

        # Forward to test suite tab (telemetry bridging for test runner)
        self._test_tab.on_telemetry(data)

    def _on_telemetry_error(self, msg: str):
        self._log_tab.append("WARNING", f"Telemetry: {msg}")

    def _on_command_completed(self, name: str, success: bool, message: str):
        level = "INFO" if success else "ERROR"
        self._log_tab.append(level, f"Command '{name}': {message}")

    def closeEvent(self, event):
        """Clean shutdown."""
        self._telemetry_worker.stop()
        self._command_worker.stop()
        self._conn_manager.disconnect()
        event.accept()


class _QtLogHandler(logging.Handler):
    """Routes Python logging to the LogTab."""

    def __init__(self, log_tab: LogTab):
        super().__init__()
        self._log_tab = log_tab

    def emit(self, record):
        try:
            level = record.levelname
            msg = self.format(record)
            self._log_tab.append(level, msg)
        except Exception:
            pass
