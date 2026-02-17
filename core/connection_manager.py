"""Connection manager wrapping SbgcClient with Serial/UDP transport."""
import logging
import threading
from PyQt6.QtCore import QObject, pyqtSignal

from sbgc.client import SbgcClient
from sbgc.managed_client import ManagedSbgcClient
from sbgc.transport import SerialTransport
from sbgc.udp_tunnel_transport import UdpTunnelTransport, UdpTunnelConfig
from sbgc.config import SerialCfg
from sbgc.ids import CMD_REALTIME_DATA_4
from sbgc.protocol import encode
from sbgc.commands.realtime import parse_realtime_data_4_cmd

log = logging.getLogger(__name__)


class ConnectionManager(QObject):
    """Manages gimbal connection lifecycle. Emits Qt signals for state changes."""

    connected = pyqtSignal(bool)   # bool = probe_ok (True = gimbal responded)
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client: SbgcClient | ManagedSbgcClient | None = None
        self._transport = None
        self._is_connected = False
        self._mode = "serial"  # "serial" or "udp"

    @property
    def client(self) -> SbgcClient | ManagedSbgcClient | None:
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _probe_gimbal(self, client: SbgcClient) -> bool:
        """Verify the gimbal responds to a CMD_REALTIME_DATA_4 request."""
        for attempt in range(3):
            try:
                client._t.write(encode(CMD_REALTIME_DATA_4))
                payload = client._wait_for(CMD_REALTIME_DATA_4, timeout_s=0.5)
                parsed = parse_realtime_data_4_cmd(payload)
                log.info("Gimbal probe OK: system_error=%d, profile=%d",
                         parsed.system_error, parsed.cur_profile)
                return True
            except TimeoutError:
                log.warning("Gimbal probe attempt %d/3 timed out", attempt + 1)
            except Exception as e:
                log.warning("Gimbal probe attempt %d/3 failed: %s", attempt + 1, e)
        return False

    def connect_serial(self, port: str, baud: int, auto_detect: bool = False):
        """Connect via serial port. Runs probe in background thread."""
        # Do the actual connection in a thread so UI doesn't freeze during probe
        threading.Thread(
            target=self._connect_serial_worker,
            args=(port, baud, auto_detect),
            daemon=True,
        ).start()

    def _connect_serial_worker(self, port: str, baud: int, auto_detect: bool):
        try:
            self.disconnect()
            if auto_detect:
                cfg = SerialCfg(port=port, baud=baud, auto_detect=True)
                client = ManagedSbgcClient(cfg)
                client.open()
                self._client = client
                # ManagedSbgcClient probes internally
                probe_ok = getattr(client, '_connected', False)
            else:
                transport = SerialTransport(port, baud=baud)
                transport.open()
                self._transport = transport
                client = SbgcClient(transport)
                self._client = client
                # Probe to verify gimbal responds
                probe_ok = self._probe_gimbal(client)

            self._mode = "serial"
            self._is_connected = True
            log.info("Connected via serial: %s @ %d (probe=%s)", port, baud, probe_ok)
            self.connected.emit(probe_ok)
        except Exception as e:
            self._is_connected = False
            self._client = None
            self._transport = None
            log.error("Serial connection failed: %s", e)
            self.error.emit(str(e))

    def connect_udp(self, bridge_ip: str, bridge_port: int, pc_port: int):
        """Connect via UDP tunnel. Runs probe in background thread."""
        threading.Thread(
            target=self._connect_udp_worker,
            args=(bridge_ip, bridge_port, pc_port),
            daemon=True,
        ).start()

    def _connect_udp_worker(self, bridge_ip: str, bridge_port: int, pc_port: int):
        try:
            self.disconnect()
            cfg = UdpTunnelConfig(
                bridge_ip=bridge_ip,
                bridge_rx_port=bridge_port,
                pc_rx_port=pc_port,
            )
            transport = UdpTunnelTransport(cfg)
            transport.open()
            self._transport = transport
            client = SbgcClient(transport)
            self._client = client

            probe_ok = self._probe_gimbal(client)

            self._mode = "udp"
            self._is_connected = True
            log.info("Connected via UDP: %s:%d (probe=%s)", bridge_ip, bridge_port, probe_ok)
            self.connected.emit(probe_ok)
        except Exception as e:
            self._is_connected = False
            self._client = None
            self._transport = None
            log.error("UDP connection failed: %s", e)
            self.error.emit(str(e))

    def disconnect(self):
        """Disconnect and clean up."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                log.warning("Error during disconnect: %s", e)
            self._client = None
            self._transport = None
        if self._is_connected:
            self._is_connected = False
            self.disconnected.emit()
