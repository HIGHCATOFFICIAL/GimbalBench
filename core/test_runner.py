"""Gimbal validation test runner with telemetry bridging and wizard support."""
import time
import math
import logging
import threading
from PyQt6.QtCore import QThread, pyqtSignal

from sbgc.units import to_degree
from core.test_models import (
    TestStatus, TestCategory, TelemetrySample, TestCaseResult, TestSuiteConfig,
)
from core.test_cases import TestCaseDefinition

log = logging.getLogger(__name__)


class TestRunner(QThread):
    """Runs the gimbal validation test suite.

    Telemetry bridging: the main window forwards TelemetryWorker data to
    on_telemetry(), so this thread never does its own serial reads.
    Gimbal commands are sent via the CommandWorker.submit() pattern or
    directly through the SbgcClient reference.
    """

    test_started = pyqtSignal(str)              # test case name
    test_completed = pyqtSignal(object)         # TestCaseResult
    suite_completed = pyqtSignal(list)          # list[TestCaseResult]
    log_message = pyqtSignal(str)
    progress = pyqtSignal(int, int)             # current, total
    status_detail = pyqtSignal(str)             # sub-step activity text
    waiting_for_user = pyqtSignal(str)          # instruction text
    user_action_needed = pyqtSignal(str)        # button label hint
    page_request = pyqtSignal(int)              # request UI page switch (1=wizard, 2=running)

    def __init__(self, connection_manager, config: TestSuiteConfig,
                 test_cases: list[TestCaseDefinition], parent=None):
        super().__init__(parent)
        self._conn = connection_manager
        self._config = config
        self._cases = test_cases
        self._running = False

        # Telemetry bridging: updated from main thread via on_telemetry()
        self._telem_lock = threading.Lock()
        self._latest_telem = None  # raw RealtimeData4InCmd

        # Wizard synchronization
        self._user_event = threading.Event()

    # -- Telemetry bridging (called from main/GUI thread) --

    def on_telemetry(self, data) -> None:
        """Thread-safe slot: store latest telemetry from TelemetryWorker."""
        with self._telem_lock:
            self._latest_telem = data

    def _get_telemetry(self):
        """Read latest telemetry snapshot (thread-safe)."""
        with self._telem_lock:
            return self._latest_telem

    def _make_sample(self, data) -> TelemetrySample | None:
        if data is None:
            return None
        return TelemetrySample(
            timestamp=time.time(),
            imu_angles=(
                to_degree(data.imu_angle_1),
                to_degree(data.imu_angle_2),
                to_degree(data.imu_angle_3),
            ),
            motor_power=(data.motor_power_1, data.motor_power_2, data.motor_power_3),
            system_error=data.system_error,
            balance_error=(data.balance_error_1, data.balance_error_2, data.balance_error_3),
        )

    # -- Wizard interaction --

    def user_continue(self) -> None:
        """Called from UI when user presses Ready/Continue."""
        self._user_event.set()

    def user_skip(self) -> None:
        """Called from UI when user presses Skip."""
        self._user_event.set()
        self._skip_current = True

    # -- Polling helpers --

    def _wait_for_angles(self, target_pitch: float | None, target_yaw: float | None,
                         tolerance: float, timeout: float) -> tuple[bool, list[TelemetrySample]]:
        """Poll telemetry until angles are within tolerance of target. Returns (reached, samples)."""
        samples: list[TelemetrySample] = []
        deadline = time.time() + timeout
        last_detail_t = 0.0
        while self._running and time.time() < deadline:
            data = self._get_telemetry()
            sample = self._make_sample(data)
            if sample:
                samples.append(sample)
                _, pitch, yaw = sample.imu_angles
                pitch_ok = target_pitch is None or abs(pitch - target_pitch) <= tolerance
                yaw_ok = target_yaw is None or abs(yaw - target_yaw) <= tolerance
                if pitch_ok and yaw_ok:
                    return True, samples
                # Emit sub-step detail every ~1s
                now = time.time()
                if now - last_detail_t >= 1.0:
                    remaining = deadline - now
                    parts = []
                    if target_pitch is not None:
                        parts.append(f"pitch {pitch:+.1f}\u00b0\u2192{target_pitch:.0f}\u00b0")
                    if target_yaw is not None:
                        parts.append(f"yaw {yaw:+.1f}\u00b0\u2192{target_yaw:.0f}\u00b0")
                    self.status_detail.emit(
                        f"Waiting for angles: {', '.join(parts)}  ({remaining:.0f}s left)")
                    last_detail_t = now
            time.sleep(0.1)
        return False, samples

    def _wait_for_motors_on(self, timeout: float) -> tuple[bool, list[TelemetrySample]]:
        """Poll until any motor_power > 0."""
        samples: list[TelemetrySample] = []
        deadline = time.time() + timeout
        last_detail_t = 0.0
        while self._running and time.time() < deadline:
            data = self._get_telemetry()
            sample = self._make_sample(data)
            if sample:
                samples.append(sample)
                if any(p > 0 for p in sample.motor_power):
                    return True, samples
            now = time.time()
            if now - last_detail_t >= 1.0:
                remaining = deadline - now
                pwr = f"{sample.motor_power}" if sample else "no data"
                self.status_detail.emit(
                    f"Waiting for motors ON: power={pwr}  ({remaining:.0f}s left)")
                last_detail_t = now
            time.sleep(0.1)
        return False, samples

    def _record_stability(self, target_pitch: float | None, target_yaw: float | None,
                          duration: float) -> list[TelemetrySample]:
        """Sample telemetry at ~10Hz for duration seconds."""
        samples: list[TelemetrySample] = []
        start = time.time()
        deadline = start + duration
        last_detail_t = 0.0
        while self._running and time.time() < deadline:
            data = self._get_telemetry()
            sample = self._make_sample(data)
            if sample:
                samples.append(sample)
            now = time.time()
            if now - last_detail_t >= 1.0:
                elapsed = now - start
                self.status_detail.emit(
                    f"Recording stability: {elapsed:.0f}s / {duration:.0f}s")
                last_detail_t = now
            time.sleep(0.1)
        return samples

    @staticmethod
    def _compute_deviation(samples: list[TelemetrySample],
                           target_pitch: float | None,
                           target_yaw: float | None) -> tuple[float, float, float]:
        """Compute max, mean, stddev deviation from target angles."""
        errors: list[float] = []
        for s in samples:
            _, pitch, yaw = s.imu_angles
            err = 0.0
            if target_pitch is not None:
                err = max(err, abs(pitch - target_pitch))
            if target_yaw is not None:
                err = max(err, abs(yaw - target_yaw))
            errors.append(err)
        if not errors:
            return 0.0, 0.0, 0.0
        max_err = max(errors)
        mean_err = sum(errors) / len(errors)
        variance = sum((e - mean_err) ** 2 for e in errors) / len(errors)
        stddev = math.sqrt(variance)
        return max_err, mean_err, stddev

    # -- Main run loop --

    def run(self):
        self._running = True
        self._skip_current = False
        total = len(self._cases)
        results: list[TestCaseResult] = []

        self.log_message.emit(f"Starting test suite: {total} test cases")

        for i, case in enumerate(self._cases):
            if not self._running:
                self.log_message.emit("Test suite aborted by user")
                break

            self.progress.emit(i, total)
            self.test_started.emit(case.name)
            self.log_message.emit(f"[{i+1}/{total}] {case.category.value}: {case.name}")

            result = TestCaseResult(name=case.name, category=case.category)
            result.status = TestStatus.RUNNING
            start = time.time()

            try:
                if case.category == TestCategory.MOTOR_STARTUP:
                    self._run_motor_startup_test(case, result)
                elif case.category == TestCategory.RECOVERY:
                    self._run_recovery_test(case, result)
                elif case.category == TestCategory.SWEEP:
                    self._run_sweep_test(case, result)
                elif case.category == TestCategory.STABILITY:
                    self._run_stability_test(case, result)
            except Exception as e:
                result.status = TestStatus.FAIL
                result.message = f"Exception: {e}"
                self.log_message.emit(f"  ERROR: {e}")

            result.duration_s = time.time() - start

            if result.status == TestStatus.RUNNING:
                result.status = TestStatus.FAIL
                result.message = result.message or "Did not complete"

            status_str = result.status.value
            self.log_message.emit(f"  Result: {status_str} ({result.duration_s:.1f}s) {result.message}")
            results.append(result)
            self.test_completed.emit(result)

        self.progress.emit(total, total)
        self.suite_completed.emit(results)
        self.log_message.emit("Test suite complete")
        self._running = False

    # -- Motor state helpers --

    def _motors_are_on(self) -> bool:
        """Check if motors are currently on from latest telemetry."""
        data = self._get_telemetry()
        if data is None:
            return False
        return any(p > 0 for p in (data.motor_power_1, data.motor_power_2, data.motor_power_3))

    def _ensure_motors_on(self, result: TestCaseResult) -> bool:
        """Check if motors are on; if not, turn them on and wait for confirmation.

        Returns True if motors are on (or successfully turned on), False on failure.
        Appends telemetry samples to result.
        """
        if self._motors_are_on():
            self.log_message.emit("  Motors already on")
            return True

        if not self._conn.is_connected or self._conn.client is None:
            result.status = TestStatus.FAIL
            result.message = "Not connected"
            return False

        self.log_message.emit("  Motors are OFF - sending motors_on command...")
        self.status_detail.emit("Turning motors on...")
        try:
            self._conn.client.motors_on()
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = f"Failed to send motors_on: {e}"
            return False

        # Wait for motors to come on (use startup timeout as upper bound)
        timeout = min(self._config.startup_timeout_s, 15.0)
        motors_on, samples = self._wait_for_motors_on(timeout)
        result.samples.extend(samples)

        if motors_on:
            self.log_message.emit("  Motors are now ON")
            # Brief settle time
            time.sleep(0.5)
            return True
        else:
            result.status = TestStatus.FAIL
            result.message = "Motors did not turn on after motors_on command"
            return False

    # -- Category runners --

    def _run_motor_startup_test(self, case: TestCaseDefinition, result: TestCaseResult):
        """Wizard flow: instruct user, wait for continue, then check motors + angles."""
        self.page_request.emit(1)  # switch to wizard page
        self._skip_current = False

        # Wait for user to position gimbal and press Ready
        result.status = TestStatus.WAITING_USER
        self.waiting_for_user.emit(case.instruction)
        self.user_action_needed.emit("Press 'Ready' when gimbal has been power-cycled")

        self._user_event.clear()
        self._user_event.wait()  # blocks until user_continue() or user_skip()

        if self._skip_current:
            result.status = TestStatus.SKIPPED
            result.message = "Skipped by user"
            return

        if not self._running:
            result.status = TestStatus.ABORTED
            return

        result.status = TestStatus.RUNNING
        self.log_message.emit("  Waiting for motors to power on...")
        timeout = self._config.startup_timeout_s

        # Wait for motors to come on
        motors_on, samples = self._wait_for_motors_on(timeout)
        result.samples.extend(samples)

        if not motors_on:
            result.status = TestStatus.FAIL
            result.message = "Motors did not power on within timeout"
            return

        self.log_message.emit("  Motors on - waiting for angles to reach home...")

        # Check for system errors
        last_sample = samples[-1] if samples else None
        if last_sample and last_sample.system_error != 0:
            result.status = TestStatus.FAIL
            result.message = f"System error: {last_sample.system_error}"
            return

        # Wait for angles to converge to home (~0)
        reached, angle_samples = self._wait_for_angles(
            0.0, None, self._config.angle_tolerance_deg, timeout)
        result.samples.extend(angle_samples)

        if reached:
            result.status = TestStatus.PASS
            result.message = "Motors started and angles reached home"
        else:
            # Check for system error in last sample
            last = angle_samples[-1] if angle_samples else last_sample
            if last and last.system_error != 0:
                result.status = TestStatus.FAIL
                result.message = f"System error {last.system_error} during recovery"
            else:
                result.status = TestStatus.FAIL
                result.message = "Angles did not reach home within timeout"

    def _run_recovery_test(self, case: TestCaseDefinition, result: TestCaseResult):
        """Automatic: send extreme angle, then home/center, verify return."""
        self.page_request.emit(2)  # running page

        if not self._conn.is_connected or self._conn.client is None:
            result.status = TestStatus.FAIL
            result.message = "Not connected"
            return

        # Ensure motors are on before testing
        if not self._ensure_motors_on(result):
            return

        client = self._conn.client
        action = case.params.get("action", "")
        timeout = self._config.move_timeout_s
        tolerance = self._config.angle_tolerance_deg

        if action == "home_from_angle":
            pitch = case.params["pitch_deg"]
            self.log_message.emit(f"  Sending pitch to {pitch}\u00b0...")
            client.set_angles(pitch, speed_dps=self._config.speed_dps)

            # Wait to reach the extreme angle
            reached, samples = self._wait_for_angles(pitch, None, tolerance, timeout)
            result.samples.extend(samples)
            if not reached:
                result.status = TestStatus.FAIL
                result.message = f"Could not reach {pitch}\u00b0 before recovery test"
                return

            time.sleep(0.5)
            self.log_message.emit("  Commanding home...")
            client.home()

            reached, samples = self._wait_for_angles(0.0, None, tolerance, timeout)
            result.samples.extend(samples)
            if reached:
                result.status = TestStatus.PASS
                result.message = f"Returned home from {pitch}\u00b0"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Did not return home from {pitch}\u00b0 within timeout"

        elif action == "center_yaw_from":
            yaw = case.params["yaw_deg"]
            self.log_message.emit(f"  Sending yaw to {yaw}\u00b0...")
            client.set_angles(0.0, yaw_deg=yaw, speed_dps=self._config.speed_dps)

            reached, samples = self._wait_for_angles(None, yaw, tolerance, timeout)
            result.samples.extend(samples)
            if not reached:
                result.status = TestStatus.FAIL
                result.message = f"Could not reach yaw {yaw}\u00b0 before recovery test"
                return

            time.sleep(0.5)
            self.log_message.emit("  Commanding center yaw...")
            client.center_yaw()

            reached, samples = self._wait_for_angles(None, 0.0, tolerance, timeout)
            result.samples.extend(samples)
            if reached:
                result.status = TestStatus.PASS
                result.message = f"Yaw centered from {yaw}\u00b0"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Yaw did not center from {yaw}\u00b0 within timeout"

        elif action == "home_after_rate":
            yaw_dps = case.params["yaw_dps"]
            spin_dur = case.params["spin_duration_s"]
            self.log_message.emit(f"  Spinning yaw at {yaw_dps} dps for {spin_dur}s...")

            deadline = time.time() + spin_dur
            while self._running and time.time() < deadline:
                client.set_rates(yaw_dps, None)
                time.sleep(0.02)

            self.log_message.emit("  Commanding home...")
            client.home()

            reached, samples = self._wait_for_angles(0.0, None, tolerance, timeout)
            result.samples.extend(samples)
            if reached:
                result.status = TestStatus.PASS
                result.message = "Returned home after rate spin"
            else:
                result.status = TestStatus.FAIL
                result.message = "Did not return home after rate spin within timeout"

        else:
            result.status = TestStatus.FAIL
            result.message = f"Unknown recovery action: {action}"

    def _run_sweep_test(self, case: TestCaseDefinition, result: TestCaseResult):
        """Automatic: step through each angle in the sweep pattern."""
        self.page_request.emit(2)

        if not self._conn.is_connected or self._conn.client is None:
            result.status = TestStatus.FAIL
            result.message = "Not connected"
            return

        # Ensure motors are on before testing
        if not self._ensure_motors_on(result):
            return

        client = self._conn.client
        axis = case.params.get("axis", "pitch")
        tolerance = self._config.angle_tolerance_deg
        timeout = self._config.move_timeout_s
        speed = self._config.speed_dps

        if axis == "combined":
            # Run pitch sweep then yaw sweep sequentially
            step = self._config.sweep_step_deg
            pitch_angles: list[float] = [0.0]
            a = 0.0
            while a > -90.0:
                a = max(a - step, -90.0)
                pitch_angles.append(a)
            while a < 0.0:
                a = min(a + step, 0.0)
                pitch_angles.append(a)

            yaw_angles: list[float] = [0.0]
            a = 0.0
            while a > -90.0:
                a = max(a - step, -90.0)
                yaw_angles.append(a)
            while a < 90.0:
                a = min(a + step, 90.0)
                yaw_angles.append(a)
            while a > 0.0:
                a = max(a - step, 0.0)
                yaw_angles.append(a)

            all_ok = True
            for ang in pitch_angles:
                if not self._running:
                    break
                self.log_message.emit(f"  Pitch -> {ang}\u00b0")
                client.set_angles(ang, speed_dps=speed)
                reached, samples = self._wait_for_angles(ang, None, tolerance, timeout)
                result.samples.extend(samples)
                if not reached:
                    all_ok = False
                    self.log_message.emit(f"  TIMEOUT at pitch {ang}\u00b0")

            for ang in yaw_angles:
                if not self._running:
                    break
                self.log_message.emit(f"  Yaw -> {ang}\u00b0")
                client.set_angles(0.0, yaw_deg=ang, speed_dps=speed)
                reached, samples = self._wait_for_angles(None, ang, tolerance, timeout)
                result.samples.extend(samples)
                if not reached:
                    all_ok = False
                    self.log_message.emit(f"  TIMEOUT at yaw {ang}\u00b0")
        else:
            angles = case.params.get("angles", [0.0])
            all_ok = True
            for ang in angles:
                if not self._running:
                    break
                self.log_message.emit(f"  {axis.title()} -> {ang}\u00b0")
                if axis == "pitch":
                    client.set_angles(ang, speed_dps=speed)
                    reached, samples = self._wait_for_angles(ang, None, tolerance, timeout)
                else:
                    client.set_angles(0.0, yaw_deg=ang, speed_dps=speed)
                    reached, samples = self._wait_for_angles(None, ang, tolerance, timeout)
                result.samples.extend(samples)
                if not reached:
                    all_ok = False
                    self.log_message.emit(f"  TIMEOUT at {axis} {ang}\u00b0")

        if all_ok:
            result.status = TestStatus.PASS
            result.message = f"{axis.title()} sweep completed - all targets reached"
        else:
            result.status = TestStatus.FAIL
            result.message = f"{axis.title()} sweep - some targets not reached within tolerance"

    def _run_stability_test(self, case: TestCaseDefinition, result: TestCaseResult):
        """Automatic: command angle, wait, then measure hold stability."""
        self.page_request.emit(2)

        if not self._conn.is_connected or self._conn.client is None:
            result.status = TestStatus.FAIL
            result.message = "Not connected"
            return

        # Ensure motors are on before testing
        if not self._ensure_motors_on(result):
            return

        client = self._conn.client
        pitch = case.params.get("pitch_deg", 0.0)
        yaw = case.params.get("yaw_deg")
        tolerance = self._config.hold_tolerance_deg
        move_timeout = self._config.move_timeout_s
        hold_dur = self._config.hold_duration_s
        speed = self._config.speed_dps

        # Command the position
        self.log_message.emit(f"  Moving to pitch={pitch}\u00b0" +
                              (f", yaw={yaw}\u00b0" if yaw is not None else ""))
        client.set_angles(pitch, yaw_deg=yaw, speed_dps=speed)

        # Wait to reach position
        reached, move_samples = self._wait_for_angles(
            pitch, yaw, self._config.angle_tolerance_deg, move_timeout)
        result.samples.extend(move_samples)
        if not reached:
            result.status = TestStatus.FAIL
            result.message = "Could not reach target position for stability test"
            return

        # Record stability
        self.log_message.emit(f"  Holding for {hold_dur}s...")
        hold_samples = self._record_stability(pitch, yaw, hold_dur)
        result.samples.extend(hold_samples)

        max_err, mean_err, stddev = self._compute_deviation(hold_samples, pitch, yaw)
        result.max_error_deg = max_err
        result.mean_error_deg = mean_err

        self.log_message.emit(
            f"  Deviation: max={max_err:.2f}\u00b0, mean={mean_err:.2f}\u00b0, stddev={stddev:.2f}\u00b0")

        if max_err <= tolerance:
            result.status = TestStatus.PASS
            result.message = (f"Hold stable: max={max_err:.2f}\u00b0, "
                              f"mean={mean_err:.2f}\u00b0 (tol={tolerance}\u00b0)")
        else:
            result.status = TestStatus.FAIL
            result.message = (f"Hold unstable: max={max_err:.2f}\u00b0 > {tolerance}\u00b0 "
                              f"(mean={mean_err:.2f}\u00b0)")

    # -- Control --

    def stop(self):
        self._running = False
        self._user_event.set()  # unblock any wizard wait
        self.wait(5000)
