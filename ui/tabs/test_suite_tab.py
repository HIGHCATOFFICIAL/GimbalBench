"""Gimbal validation test suite UI with config, wizard, progress, and results pages."""
import os
import time as _time
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QPushButton, QLabel, QDoubleSpinBox, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QTextEdit, QStackedWidget, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QTimer

from sbgc.units import to_degree
from core.test_models import TestStatus, TestCategory, TestCaseResult, TestSuiteConfig
from core.test_cases import build_test_suite
from core.test_runner import TestRunner
from core.test_export import export_results_csv, default_filename
from ui.styles import (
    COLOR_OK, COLOR_WARN, COLOR_FAIL, COLOR_ACCENT,
    TEXT, SUBTEXT0, SURFACE0, SURFACE1, BASE, MANTLE, GREEN, RED, YELLOW, BLUE,
)

# Log directory
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "logs")

# Page indices for QStackedWidget
PAGE_CONFIG = 0
PAGE_WIZARD = 1
PAGE_RUNNING = 2
PAGE_RESULTS = 3


class TestSuiteTab(QWidget):
    """Gimbal validation test suite with 4 test categories and wizard support."""

    def __init__(self, connection_manager, parent=None):
        super().__init__(parent)
        self._conn = connection_manager
        self._runner: TestRunner | None = None
        self._results: list[TestCaseResult] = []

        # Log persistence
        self._log_lines: list[str] = []  # plain text lines for file
        self._log_file_path: str | None = None

        # Elapsed time tracking
        self._suite_start_time: float = 0.0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(500)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        # Stacked pages
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_config_page())    # 0
        self._stack.addWidget(self._build_wizard_page())     # 1
        self._stack.addWidget(self._build_running_page())    # 2
        self._stack.addWidget(self._build_results_page())    # 3

        # Log at bottom (visible on all pages)
        log_group = QGroupBox("Test Log")
        log_layout = QVBoxLayout(log_group)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumHeight(110)
        log_layout.addWidget(self._log_view)

        log_btn_row = QHBoxLayout()
        self._save_log_btn = QPushButton("Save Log")
        self._save_log_btn.clicked.connect(self._save_log_as)
        log_btn_row.addWidget(self._save_log_btn)

        self._open_log_dir_btn = QPushButton("Open Log Folder")
        self._open_log_dir_btn.clicked.connect(self._open_log_folder)
        log_btn_row.addWidget(self._open_log_dir_btn)

        self._log_path_label = QLabel("")
        self._log_path_label.setStyleSheet(f"color: {SUBTEXT0}; font-size: 11px;")
        log_btn_row.addWidget(self._log_path_label)
        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)

        layout.addWidget(log_group)

    # ── Page 0: Config & Start ─────────────────────────────────────

    def _build_config_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(6)

        # Category selection
        cat_group = QGroupBox("Test Categories")
        cat_layout = QHBoxLayout(cat_group)
        self._cat_motor = QCheckBox("Motor Startup (Wizard)")
        self._cat_motor.setChecked(True)
        self._cat_recovery = QCheckBox("Home/Center Recovery")
        self._cat_recovery.setChecked(True)
        self._cat_sweep = QCheckBox("Axis Range Sweep")
        self._cat_sweep.setChecked(True)
        self._cat_stability = QCheckBox("Hold Stability")
        self._cat_stability.setChecked(True)
        cat_layout.addWidget(self._cat_motor)
        cat_layout.addWidget(self._cat_recovery)
        cat_layout.addWidget(self._cat_sweep)
        cat_layout.addWidget(self._cat_stability)
        cat_layout.addStretch()
        layout.addWidget(cat_group)

        # Config spinboxes
        cfg_group = QGroupBox("Configuration")
        cfg_grid = QGridLayout(cfg_group)

        cfg_grid.addWidget(QLabel("Speed (dps):"), 0, 0)
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(1.0, 100.0)
        self._speed_spin.setValue(20.0)
        cfg_grid.addWidget(self._speed_spin, 0, 1)

        cfg_grid.addWidget(QLabel("Angle tolerance (deg):"), 0, 2)
        self._angle_tol_spin = QDoubleSpinBox()
        self._angle_tol_spin.setRange(0.5, 20.0)
        self._angle_tol_spin.setValue(3.0)
        cfg_grid.addWidget(self._angle_tol_spin, 0, 3)

        cfg_grid.addWidget(QLabel("Hold tolerance (deg):"), 0, 4)
        self._hold_tol_spin = QDoubleSpinBox()
        self._hold_tol_spin.setRange(0.5, 10.0)
        self._hold_tol_spin.setValue(2.0)
        cfg_grid.addWidget(self._hold_tol_spin, 0, 5)

        cfg_grid.addWidget(QLabel("Move timeout (s):"), 1, 0)
        self._move_timeout_spin = QDoubleSpinBox()
        self._move_timeout_spin.setRange(1.0, 60.0)
        self._move_timeout_spin.setValue(10.0)
        cfg_grid.addWidget(self._move_timeout_spin, 1, 1)

        cfg_grid.addWidget(QLabel("Startup timeout (s):"), 1, 2)
        self._startup_timeout_spin = QDoubleSpinBox()
        self._startup_timeout_spin.setRange(5.0, 120.0)
        self._startup_timeout_spin.setValue(20.0)
        cfg_grid.addWidget(self._startup_timeout_spin, 1, 3)

        cfg_grid.addWidget(QLabel("Hold duration (s):"), 1, 4)
        self._hold_dur_spin = QDoubleSpinBox()
        self._hold_dur_spin.setRange(1.0, 30.0)
        self._hold_dur_spin.setValue(5.0)
        cfg_grid.addWidget(self._hold_dur_spin, 1, 5)

        cfg_grid.addWidget(QLabel("Sweep step (deg):"), 2, 0)
        self._step_spin = QDoubleSpinBox()
        self._step_spin.setRange(5.0, 90.0)
        self._step_spin.setValue(45.0)
        cfg_grid.addWidget(self._step_spin, 2, 1)

        self._test_pitch_cb = QCheckBox("Test Pitch")
        self._test_pitch_cb.setChecked(True)
        cfg_grid.addWidget(self._test_pitch_cb, 2, 2)

        self._test_yaw_cb = QCheckBox("Test Yaw")
        self._test_yaw_cb.setChecked(True)
        cfg_grid.addWidget(self._test_yaw_cb, 2, 3)

        layout.addWidget(cfg_group)

        # Start button + last run summary
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("Run All Selected")
        self._start_btn.setStyleSheet(
            f"QPushButton {{ border-color: {GREEN}; color: {GREEN}; font-weight: bold; "
            f"padding: 10px 24px; font-size: 14px; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._start_btn.clicked.connect(self._start_suite)
        btn_row.addWidget(self._start_btn)

        self._view_results_btn = QPushButton("View Last Results")
        self._view_results_btn.setEnabled(False)
        self._view_results_btn.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_RESULTS))
        btn_row.addWidget(self._view_results_btn)

        btn_row.addStretch()
        self._config_status = QLabel("Ready")
        self._config_status.setStyleSheet(f"color: {SUBTEXT0};")
        btn_row.addWidget(self._config_status)
        layout.addLayout(btn_row)

        layout.addStretch()
        return page

    # ── Page 1: Wizard Panel ───────────────────────────────────────

    def _build_wizard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Header
        header = QLabel("Motor Startup Test - Wizard")
        header.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {BLUE};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Instruction panel
        self._wizard_instruction = QLabel("Follow the instruction below...")
        self._wizard_instruction.setWordWrap(True)
        self._wizard_instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wizard_instruction.setStyleSheet(
            f"font-size: 15px; padding: 20px; background-color: {SURFACE0}; "
            f"border: 1px solid {SURFACE1}; border-radius: 8px; color: {TEXT};")
        self._wizard_instruction.setMinimumHeight(100)
        layout.addWidget(self._wizard_instruction)

        # Action hint
        self._wizard_action = QLabel("")
        self._wizard_action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wizard_action.setStyleSheet(f"color: {YELLOW}; font-size: 13px;")
        layout.addWidget(self._wizard_action)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._wizard_ready_btn = QPushButton("Ready / Continue")
        self._wizard_ready_btn.setStyleSheet(
            f"QPushButton {{ border-color: {GREEN}; color: {GREEN}; font-weight: bold; "
            f"padding: 10px 30px; font-size: 14px; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._wizard_ready_btn.clicked.connect(self._on_wizard_ready)
        btn_row.addWidget(self._wizard_ready_btn)

        self._wizard_skip_btn = QPushButton("Skip This Test")
        self._wizard_skip_btn.setStyleSheet(
            f"QPushButton {{ border-color: {YELLOW}; color: {YELLOW}; padding: 10px 20px; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._wizard_skip_btn.clicked.connect(self._on_wizard_skip)
        btn_row.addWidget(self._wizard_skip_btn)

        self._wizard_abort_btn = QPushButton("Abort Suite")
        self._wizard_abort_btn.setStyleSheet(
            f"QPushButton {{ border-color: {RED}; color: {RED}; padding: 10px 20px; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._wizard_abort_btn.clicked.connect(self._abort_suite)
        btn_row.addWidget(self._wizard_abort_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Live telemetry mini-display
        telem_group = QGroupBox("Live Telemetry")
        telem_layout = QGridLayout(telem_group)
        self._wiz_pitch_label = QLabel("Pitch: --")
        self._wiz_yaw_label = QLabel("Yaw: --")
        self._wiz_roll_label = QLabel("Roll: --")
        self._wiz_motors_label = QLabel("Motors: --")
        for lbl in (self._wiz_pitch_label, self._wiz_yaw_label,
                     self._wiz_roll_label, self._wiz_motors_label):
            lbl.setStyleSheet(f"font-family: monospace; font-size: 13px; color: {TEXT};")
        telem_layout.addWidget(self._wiz_roll_label, 0, 0)
        telem_layout.addWidget(self._wiz_pitch_label, 0, 1)
        telem_layout.addWidget(self._wiz_yaw_label, 0, 2)
        telem_layout.addWidget(self._wiz_motors_label, 0, 3)
        layout.addWidget(telem_group)

        # Progress
        self._wizard_progress = QLabel("")
        self._wizard_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wizard_progress.setStyleSheet(f"color: {SUBTEXT0};")
        layout.addWidget(self._wizard_progress)

        layout.addStretch()
        return page

    # ── Page 2: Running (automatic tests) ──────────────────────────

    def _build_running_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(6)

        # Progress header
        top_row = QHBoxLayout()
        self._running_label = QLabel("Running tests...")
        self._running_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {BLUE};")
        top_row.addWidget(self._running_label)
        top_row.addStretch()

        self._elapsed_label = QLabel("")
        self._elapsed_label.setStyleSheet(f"color: {SUBTEXT0}; font-size: 13px;")
        top_row.addWidget(self._elapsed_label)

        self._running_abort_btn = QPushButton("Abort")
        self._running_abort_btn.setStyleSheet(
            f"QPushButton {{ border-color: {RED}; color: {RED}; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._running_abort_btn.clicked.connect(self._abort_suite)
        top_row.addWidget(self._running_abort_btn)
        layout.addLayout(top_row)

        self._running_progress = QProgressBar()
        self._running_progress.setRange(0, 100)
        layout.addWidget(self._running_progress)

        # Two-line status: test name + sub-step detail
        self._running_test_name = QLabel("")
        self._running_test_name.setStyleSheet(f"color: {TEXT}; font-weight: bold;")
        layout.addWidget(self._running_test_name)

        self._running_detail = QLabel("")
        self._running_detail.setStyleSheet(f"color: {SUBTEXT0}; font-size: 12px;")
        layout.addWidget(self._running_detail)

        # Live telemetry mini-display
        telem_group = QGroupBox("Live Telemetry")
        telem_layout = QGridLayout(telem_group)
        self._run_pitch_label = QLabel("Pitch: --")
        self._run_yaw_label = QLabel("Yaw: --")
        self._run_roll_label = QLabel("Roll: --")
        self._run_motors_label = QLabel("Motors: --")
        for lbl in (self._run_pitch_label, self._run_yaw_label,
                     self._run_roll_label, self._run_motors_label):
            lbl.setStyleSheet(f"font-family: monospace; font-size: 13px; color: {TEXT};")
        telem_layout.addWidget(self._run_roll_label, 0, 0)
        telem_layout.addWidget(self._run_pitch_label, 0, 1)
        telem_layout.addWidget(self._run_yaw_label, 0, 2)
        telem_layout.addWidget(self._run_motors_label, 0, 3)
        layout.addWidget(telem_group)

        # In-progress results table
        self._running_table = QTableWidget()
        self._running_table.setColumnCount(5)
        self._running_table.setHorizontalHeaderLabels([
            "Test", "Category", "Status", "Duration", "Message",
        ])
        self._running_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._running_table.setAlternatingRowColors(True)
        layout.addWidget(self._running_table, stretch=1)

        return page

    # ── Page 3: Results ────────────────────────────────────────────

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(6)

        # Summary banner
        self._results_summary = QLabel("No results")
        self._results_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._results_summary.setStyleSheet(
            f"font-size: 16px; font-weight: bold; padding: 12px; "
            f"background-color: {SURFACE0}; border-radius: 6px;")
        layout.addWidget(self._results_summary)

        # Stats row
        stats_row = QHBoxLayout()
        self._results_stats = QLabel("")
        self._results_stats.setWordWrap(True)
        self._results_stats.setStyleSheet(f"color: {SUBTEXT0};")
        stats_row.addWidget(self._results_stats)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Results table
        self._results_table = QTableWidget()
        self._results_table.setColumnCount(7)
        self._results_table.setHorizontalHeaderLabels([
            "Test", "Category", "Status", "Duration (s)",
            "Max Err (deg)", "Mean Err (deg)", "Message",
        ])
        self._results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._results_table.setAlternatingRowColors(True)
        layout.addWidget(self._results_table, stretch=1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self._export_btn = QPushButton("Export CSV")
        self._export_btn.clicked.connect(self._export_csv)
        btn_row.addWidget(self._export_btn)

        self._view_log_btn = QPushButton("View Full Log")
        self._view_log_btn.clicked.connect(self._view_log_file)
        btn_row.addWidget(self._view_log_btn)

        self._back_btn = QPushButton("Back to Config")
        self._back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(PAGE_CONFIG))
        btn_row.addWidget(self._back_btn)

        self._rerun_btn = QPushButton("Run Again")
        self._rerun_btn.setStyleSheet(
            f"QPushButton {{ border-color: {GREEN}; color: {GREEN}; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._rerun_btn.clicked.connect(self._start_suite)
        btn_row.addWidget(self._rerun_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return page

    # ── Config helpers ─────────────────────────────────────────────

    def _get_config(self) -> TestSuiteConfig:
        return TestSuiteConfig(
            speed_dps=self._speed_spin.value(),
            angle_tolerance_deg=self._angle_tol_spin.value(),
            hold_tolerance_deg=self._hold_tol_spin.value(),
            move_timeout_s=self._move_timeout_spin.value(),
            startup_timeout_s=self._startup_timeout_spin.value(),
            hold_duration_s=self._hold_dur_spin.value(),
            test_pitch=self._test_pitch_cb.isChecked(),
            test_yaw=self._test_yaw_cb.isChecked(),
            sweep_step_deg=self._step_spin.value(),
        )

    # ── Telemetry forwarding ───────────────────────────────────────

    def on_telemetry(self, data) -> None:
        """Called from MainWindow._on_telemetry to feed live data."""
        # Forward to runner if active
        if self._runner and self._runner.isRunning():
            self._runner.on_telemetry(data)

        # Update mini telemetry displays on visible page
        roll = to_degree(data.imu_angle_1)
        pitch = to_degree(data.imu_angle_2)
        yaw = to_degree(data.imu_angle_3)
        mp1, mp2, mp3 = data.motor_power_1, data.motor_power_2, data.motor_power_3
        motors_str = f"Motors: {mp1}/{mp2}/{mp3}"

        current_page = self._stack.currentIndex()
        if current_page == PAGE_WIZARD:
            self._wiz_roll_label.setText(f"Roll: {roll:+.1f}\u00b0")
            self._wiz_pitch_label.setText(f"Pitch: {pitch:+.1f}\u00b0")
            self._wiz_yaw_label.setText(f"Yaw: {yaw:+.1f}\u00b0")
            motors_on = any(p > 0 for p in (mp1, mp2, mp3))
            color = GREEN if motors_on else RED
            self._wiz_motors_label.setText(f"<span style='color:{color}'>{motors_str}</span>")
        elif current_page == PAGE_RUNNING:
            self._run_roll_label.setText(f"Roll: {roll:+.1f}\u00b0")
            self._run_pitch_label.setText(f"Pitch: {pitch:+.1f}\u00b0")
            self._run_yaw_label.setText(f"Yaw: {yaw:+.1f}\u00b0")
            self._run_motors_label.setText(motors_str)

    # ── Suite lifecycle ────────────────────────────────────────────

    def _start_suite(self):
        if not self._conn.is_connected:
            self._log_view.append(
                f'<span style="color:{RED}">Not connected to gimbal</span>')
            return

        cfg = self._get_config()
        cases = build_test_suite(
            cfg,
            motor_startup=self._cat_motor.isChecked(),
            recovery=self._cat_recovery.isChecked(),
            sweep=self._cat_sweep.isChecked(),
            stability=self._cat_stability.isChecked(),
        )
        if not cases:
            self._log_view.append(
                f'<span style="color:{YELLOW}">No test categories selected</span>')
            return

        self._results.clear()
        self._running_table.setRowCount(0)
        self._log_view.clear()
        self._log_lines.clear()
        self._running_detail.setText("")

        # Prepare log file
        os.makedirs(_LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file_path = os.path.join(_LOG_DIR, f"test_run_{ts}.log")
        self._log_path_label.setText(f"Log: {self._log_file_path}")

        self._runner = TestRunner(self._conn, cfg, cases)
        self._runner.test_started.connect(self._on_test_started)
        self._runner.test_completed.connect(self._on_test_completed)
        self._runner.suite_completed.connect(self._on_suite_completed)
        self._runner.log_message.connect(self._on_log)
        self._runner.progress.connect(self._on_progress)
        self._runner.status_detail.connect(self._on_status_detail)
        self._runner.waiting_for_user.connect(self._on_waiting_for_user)
        self._runner.user_action_needed.connect(self._on_user_action)
        self._runner.page_request.connect(self._on_page_request)

        self._start_btn.setEnabled(False)
        self._config_status.setText("Running...")

        # Start elapsed timer
        self._suite_start_time = _time.time()
        self._elapsed_timer.start()

        # Start on appropriate page
        first_is_wizard = cases[0].category == TestCategory.MOTOR_STARTUP
        if first_is_wizard:
            self._stack.setCurrentIndex(PAGE_WIZARD)
        else:
            self._stack.setCurrentIndex(PAGE_RUNNING)

        self._runner.start()

    def _abort_suite(self):
        if self._runner:
            self._runner.stop()
        self._on_log("Suite aborted by user")

    # ── Elapsed time ───────────────────────────────────────────────

    def _update_elapsed(self):
        if self._suite_start_time > 0:
            elapsed = _time.time() - self._suite_start_time
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            self._elapsed_label.setText(f"Elapsed: {mins}:{secs:02d}")

    # ── Wizard callbacks ───────────────────────────────────────────

    def _on_wizard_ready(self):
        if self._runner:
            self._runner.user_continue()

    def _on_wizard_skip(self):
        if self._runner:
            self._runner.user_skip()

    # ── Runner signal handlers ─────────────────────────────────────

    def _on_test_started(self, name: str):
        self._running_test_name.setText(f"Current: {name}")
        self._running_detail.setText("")

    def _on_test_completed(self, result: TestCaseResult):
        self._results.append(result)
        self._add_result_to_running_table(result)

    def _on_suite_completed(self, results: list):
        self._elapsed_timer.stop()
        self._start_btn.setEnabled(True)
        self._view_results_btn.setEnabled(True)
        self._populate_results_page(results)
        self._stack.setCurrentIndex(PAGE_RESULTS)

        # Flush log to file
        self._flush_log()

        # Update config page status
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        total = len(results)
        color = COLOR_OK if passed == total else COLOR_FAIL
        self._config_status.setText(
            f"<span style='color:{color}'>{passed}/{total} PASSED</span>")

    def _on_progress(self, current: int, total: int):
        if total > 0:
            self._running_progress.setRange(0, total)
            self._running_progress.setValue(current)
            self._wizard_progress.setText(f"Test {current + 1} of {total}")

    def _on_status_detail(self, text: str):
        """Sub-step activity text from runner (e.g. 'Waiting for angles... 8s left')."""
        self._running_detail.setText(text)

    def _on_waiting_for_user(self, instruction: str):
        self._wizard_instruction.setText(instruction)

    def _on_user_action(self, hint: str):
        self._wizard_action.setText(hint)

    def _on_page_request(self, page: int):
        self._stack.setCurrentIndex(page)

    def _on_log(self, message: str):
        self._log_view.append(message)
        # Strip HTML tags for plain text log file
        import re
        plain = re.sub(r'<[^>]+>', '', message)
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_lines.append(f"[{ts}] {plain}")

    # ── Log persistence ────────────────────────────────────────────

    def _flush_log(self):
        """Write accumulated log lines to the log file."""
        if self._log_file_path and self._log_lines:
            try:
                with open(self._log_file_path, "w") as f:
                    f.write("\n".join(self._log_lines))
                    f.write("\n")
                self._log_path_label.setText(f"Log saved: {self._log_file_path}")
            except Exception as e:
                self._log_path_label.setText(f"Log save error: {e}")

    def _save_log_as(self):
        """Save current log to a user-chosen location."""
        if not self._log_lines:
            return
        default = self._log_file_path or "test_log.log"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", default, "Log Files (*.log);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w") as f:
                f.write("\n".join(self._log_lines))
                f.write("\n")
            self._on_log(f"Log saved to {path}")
        except Exception as e:
            self._on_log(f"Error saving log: {e}")

    def _open_log_folder(self):
        """Open the logs directory in the file manager."""
        os.makedirs(_LOG_DIR, exist_ok=True)
        import subprocess
        subprocess.Popen(["xdg-open", _LOG_DIR])

    def _view_log_file(self):
        """Open the current log file in the default text editor."""
        if self._log_file_path and os.path.isfile(self._log_file_path):
            import subprocess
            subprocess.Popen(["xdg-open", self._log_file_path])

    # ── Table helpers ──────────────────────────────────────────────

    def _add_result_to_running_table(self, result: TestCaseResult):
        table = self._running_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(result.name))
        table.setItem(row, 1, QTableWidgetItem(result.category.value))

        status_item = QTableWidgetItem(result.status.value)
        if result.status == TestStatus.PASS:
            status_item.setForeground(Qt.GlobalColor.green)
        elif result.status == TestStatus.FAIL:
            status_item.setForeground(Qt.GlobalColor.red)
        elif result.status == TestStatus.SKIPPED:
            status_item.setForeground(Qt.GlobalColor.yellow)
        table.setItem(row, 2, status_item)

        table.setItem(row, 3, QTableWidgetItem(f"{result.duration_s:.1f}s"))
        table.setItem(row, 4, QTableWidgetItem(result.message))
        table.scrollToBottom()

    def _populate_results_page(self, results: list[TestCaseResult]):
        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        if failed == 0 and total > 0:
            self._results_summary.setText(f"ALL PASSED ({passed}/{total})")
            self._results_summary.setStyleSheet(
                f"font-size: 16px; font-weight: bold; padding: 12px; "
                f"background-color: {SURFACE0}; border-radius: 6px; color: {GREEN};")
        elif total > 0:
            self._results_summary.setText(f"{failed} FAILED ({passed}/{total} passed)")
            self._results_summary.setStyleSheet(
                f"font-size: 16px; font-weight: bold; padding: 12px; "
                f"background-color: {SURFACE0}; border-radius: 6px; color: {RED};")
        else:
            self._results_summary.setText("No results")

        # Stats
        total_time = sum(r.duration_s for r in results)
        parts = [f"Total: {total}", f"Passed: {passed}", f"Failed: {failed}"]
        if skipped:
            parts.append(f"Skipped: {skipped}")
        parts.append(f"Duration: {total_time:.1f}s")
        self._results_stats.setText("  |  ".join(parts))

        # Table
        table = self._results_table
        table.setRowCount(0)
        for r in results:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(r.name))
            table.setItem(row, 1, QTableWidgetItem(r.category.value))

            status_item = QTableWidgetItem(r.status.value)
            if r.status == TestStatus.PASS:
                status_item.setForeground(Qt.GlobalColor.green)
            elif r.status == TestStatus.FAIL:
                status_item.setForeground(Qt.GlobalColor.red)
            elif r.status == TestStatus.SKIPPED:
                status_item.setForeground(Qt.GlobalColor.yellow)
            table.setItem(row, 2, status_item)

            table.setItem(row, 3, QTableWidgetItem(f"{r.duration_s:.2f}"))
            table.setItem(row, 4, QTableWidgetItem(f"{r.max_error_deg:.2f}"))
            table.setItem(row, 5, QTableWidgetItem(f"{r.mean_error_deg:.2f}"))
            table.setItem(row, 6, QTableWidgetItem(r.message))

    # ── CSV Export ─────────────────────────────────────────────────

    def _export_csv(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default_filename(), "CSV Files (*.csv)")
        if not path:
            return
        export_results_csv(path, self._results)
        self._on_log(f"Results exported to {path}")
