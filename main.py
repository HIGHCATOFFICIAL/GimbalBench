#!/usr/bin/env python3
"""GimbalBench - Entry point.

Requires the sbgc library from the Gimbal project. The library is located
by checking (in order):
  1. SBGC_LIB_PATH environment variable
  2. ../Gimbal  (sibling directory)
  3. /home/ubuntu/Desktop/Gimbal  (legacy default)
"""
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_sbgc_lib() -> str | None:
    """Locate the Gimbal project directory containing the sbgc package."""
    candidates = [
        os.environ.get("SBGC_LIB_PATH", ""),       # explicit override
        os.path.join(_HERE, "..", "Gimbal"),          # sibling dir
        "/home/ubuntu/Desktop/Gimbal",                # legacy default
    ]
    for path in candidates:
        if path and os.path.isdir(os.path.join(path, "sbgc")):
            return os.path.abspath(path)
    return None


sbgc_path = _find_sbgc_lib()
if sbgc_path is None:
    print(
        "ERROR: Could not find the sbgc library.\n"
        "The Gimbal project (containing the 'sbgc' package) is required.\n"
        "\n"
        "Options:\n"
        "  1. Place the Gimbal project next to this tool:\n"
        "       parent_dir/\n"
        "         Gimbal/sbgc/\n"
        "         GimbalBench/main.py\n"
        "  2. Set the SBGC_LIB_PATH environment variable:\n"
        "       export SBGC_LIB_PATH=/path/to/Gimbal\n",
        file=sys.stderr,
    )
    sys.exit(1)

sys.path.insert(0, sbgc_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GimbalBench")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
