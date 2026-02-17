"""Catppuccin Mocha-inspired dark theme for GimbalBench."""

# -- Catppuccin Mocha palette --
BASE = "#1e1e2e"
MANTLE = "#181825"
CRUST = "#11111b"
SURFACE0 = "#313244"
SURFACE1 = "#45475a"
SURFACE2 = "#585b70"
OVERLAY0 = "#6c7086"
TEXT = "#cdd6f4"
SUBTEXT0 = "#a6adc8"
SUBTEXT1 = "#bac2de"
RED = "#f38ba8"
GREEN = "#a6e3a1"
YELLOW = "#f9e2af"
BLUE = "#89b4fa"
MAUVE = "#cba6f7"
TEAL = "#94e2d5"
PEACH = "#fab387"
SKY = "#89dceb"

# Semantic aliases
COLOR_OK = GREEN
COLOR_WARN = YELLOW
COLOR_FAIL = RED
COLOR_INACTIVE = OVERLAY0
COLOR_ACCENT = BLUE

DARK_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BASE};
    color: {TEXT};
    font-family: "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    background-color: {BASE};
}}

QTabBar::tab {{
    background-color: {SURFACE0};
    color: {SUBTEXT0};
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {SURFACE1};
    color: {TEXT};
    border-bottom: 2px solid {BLUE};
}}

QTabBar::tab:hover {{
    background-color: {SURFACE1};
}}

QGroupBox {{
    border: 1px solid {SURFACE1};
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: {SUBTEXT1};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}

QPushButton {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 6px 16px;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {SURFACE1};
    border-color: {BLUE};
}}

QPushButton:pressed {{
    background-color: {SURFACE2};
}}

QPushButton:disabled {{
    color: {OVERLAY0};
    background-color: {MANTLE};
}}

QPushButton#connectBtn {{
    background-color: {SURFACE0};
    border-color: {GREEN};
    color: {GREEN};
}}

QPushButton#connectBtn:hover {{
    background-color: {SURFACE1};
}}

QPushButton#disconnectBtn {{
    background-color: {SURFACE0};
    border-color: {RED};
    color: {RED};
}}

QPushButton#disconnectBtn:hover {{
    background-color: {SURFACE1};
}}

QComboBox {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {BLUE};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE0};
    color: {TEXT};
    selection-background-color: {SURFACE1};
    border: 1px solid {SURFACE1};
}}

QLineEdit {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}}

QLineEdit:focus {{
    border-color: {BLUE};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 4px 8px;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {SURFACE1};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {BLUE};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QSlider::groove:vertical {{
    width: 6px;
    background: {SURFACE1};
    border-radius: 3px;
}}

QSlider::handle:vertical {{
    background: {BLUE};
    width: 16px;
    height: 16px;
    margin: 0 -5px;
    border-radius: 8px;
}}

QProgressBar {{
    background-color: {SURFACE0};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    text-align: center;
    color: {TEXT};
    min-height: 18px;
}}

QProgressBar::chunk {{
    background-color: {BLUE};
    border-radius: 3px;
}}

QTextEdit {{
    background-color: {MANTLE};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
}}

QTableWidget {{
    background-color: {MANTLE};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    gridline-color: {SURFACE0};
    alternate-background-color: {CRUST};
}}

QTableWidget::item:selected {{
    background-color: {SURFACE1};
}}

QHeaderView::section {{
    background-color: {SURFACE0};
    color: {SUBTEXT1};
    border: 1px solid {SURFACE1};
    padding: 4px 8px;
    font-weight: bold;
}}

QScrollBar:vertical {{
    background: {MANTLE};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {SURFACE1};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {MANTLE};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {SURFACE1};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QRadioButton, QCheckBox {{
    color: {TEXT};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {SURFACE2};
    border-radius: 3px;
    background-color: {SURFACE0};
}}

QCheckBox::indicator:hover {{
    border-color: {BLUE};
}}

QCheckBox::indicator:checked {{
    background-color: {BLUE};
    border-color: {BLUE};
    image: none;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {SURFACE2};
    border-radius: 10px;
    background-color: {SURFACE0};
}}

QRadioButton::indicator:hover {{
    border-color: {BLUE};
}}

QRadioButton::indicator:checked {{
    background-color: {BLUE};
    border-color: {BLUE};
}}

QLabel {{
    color: {TEXT};
}}

QStatusBar {{
    background-color: {MANTLE};
    color: {SUBTEXT0};
    border-top: 1px solid {SURFACE0};
}}

QToolTip {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    padding: 4px;
}}
"""
