"""Manual control tab with sliders, mode/preset/profile controls."""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QGridLayout, QPushButton, QComboBox, QLabel,
                              QRadioButton, QButtonGroup, QDoubleSpinBox)
from PyQt6.QtCore import QTimer, pyqtSignal

from sbgc.models import Mode
from ui.widgets.axis_slider import AxisSlider
from ui.styles import SUBTEXT0, BLUE


class ControlTab(QWidget):
    """Manual gimbal control: mode, presets, profiles, sliders."""

    # Signals for commands to be executed by CommandWorker
    command_requested = pyqtSignal(str, object, tuple, dict)  # name, func, args, kwargs

    def __init__(self, connection_manager, command_worker, parent=None):
        super().__init__(parent)
        self._conn = connection_manager
        self._cmd_worker = command_worker
        self._rate_timer = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # === Top row: Mode + Presets + Profiles ===
        top_layout = QHBoxLayout()

        # Mode group
        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout(mode_group)
        self._follow_off_btn = QPushButton("FOLLOW OFF")
        self._follow_on_btn = QPushButton("FOLLOW ON")
        self._follow_off_btn.clicked.connect(lambda: self._set_mode(Mode.FOLLOW_OFF))
        self._follow_on_btn.clicked.connect(lambda: self._set_mode(Mode.FOLLOW_ON))
        mode_layout.addWidget(self._follow_off_btn)
        mode_layout.addWidget(self._follow_on_btn)
        top_layout.addWidget(mode_group)

        # Presets
        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout(preset_group)
        home_btn = QPushButton("Home (0 deg)")
        down_btn = QPushButton("Down (90 deg)")
        center_btn = QPushButton("Center Yaw")
        home_btn.clicked.connect(lambda: self._send_cmd("home", lambda c: c.home()))
        down_btn.clicked.connect(lambda: self._send_cmd("down", lambda c: c.down()))
        center_btn.clicked.connect(lambda: self._send_cmd("center_yaw", lambda c: c.center_yaw()))
        preset_layout.addWidget(home_btn)
        preset_layout.addWidget(down_btn)
        preset_layout.addWidget(center_btn)
        top_layout.addWidget(preset_group)

        # Profiles
        profile_group = QGroupBox("Profiles")
        profile_layout = QGridLayout(profile_group)
        self._profile_btns = []
        for i in range(1, 6):
            btn = QPushButton(f"Profile {i}")
            btn.clicked.connect(lambda checked, pid=i: self._select_profile(pid))
            profile_layout.addWidget(btn, (i - 1) // 3, (i - 1) % 3)
            self._profile_btns.append(btn)
        top_layout.addWidget(profile_group)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # === Control mode selector ===
        ctrl_mode_group = QGroupBox("Control Mode")
        ctrl_mode_layout = QHBoxLayout(ctrl_mode_group)

        self._rate_mode_radio = QRadioButton("Rate Mode")
        self._angle_mode_radio = QRadioButton("Angle Mode")
        self._angle_mode_radio.setChecked(True)
        ctrl_btn_group = QButtonGroup(self)
        ctrl_btn_group.addButton(self._rate_mode_radio)
        ctrl_btn_group.addButton(self._angle_mode_radio)
        self._rate_mode_radio.toggled.connect(self._on_control_mode_changed)

        ctrl_mode_layout.addWidget(self._rate_mode_radio)
        ctrl_mode_layout.addWidget(self._angle_mode_radio)

        ctrl_mode_layout.addWidget(QLabel("Speed (dps):"))
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(1.0, 100.0)
        self._speed_spin.setValue(20.0)
        self._speed_spin.setSingleStep(5.0)
        ctrl_mode_layout.addWidget(self._speed_spin)

        ctrl_mode_layout.addStretch()
        layout.addWidget(ctrl_mode_group)

        # === Axis sliders ===
        slider_group = QGroupBox("Manual Control")
        slider_layout = QVBoxLayout(slider_group)

        self._pitch_slider = AxisSlider("Pitch", -90, 90, center_return=False)
        self._yaw_slider = AxisSlider("Yaw", -90, 90, center_return=False)
        self._roll_slider = AxisSlider("Roll", -45, 45, center_return=False)

        slider_layout.addWidget(self._pitch_slider)
        slider_layout.addWidget(self._yaw_slider)
        slider_layout.addWidget(self._roll_slider)

        # Connect slider signals
        self._pitch_slider.value_changed.connect(self._on_slider_changed)
        self._yaw_slider.value_changed.connect(self._on_slider_changed)
        self._roll_slider.value_changed.connect(self._on_slider_changed)

        layout.addWidget(slider_group)

        # === Action buttons ===
        action_layout = QHBoxLayout()
        release_btn = QPushButton("Release Control")
        release_btn.clicked.connect(lambda: self._send_cmd("release", lambda c: c.release_control()))
        action_layout.addWidget(release_btn)

        stop_btn = QPushButton("STOP (All Zero)")
        stop_btn.setStyleSheet("background-color: #45475a; border-color: #f38ba8; color: #f38ba8; font-weight: bold;")
        stop_btn.clicked.connect(self._emergency_stop)
        action_layout.addWidget(stop_btn)

        reset_btn = QPushButton("Reset Sliders")
        reset_btn.clicked.connect(self._reset_sliders)
        action_layout.addWidget(reset_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)
        layout.addStretch()

        # Rate mode timer (50Hz)
        self._rate_timer = QTimer(self)
        self._rate_timer.setInterval(20)  # 50Hz
        self._rate_timer.timeout.connect(self._send_rate_command)

    def _set_mode(self, mode: Mode):
        self._send_cmd(f"set_mode_{mode.value}", lambda c, m=mode: c.set_mode(m))

    def _select_profile(self, profile_id: int):
        self._send_cmd(f"profile_{profile_id}", lambda c, p=profile_id: c.select_profile(p))

    def _send_cmd(self, name: str, func):
        self._cmd_worker.submit(name, func)

    def _on_control_mode_changed(self, rate_checked: bool):
        if rate_checked:
            # Switch to rate mode: enable center-return on sliders
            self._pitch_slider._center_return = True
            self._yaw_slider._center_return = True
            self._roll_slider._center_return = True
            self._rate_timer.start()
        else:
            # Angle mode
            self._pitch_slider._center_return = False
            self._yaw_slider._center_return = False
            self._roll_slider._center_return = False
            self._rate_timer.stop()

    def _on_slider_changed(self, value: float):
        """Handle slider value change in angle mode."""
        if self._angle_mode_radio.isChecked():
            pitch = self._pitch_slider.value()
            yaw = self._yaw_slider.value()
            speed = self._speed_spin.value()
            self._send_cmd(
                "set_angles",
                lambda c, p=pitch, y=yaw, s=speed: c.set_angles(p, yaw_deg=y, speed_dps=s)
            )

    def _send_rate_command(self):
        """Called at 50Hz in rate mode to send rate commands."""
        if not self._conn.is_connected or self._conn.client is None:
            return
        pitch_rate = self._pitch_slider.value()
        yaw_rate = self._yaw_slider.value()
        if abs(pitch_rate) < 0.5 and abs(yaw_rate) < 0.5:
            return
        self._send_cmd(
            "set_rates",
            lambda c, p=pitch_rate, y=yaw_rate: c.set_rates(y, p)
        )

    def _emergency_stop(self):
        self._reset_sliders()
        self._send_cmd("release", lambda c: c.release_control())

    def _reset_sliders(self):
        self._pitch_slider.reset()
        self._yaw_slider.reset()
        self._roll_slider.reset()

    def update_actual_angles(self, data):
        """Update actual angle readouts from telemetry data."""
        from sbgc.units import to_degree
        self._pitch_slider.set_actual(to_degree(data.imu_angle_2))
        self._yaw_slider.set_actual(to_degree(data.imu_angle_3))
        self._roll_slider.set_actual(to_degree(data.imu_angle_1))
