# GimbalBench

A PyQt6 desktop application for validating and testing SimpleBGC gimbal controllers over serial or UDP. Provides real-time telemetry monitoring, manual gimbal control, motor health diagnostics, and an automated test suite for validating gimbal behavior.

Works on **Linux**, **Windows**, and **macOS**.

## Features

- **Dashboard** — Live telemetry display (IMU angles, motor power, battery voltage), motor ON/OFF status with flicker detection, system error diagnostics with fix suggestions, motor toggle control
- **Control** — Manual gimbal control via sliders and angle inputs, set rates, home/center commands
- **Motor Health** — Per-axis motor power and balance error monitoring
- **Test Suite** — Automated gimbal validation with 4 test categories:
  - **Motor Startup** (wizard-guided) — Verifies motors start from various physical orientations
  - **Home/Center Recovery** — Sends extreme angles then commands home, verifies return
  - **Axis Range Sweep** — Steps through pitch/yaw range, verifies each target is reached
  - **Hold Stability** — Commands a position and measures deviation over time
- **Log** — Full application log with level filtering, test run logs persisted to disk with CSV export

## Quick Start (Executable)

If you have a pre-built executable, no installation is needed — just run it:

- **Windows**: Double-click `GimbalBench.exe`
- **Linux**: `./GimbalBench`
- **macOS**: `./GimbalBench`

To build the executable yourself, see [Building an Executable](#building-an-executable) below.

## Installation (from source)

### Prerequisites

- **Python 3.12+**
- **Git**
- **SimpleBGC gimbal** connected via USB-serial (CH340/CH341) or UDP bridge

### 1. Clone the repository

```bash
git clone --recurse-submodules https://github.com/HIGHCATOFFICIAL/GimbalBench.git
cd GimbalBench
```

This clones GimbalBench along with the [Gimbal](https://github.com/HIGHCATOFFICIAL/Gimbal) submodule which provides the SimpleBGC protocol library (`sbgc`).

If you already cloned without `--recurse-submodules`, pull the submodule separately:

```bash
git submodule update --init
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Platform-specific setup

<details>
<summary><b>Linux (Ubuntu/Debian)</b></summary>

Install the Qt6 platform plugin dependency:

```bash
sudo apt-get install libxcb-cursor0
```

Add your user to the `dialout` group for serial port access:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in for the group change to take effect.

**Note:** On Ubuntu, the `brltty` package can interfere with CH340/CH341 USB-serial adapters. If your serial port disappears shortly after plugging in, remove it:

```bash
sudo apt-get remove brltty
```

</details>

<details>
<summary><b>Windows</b></summary>

Install the CH340/CH341 USB-serial driver if your system doesn't recognize the gimbal automatically:

1. Download the driver from [the manufacturer's site](http://www.wch-ic.com/downloads/CH341SER_EXE.html)
2. Run the installer and restart if prompted
3. The gimbal should appear as a COM port (e.g., `COM3`) in Device Manager under "Ports (COM & LPT)"

No additional permissions are needed on Windows.

</details>

<details>
<summary><b>macOS</b></summary>

Install the CH340/CH341 driver if needed:

```bash
brew install --cask wch-ch34x-usb-serial-driver
```

The gimbal will appear as `/dev/tty.usbserial-*` or `/dev/tty.usbmodem-*`.

</details>

### 4. Run

```bash
python main.py
```

On Linux you may need `python3` instead of `python`.

## Building an Executable

You can build a standalone executable that runs without Python installed:

```bash
pip install pyinstaller
python build.py
```

The executable is created at:
- **Linux/macOS**: `dist/GimbalBench`
- **Windows**: `dist/GimbalBench.exe`

To clean build artifacts and rebuild:

```bash
python build.py --clean
```

The executable is self-contained — it bundles Python, PyQt6, pyserial, and the sbgc library. Just copy it to any machine and run it.

## Usage

### Connection

1. Select **Serial** or **UDP** transport in the top connection panel
2. For serial: select the port (`COM3` on Windows, `/dev/ttyUSB0` on Linux), baud rate `115200`, and click **Connect**
3. For UDP: enter the bridge IP, bridge port, and PC port, then click **Connect**
4. The LED indicator turns green when the gimbal is responding with telemetry

### Running Tests

1. Navigate to the **Test Suite** tab
2. Select which test categories to run (Motor Startup, Recovery, Sweep, Stability)
3. Adjust parameters (speed, tolerance, timeouts) if needed
4. Click **Run All Selected**
5. For Motor Startup tests, follow the on-screen wizard instructions
6. Automatic tests will turn motors on if they are off
7. Results are displayed in a summary table; logs are saved to the `logs/` directory
8. Click **Export CSV** to save results

## Project Structure

```
GimbalBench/
    main.py                          # Entry point
    build.py                         # PyInstaller build script
    requirements.txt                 # Python dependencies
    Gimbal/                          # Git submodule - SimpleBGC protocol library
        sbgc/
    core/
        connection_manager.py        # Serial/UDP connection handling
        telemetry_worker.py          # Background telemetry polling (QThread)
        command_worker.py            # Queued gimbal command execution (QThread)
        health_checker.py            # Motor health analysis
        sbgc_errors.py               # System error code definitions and decoding
        test_models.py               # Test data models (enums, dataclasses)
        test_cases.py                # Test case definitions builder
        test_runner.py               # Test execution engine (QThread)
        test_export.py               # CSV export for test results
    ui/
        main_window.py               # Main application window
        connection_panel.py          # Connection config and status
        styles.py                    # Catppuccin Mocha dark theme
        tabs/
            dashboard_tab.py         # Telemetry dashboard with motor diagnostics
            control_tab.py           # Manual gimbal control
            motor_health_tab.py      # Motor health monitoring
            test_suite_tab.py        # Automated test suite UI
            log_tab.py               # Application log viewer
        widgets/
            angle_gauge.py           # Angle display gauge
            axis_slider.py           # Axis control slider
            labeled_value.py         # Label + value display
            led_indicator.py         # Colored LED status indicator
    logs/                            # Test run logs (created at runtime)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'sbgc'` | Submodule not initialized. Run `git submodule update --init`. |
| `ModuleNotFoundError: No module named 'PyQt6'` | Run `pip install -r requirements.txt`. |
| `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"` | Linux only. Install `libxcb-cursor0`: `sudo apt-get install libxcb-cursor0`. |
| Serial port not found (Linux) | Add user to `dialout` group: `sudo usermod -aG dialout $USER`, then log out/in. |
| Serial port disappears (Linux) | Remove `brltty`: `sudo apt-get remove brltty`. |
| COM port not showing (Windows) | Install the CH340/CH341 driver. Check Device Manager for the port. |
| Gimbal connected but no telemetry | Check baud rate is `115200`. Try power-cycling the gimbal. |
| Motors won't turn on | Check the Dashboard diagnostics panel for system errors and follow the suggested fixes. |
