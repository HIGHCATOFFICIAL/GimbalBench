"""Log viewer tab with severity filtering."""
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                              QCheckBox, QPushButton, QLabel)
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QTextCharFormat, QColor

from ui.styles import TEXT, COLOR_OK, COLOR_WARN, COLOR_FAIL, SUBTEXT0, BLUE


class LogTab(QWidget):
    """Scrolling log viewer with severity filters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filters:"))

        self._filters = {}
        for level, color in [("DEBUG", SUBTEXT0), ("INFO", COLOR_OK),
                              ("WARNING", COLOR_WARN), ("ERROR", COLOR_FAIL)]:
            cb = QCheckBox(level)
            cb.setChecked(level != "DEBUG")
            cb.setStyleSheet(f"color: {color};")
            cb.toggled.connect(self._apply_filter)
            filter_layout.addWidget(cb)
            self._filters[level] = cb

        filter_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear)
        filter_layout.addWidget(clear_btn)

        self._count_label = QLabel("0 entries")
        self._count_label.setStyleSheet(f"color: {SUBTEXT0};")
        filter_layout.addWidget(self._count_label)

        layout.addLayout(filter_layout)

        # Log view
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        layout.addWidget(self._log_view)

        # Internal log storage
        self._entries: list[tuple[str, str, str]] = []  # (timestamp, level, message)

    def append(self, level: str, message: str):
        """Add a log entry."""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._entries.append((ts, level, message))
        self._count_label.setText(f"{len(self._entries)} entries")

        if self._filters.get(level, self._filters.get("INFO")).isChecked():
            self._append_formatted(ts, level, message)

    def _append_formatted(self, ts: str, level: str, message: str):
        colors = {
            "DEBUG": SUBTEXT0,
            "INFO": COLOR_OK,
            "WARNING": COLOR_WARN,
            "ERROR": COLOR_FAIL,
        }
        color = colors.get(level, TEXT)
        self._log_view.append(
            f'<span style="color:{SUBTEXT0}">[{ts}]</span> '
            f'<span style="color:{color}">{level:7s}</span> '
            f'<span style="color:{TEXT}">{message}</span>'
        )
        # Auto-scroll to bottom
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _apply_filter(self):
        """Re-render log with current filter settings."""
        self._log_view.clear()
        for ts, level, message in self._entries:
            if self._filters.get(level, self._filters.get("INFO")).isChecked():
                self._append_formatted(ts, level, message)

    def _clear(self):
        self._entries.clear()
        self._log_view.clear()
        self._count_label.setText("0 entries")
