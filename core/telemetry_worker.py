"""QThread worker that polls CMD_REALTIME_DATA_4 at ~10Hz."""
import time
import logging
from PyQt6.QtCore import QThread, pyqtSignal

from sbgc.ids import CMD_REALTIME_DATA_4
from sbgc.protocol import encode
from sbgc.commands.realtime import parse_realtime_data_4_cmd
from sbgc.models import Angles, RealtimeState
from sbgc.units import to_degree

log = logging.getLogger(__name__)


class TelemetryWorker(QThread):
    """Polls full RealtimeData4 from gimbal and emits parsed data."""

    data_received = pyqtSignal(object)  # RealtimeData4InCmd
    error_occurred = pyqtSignal(str)

    def __init__(self, connection_manager, poll_hz: float = 10.0, parent=None):
        super().__init__(parent)
        self._conn = connection_manager
        self._poll_interval = 1.0 / poll_hz
        self._running = False

    def run(self):
        self._running = True
        consecutive_timeouts = 0
        log.info("TelemetryWorker started at %.1f Hz", 1.0 / self._poll_interval)

        while self._running:
            if not self._conn.is_connected or self._conn.client is None:
                time.sleep(0.1)
                continue

            client = self._conn.client
            try:
                # Match the pattern used by client._fetch_state():
                # write outside the lock, _wait_for acquires the lock internally
                # to pump rx and find the response.
                client._t.write(encode(CMD_REALTIME_DATA_4))
                payload = client._wait_for(CMD_REALTIME_DATA_4, timeout_s=0.3)
                parsed = parse_realtime_data_4_cmd(payload)

                # Update the client's cached state so set_rates() etc. work
                angles = Angles(
                    roll_deg=to_degree(parsed.imu_angle_1),
                    pitch_deg=to_degree(parsed.imu_angle_2),
                    yaw_deg=to_degree(parsed.imu_angle_3),
                )
                cur_profile = int(parsed.cur_profile)
                cur_profile_id = cur_profile + 1 if 0 <= cur_profile <= 4 else None
                state = RealtimeState(
                    angles=angles,
                    rt_data_flags=int(parsed.rt_data_flags),
                    system_error=int(parsed.system_error),
                    system_sub_error=int(parsed.system_sub_error),
                    cur_profile_id=cur_profile_id,
                )
                client._set_last_state(state)

                self.data_received.emit(parsed)
                consecutive_timeouts = 0

            except TimeoutError:
                consecutive_timeouts += 1
                if consecutive_timeouts <= 3 or consecutive_timeouts % 50 == 0:
                    msg = f"Telemetry timeout ({consecutive_timeouts} consecutive)"
                    log.warning(msg)
                    self.error_occurred.emit(msg)
            except Exception as e:
                if self._running:
                    log.error("Telemetry poll error: %s", e, exc_info=True)
                    self.error_occurred.emit(str(e))

            time.sleep(self._poll_interval)

        log.info("TelemetryWorker stopped")

    def stop(self):
        self._running = False
        self.wait(2000)
