"""QThread worker that processes a queue of gimbal commands."""
import logging
import queue
from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)


class CommandWorker(QThread):
    """Processes queued gimbal commands off the GUI thread."""

    command_completed = pyqtSignal(str, bool, str)  # command_name, success, message
    command_started = pyqtSignal(str)

    def __init__(self, connection_manager, parent=None):
        super().__init__(parent)
        self._conn = connection_manager
        self._queue: queue.Queue = queue.Queue()
        self._running = False

    def run(self):
        self._running = True
        log.info("CommandWorker started")

        while self._running:
            try:
                cmd_name, func, args, kwargs = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self._conn.is_connected or self._conn.client is None:
                self.command_completed.emit(cmd_name, False, "Not connected")
                continue

            self.command_started.emit(cmd_name)
            try:
                func(self._conn.client, *args, **kwargs)
                self.command_completed.emit(cmd_name, True, "OK")
            except Exception as e:
                log.error("Command '%s' failed: %s", cmd_name, e)
                self.command_completed.emit(cmd_name, False, str(e))

        log.info("CommandWorker stopped")

    def submit(self, name: str, func, *args, **kwargs):
        """Queue a command. func(client, *args, **kwargs) will be called."""
        self._queue.put((name, func, args, kwargs))

    def stop(self):
        self._running = False
        self.wait(2000)
