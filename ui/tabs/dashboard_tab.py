"""Dashboard tab showing all telemetry data from RealtimeData4."""
import collections
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QGridLayout, QLabel, QScrollArea, QPushButton)
from PyQt6.QtCore import Qt

from sbgc.commands.realtime import RealtimeData4InCmd
from sbgc.units import to_degree

from core.sbgc_errors import decode_system_errors, decode_sub_error, format_error_summary
from ui.widgets.angle_gauge import AngleGauge
from ui.widgets.labeled_value import LabeledValue
from ui.widgets.led_indicator import LedIndicator
from ui.styles import (
    COLOR_OK, COLOR_WARN, COLOR_FAIL, TEXT, SUBTEXT0, SUBTEXT1,
    SURFACE0, SURFACE1, GREEN, RED, YELLOW, BLUE, PEACH, MANTLE,
)

# Flicker detection: track last N power readings per axis over a time window
_FLICKER_WINDOW = 30       # number of recent samples to keep (~3s at 10Hz)
_FLICKER_THRESHOLD = 4     # min ON->OFF or OFF->ON transitions to count as flickering


class DashboardTab(QWidget):
    """Full telemetry dashboard with gauges and all RealtimeData4 fields."""

    def __init__(self, connection_manager=None, command_worker=None, parent=None):
        super().__init__(parent)
        self._conn = connection_manager
        self._cmd_worker = command_worker

        # Flicker detection: deque of booleans (True=on) per axis index 1,2,3
        self._power_history: dict[int, collections.deque] = {
            1: collections.deque(maxlen=_FLICKER_WINDOW),
            2: collections.deque(maxlen=_FLICKER_WINDOW),
            3: collections.deque(maxlen=_FLICKER_WINDOW),
        }
        # Track whether motors are currently on (any axis)
        self._motors_are_on = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(10)

        # === Top: Angle Gauges ===
        gauge_group = QGroupBox("Angles")
        gauge_layout = QHBoxLayout(gauge_group)

        self._gauges = {}
        for axis in ["Roll", "Pitch", "Yaw"]:
            col = QVBoxLayout()
            gauge = AngleGauge(title=axis)
            col.addWidget(gauge)
            self._gauges[axis] = gauge

            # IMU / Frame / Target values below gauge
            info = QGridLayout()
            imu_lv = LabeledValue("IMU", "deg")
            frame_lv = LabeledValue("Frame", "deg")
            target_lv = LabeledValue("Target", "deg")
            info.addWidget(imu_lv, 0, 0)
            info.addWidget(frame_lv, 1, 0)
            info.addWidget(target_lv, 2, 0)
            col.addLayout(info)

            self._gauges[f"{axis}_imu"] = imu_lv
            self._gauges[f"{axis}_frame"] = frame_lv
            self._gauges[f"{axis}_target"] = target_lv

            gauge_layout.addLayout(col)

        main_layout.addWidget(gauge_group)

        # === Middle row: System + Motor status ===
        mid_layout = QHBoxLayout()

        # System status
        sys_group = QGroupBox("System Status")
        sys_grid = QGridLayout(sys_group)
        self._sys = {}
        sys_fields = [
            ("Battery", "bat_level", ""),
            ("Current", "current", "mA"),
            ("Cycle Time", "cycle_time", "us"),
            ("System Error", "system_error", ""),
            ("Sub Error", "system_sub_error", ""),
            ("Serial Errors", "serial_err_cnt", ""),
            ("I2C Errors", "i2c_error_count", ""),
            ("Error Code", "error_code", ""),
            ("Profile", "cur_profile", ""),
            ("RT Flags", "rt_data_flags", ""),
            ("Current IMU", "cur_imu", ""),
        ]
        for i, (label, key, unit) in enumerate(sys_fields):
            lv = LabeledValue(label, unit)
            sys_grid.addWidget(lv, i // 2, i % 2)
            self._sys[key] = lv

        mid_layout.addWidget(sys_group)

        # Motor status per axis
        motor_group = QGroupBox("Motor Status")
        motor_vbox = QVBoxLayout(motor_group)

        # Motor toggle button
        btn_row = QHBoxLayout()
        self._motor_toggle_btn = QPushButton("Motors ON")
        self._motor_toggle_btn.setStyleSheet(
            f"QPushButton {{ border-color: {GREEN}; color: {GREEN}; "
            f"font-weight: bold; padding: 6px 20px; }}"
            f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        self._motor_toggle_btn.clicked.connect(self._toggle_motors)
        btn_row.addWidget(self._motor_toggle_btn)

        self._motor_overall_label = QLabel("--")
        self._motor_overall_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {SUBTEXT0};")
        btn_row.addWidget(self._motor_overall_label)
        btn_row.addStretch()
        motor_vbox.addLayout(btn_row)

        # Motor grid
        motor_grid = QGridLayout()
        self._motor = {}

        headers = ["", "Roll", "Pitch", "Yaw"]
        for col_idx, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet(f"font-weight: bold; color: {SUBTEXT0};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            motor_grid.addWidget(lbl, 0, col_idx)

        # Row 1: Motors ON/OFF with LED indicators
        status_lbl = QLabel("Status")
        status_lbl.setStyleSheet(f"color: {SUBTEXT0};")
        motor_grid.addWidget(status_lbl, 1, 0)
        self._motor_leds = {}
        self._motor_status_labels = {}
        for col_idx, axis in enumerate(["Roll", "Pitch", "Yaw"], start=1):
            cell = QHBoxLayout()
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led = LedIndicator("gray", size=14)
            on_lbl = QLabel("OFF")
            on_lbl.setStyleSheet(f"font-weight: bold; color: {COLOR_FAIL};")
            on_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            cell.addWidget(led)
            cell.addWidget(on_lbl)
            cell_widget = QWidget()
            cell_widget.setLayout(cell)
            motor_grid.addWidget(cell_widget, 1, col_idx)
            self._motor_leds[col_idx] = led
            self._motor_status_labels[col_idx] = on_lbl

        motor_rows = [
            ("Power", "motor_power"),
            ("Balance Err", "balance_error"),
            ("Stator-Rotor", "stator_rotor_angle"),
            ("Motor Out", "motor_out"),
        ]
        for row, (label, prefix) in enumerate(motor_rows, start=2):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {SUBTEXT0};")
            motor_grid.addWidget(lbl, row, 0)
            for col_idx, suffix in enumerate(["_1", "_2", "_3"], start=1):
                key = prefix + suffix
                val_lbl = QLabel("---")
                val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                val_lbl.setStyleSheet(f"font-weight: bold; color: {TEXT};")
                motor_grid.addWidget(val_lbl, row, col_idx)
                self._motor[key] = val_lbl

        motor_vbox.addLayout(motor_grid)
        mid_layout.addWidget(motor_group)
        main_layout.addLayout(mid_layout)

        # === Error/Diagnostics panel ===
        self._error_group = QGroupBox("Diagnostics")
        error_layout = QVBoxLayout(self._error_group)
        self._error_led = LedIndicator("green", size=18)
        self._error_summary_label = QLabel("No errors")
        self._error_summary_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {COLOR_OK};")

        error_header = QHBoxLayout()
        error_header.addWidget(self._error_led)
        error_header.addWidget(self._error_summary_label)
        error_header.addStretch()
        error_layout.addLayout(error_header)

        self._error_detail_label = QLabel("")
        self._error_detail_label.setWordWrap(True)
        self._error_detail_label.setStyleSheet(
            f"color: {SUBTEXT1}; padding: 4px; "
            f"background-color: {MANTLE}; border-radius: 4px;")
        self._error_detail_label.setVisible(False)
        error_layout.addWidget(self._error_detail_label)

        main_layout.addWidget(self._error_group)

        # === Bottom row: IMU data + RC ===
        bot_layout = QHBoxLayout()

        # IMU sensor data
        imu_group = QGroupBox("IMU Sensor Data")
        imu_grid = QGridLayout(imu_group)
        self._imu = {}

        imu_fields = [
            ("Accel X", "acc_data_axis_1"),
            ("Accel Y", "acc_data_axis_2"),
            ("Accel Z", "acc_data_axis_3"),
            ("Gyro X", "gyro_data_axis_1"),
            ("Gyro Y", "gyro_data_axis_2"),
            ("Gyro Z", "gyro_data_axis_3"),
            ("IMU Temp", "imu_temperature"),
            ("Frame Temp", "frame_imu_temperature"),
            ("Mag X", "mag_data_1"),
            ("Mag Y", "mag_data_2"),
            ("Mag Z", "mag_data_3"),
            ("IMU G Err", "imu_g_err"),
            ("IMU H Err", "imu_h_err"),
        ]
        for i, (label, key) in enumerate(imu_fields):
            lv = LabeledValue(label)
            imu_grid.addWidget(lv, i // 2, i % 2)
            self._imu[key] = lv

        bot_layout.addWidget(imu_group)

        # RC inputs
        rc_group = QGroupBox("RC Inputs")
        rc_grid = QGridLayout(rc_group)
        self._rc = {}

        rc_fields = [
            ("RC Roll", "rc_roll"),
            ("RC Pitch", "rc_pitch"),
            ("RC Yaw", "rc_yaw"),
            ("RC Cmd", "rc_cmd"),
            ("Ext FC Roll", "ext_fc_roll"),
            ("Ext FC Pitch", "ext_fc_pitch"),
        ]
        for i, (label, key) in enumerate(rc_fields):
            lv = LabeledValue(label)
            rc_grid.addWidget(lv, i // 2, i % 2)
            self._rc[key] = lv

        bot_layout.addWidget(rc_group)
        main_layout.addLayout(bot_layout)
        main_layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Motor toggle ───────────────────────────────────────────────

    def _toggle_motors(self):
        if self._conn is None or not self._conn.is_connected or self._conn.client is None:
            return
        if self._motors_are_on:
            if self._cmd_worker:
                self._cmd_worker.submit("motors_off",
                                        lambda client: client.motors_off())
            else:
                self._conn.client.motors_off()
        else:
            if self._cmd_worker:
                self._cmd_worker.submit("motors_on",
                                        lambda client: client.motors_on())
            else:
                self._conn.client.motors_on()

    def _update_toggle_button(self, any_on: bool):
        """Update the toggle button label and color based on motor state."""
        self._motors_are_on = any_on
        if any_on:
            self._motor_toggle_btn.setText("Motors OFF")
            self._motor_toggle_btn.setStyleSheet(
                f"QPushButton {{ border-color: {RED}; color: {RED}; "
                f"font-weight: bold; padding: 6px 20px; }}"
                f"QPushButton:hover {{ background-color: {SURFACE1}; }}")
        else:
            self._motor_toggle_btn.setText("Motors ON")
            self._motor_toggle_btn.setStyleSheet(
                f"QPushButton {{ border-color: {GREEN}; color: {GREEN}; "
                f"font-weight: bold; padding: 6px 20px; }}"
                f"QPushButton:hover {{ background-color: {SURFACE1}; }}")

    # ── Flicker detection ──────────────────────────────────────────

    @staticmethod
    def _count_transitions(history: collections.deque) -> int:
        """Count the number of ON<->OFF transitions in the history buffer."""
        transitions = 0
        prev = None
        for val in history:
            if prev is not None and val != prev:
                transitions += 1
            prev = val
        return transitions

    def _detect_flicker(self, axis_idx: int) -> bool:
        """Returns True if the axis is flickering (rapid ON/OFF cycling)."""
        history = self._power_history[axis_idx]
        if len(history) < 6:  # need minimum samples
            return False
        return self._count_transitions(history) >= _FLICKER_THRESHOLD

    # ── Telemetry update ───────────────────────────────────────────

    def update_telemetry(self, data: RealtimeData4InCmd):
        """Update all dashboard fields from a RealtimeData4InCmd."""
        # Angles
        roll = to_degree(data.imu_angle_1)
        pitch = to_degree(data.imu_angle_2)
        yaw = to_degree(data.imu_angle_3)

        self._gauges["Roll"].set_angle(roll)
        self._gauges["Pitch"].set_angle(pitch)
        self._gauges["Yaw"].set_angle(yaw)

        # Frame angles
        frame_roll = to_degree(data.frame_imu_angle_1)
        frame_pitch = to_degree(data.frame_imu_angle_2)
        frame_yaw = to_degree(data.frame_imu_angle_3)
        self._gauges["Roll"].set_frame_angle(frame_roll)
        self._gauges["Pitch"].set_frame_angle(frame_pitch)
        self._gauges["Yaw"].set_frame_angle(frame_yaw)

        # Target angles
        target_roll = to_degree(data.target_angle_1)
        target_pitch = to_degree(data.target_angle_2)
        target_yaw = to_degree(data.target_angle_3)
        self._gauges["Roll"].set_target(target_roll)
        self._gauges["Pitch"].set_target(target_pitch)
        self._gauges["Yaw"].set_target(target_yaw)

        # IMU/Frame/Target readouts
        self._gauges["Roll_imu"].set_value(roll)
        self._gauges["Pitch_imu"].set_value(pitch)
        self._gauges["Yaw_imu"].set_value(yaw)
        self._gauges["Roll_frame"].set_value(frame_roll)
        self._gauges["Pitch_frame"].set_value(frame_pitch)
        self._gauges["Yaw_frame"].set_value(frame_yaw)
        self._gauges["Roll_target"].set_value(target_roll)
        self._gauges["Pitch_target"].set_value(target_pitch)
        self._gauges["Yaw_target"].set_value(target_yaw)

        # System status
        self._sys["bat_level"].set_value(data.bat_level)
        self._sys["current"].set_value(data.current)
        self._sys["cycle_time"].set_value(data.cycle_time)
        self._sys["system_error"].set_value(
            data.system_error,
            color=COLOR_FAIL if data.system_error != 0 else None
        )
        self._sys["system_sub_error"].set_value(data.system_sub_error)
        self._sys["serial_err_cnt"].set_value(data.serial_err_cnt)
        self._sys["i2c_error_count"].set_value(
            data.i2c_error_count,
            color=COLOR_WARN if data.i2c_error_count > 10 else None
        )
        self._sys["error_code"].set_value(data.error_code)
        self._sys["cur_profile"].set_value(data.cur_profile + 1)
        self._sys["rt_data_flags"].set_value(f"0x{data.rt_data_flags:04X}")
        self._sys["cur_imu"].set_value(data.cur_imu)

        # Motor status + flicker detection
        axis_names = ["Roll", "Pitch", "Yaw"]
        any_on = False
        any_flickering = False
        flicker_axes = []

        for suffix, col_idx in [("_1", 1), ("_2", 2), ("_3", 3)]:
            power = getattr(data, f"motor_power{suffix}")
            self._motor[f"motor_power{suffix}"].setText(str(power))

            motor_on = power > 0
            if motor_on:
                any_on = True

            # Track power history for flicker detection
            self._power_history[col_idx].append(motor_on)
            flickering = self._detect_flicker(col_idx)

            if flickering:
                any_flickering = True
                flicker_axes.append(axis_names[col_idx - 1])

            # LED + status label
            if flickering:
                self._motor_leds[col_idx].set_color("yellow")
                self._motor_status_labels[col_idx].setText("UNSTABLE")
                self._motor_status_labels[col_idx].setStyleSheet(
                    f"font-weight: bold; color: {YELLOW};")
            elif motor_on:
                self._motor_leds[col_idx].set_color("green")
                self._motor_status_labels[col_idx].setText("ON")
                self._motor_status_labels[col_idx].setStyleSheet(
                    f"font-weight: bold; color: {COLOR_OK};")
            else:
                self._motor_leds[col_idx].set_color("red")
                self._motor_status_labels[col_idx].setText("OFF")
                self._motor_status_labels[col_idx].setStyleSheet(
                    f"font-weight: bold; color: {COLOR_FAIL};")

            # Power value coloring
            if power >= 230:
                self._motor[f"motor_power{suffix}"].setStyleSheet(f"font-weight: bold; color: {COLOR_FAIL};")
            elif power >= 180:
                self._motor[f"motor_power{suffix}"].setStyleSheet(f"font-weight: bold; color: {COLOR_WARN};")
            else:
                self._motor[f"motor_power{suffix}"].setStyleSheet(f"font-weight: bold; color: {TEXT};")

            balance = getattr(data, f"balance_error{suffix}")
            self._motor[f"balance_error{suffix}"].setText(str(balance))

            stator = getattr(data, f"stator_rotor_angle{suffix}")
            self._motor[f"stator_rotor_angle{suffix}"].setText(str(stator))

            motor_out = getattr(data, f"motor_out{suffix}")
            self._motor[f"motor_out{suffix}"].setText(str(motor_out))

        # Overall motor label
        if any_flickering:
            self._motor_overall_label.setText(
                f"UNSTABLE: {', '.join(flicker_axes)} flickering")
            self._motor_overall_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {YELLOW};")
        elif any_on:
            self._motor_overall_label.setText("All motors running")
            self._motor_overall_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {COLOR_OK};")
        else:
            self._motor_overall_label.setText("Motors OFF")
            self._motor_overall_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {COLOR_FAIL};")

        # Update toggle button state
        self._update_toggle_button(any_on)

        # === Diagnostics panel ===
        self._update_diagnostics(data, any_flickering, flicker_axes)

        # IMU sensor data
        self._imu["acc_data_axis_1"].set_value(data.acc_data_axis_1)
        self._imu["acc_data_axis_2"].set_value(data.acc_data_axis_2)
        self._imu["acc_data_axis_3"].set_value(data.acc_data_axis_3)
        self._imu["gyro_data_axis_1"].set_value(data.gyro_data_axis_1)
        self._imu["gyro_data_axis_2"].set_value(data.gyro_data_axis_2)
        self._imu["gyro_data_axis_3"].set_value(data.gyro_data_axis_3)
        self._imu["imu_temperature"].set_value(f"{data.imu_temperature} C")
        self._imu["frame_imu_temperature"].set_value(f"{data.frame_imu_temperature} C")
        self._imu["mag_data_1"].set_value(data.mag_data_1)
        self._imu["mag_data_2"].set_value(data.mag_data_2)
        self._imu["mag_data_3"].set_value(data.mag_data_3)
        self._imu["imu_g_err"].set_value(data.imu_g_err)
        self._imu["imu_h_err"].set_value(data.imu_h_err)

        # RC inputs
        self._rc["rc_roll"].set_value(data.rc_roll)
        self._rc["rc_pitch"].set_value(data.rc_pitch)
        self._rc["rc_yaw"].set_value(data.rc_yaw)
        self._rc["rc_cmd"].set_value(data.rc_cmd)
        self._rc["ext_fc_roll"].set_value(data.ext_fc_roll)
        self._rc["ext_fc_pitch"].set_value(data.ext_fc_pitch)

    # ── Diagnostics ────────────────────────────────────────────────

    def _update_diagnostics(self, data, any_flickering: bool, flicker_axes: list[str]):
        """Update the diagnostics panel with decoded errors and flicker warnings."""
        sys_err = data.system_error
        sub_err = data.system_sub_error

        errors = decode_system_errors(sys_err)
        sub = decode_sub_error(sub_err)
        has_errors = bool(errors) or sub is not None or any_flickering

        if not has_errors:
            self._error_led.set_color("green")
            self._error_summary_label.setText("No errors — system healthy")
            self._error_summary_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {COLOR_OK};")
            self._error_detail_label.setVisible(False)
            return

        # Determine severity
        has_critical = any(bit in (0x0080, 0x0800, 0x1000, 0x2000) for bit, _, _, _ in errors)
        if has_critical:
            self._error_led.set_color("red")
            self._error_summary_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {COLOR_FAIL};")
        elif errors:
            self._error_led.set_color("red")
            self._error_summary_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {COLOR_FAIL};")
        else:
            self._error_led.set_color("yellow")
            self._error_summary_label.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {YELLOW};")

        self._error_summary_label.setText(format_error_summary(sys_err, sub_err))

        # Build detail text
        lines = []

        for bit, name, desc, fix in errors:
            lines.append(
                f"<b style='color:{COLOR_FAIL}'>Error 0x{bit:04X}: {name}</b><br>"
                f"{desc}<br>"
                f"<span style='color:{GREEN}'>Fix: {fix}</span>")

        if sub is not None:
            sub_name, sub_desc, sub_fix = sub
            lines.append(
                f"<b style='color:{PEACH}'>Sub-error {sub_err}: {sub_name}</b><br>"
                f"{sub_desc}<br>"
                f"<span style='color:{GREEN}'>Fix: {sub_fix}</span>")

        if any_flickering:
            axes_str = ", ".join(flicker_axes)
            lines.append(
                f"<b style='color:{YELLOW}'>Motor flickering: {axes_str}</b><br>"
                f"Motor power is rapidly cycling ON/OFF. This typically indicates:<br>"
                f"- Mechanical vibration or loose motor mount<br>"
                f"- Motor power (POWER parameter) set too low for the payload<br>"
                f"- PID tuning issues causing oscillation<br>"
                f"<span style='color:{GREEN}'>Fix: Check motor mounting, increase POWER, "
                f"or re-tune PID in SimpleBGC GUI.</span>")

        self._error_detail_label.setText("<br><br>".join(lines))
        self._error_detail_label.setVisible(True)
