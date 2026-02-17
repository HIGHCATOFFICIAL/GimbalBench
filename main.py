#!/usr/bin/env python3
"""GimbalBench - Entry point.

Requires the sbgc library from the Gimbal project. The library is located
by checking (in order):
  1. SBGC_LIB_PATH environment variable
  2. ./Gimbal  (git submodule inside this repo)
  3. ../Gimbal  (sibling directory)
"""
import sys
import os

# When frozen by PyInstaller, _MEIPASS points to the temp extraction directory
# where bundled data files (including sbgc/) are unpacked.
if getattr(sys, 'frozen', False):
    _HERE = sys._MEIPASS
else:
    _HERE = os.path.dirname(os.path.abspath(__file__))


def _find_sbgc_lib() -> str | None:
    """Locate the Gimbal project directory containing the sbgc package."""
    candidates = [
        os.environ.get("SBGC_LIB_PATH", ""),       # explicit override
        _HERE,                                        # PyInstaller bundle (sbgc/ is at root)
        os.path.join(_HERE, "Gimbal"),                # git submodule
        os.path.join(_HERE, "..", "Gimbal"),           # sibling dir
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
        "If you cloned without submodules, run:\n"
        "    git submodule update --init\n"
        "\n"
        "Or set the SBGC_LIB_PATH environment variable:\n"
        "    export SBGC_LIB_PATH=/path/to/Gimbal\n",
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
