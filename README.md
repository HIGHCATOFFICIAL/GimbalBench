# GimbalBench

A PyQt6 desktop application for validating and testing SimpleBGC gimbal controllers over serial or UDP. Provides real-time telemetry monitoring, manual gimbal control, motor health diagnostics, and an automated test suite for validating gimbal behavior.

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

## Prerequisites

- **Python 3.12+**
- **SimpleBGC gimbal** connected via USB-serial (CH340/CH341) or UDP bridge

## Installation

### 1. Clone the repository

```bash
git clone --recurse-submodules <repo-url> GimbalBench
cd GimbalBench
```

This clones GimbalBench along with the [Gimbal](https://github.com/HIGHCATOFFICIAL/Gimbal) submodule which provides the SimpleBGC protocol library (`sbgc`).

If you already cloned without `--recurse-submodules`, pull the submodule separately:

```bash
git submodule update --init
```

### 2. Install system dependencies (Ubuntu/Debian)

```bash
sudo apt-get install python3 python3-pip libxcb-cursor0
```

`libxcb-cursor0` is required by the Qt6 XCB platform plugin on Linux.

### 3. Install Python dependencies

```bash
pip3 install -r requirements.txt
```

### 4. Serial port permissions

To access the USB-serial adapter without `sudo`, add your user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in for the group change to take effect.

**Note:** On Ubuntu, the `brltty` package can interfere with CH340/CH341 USB-serial adapters. If your serial port disappears shortly after plugging in, remove it:

```bash
sudo apt-get remove brltty
```

## Running

```bash
cd GimbalBench
python3 main.py
```

### Connection

1. Select **Serial** or **UDP** transport in the top connection panel
2. For serial: select the port (typically `/dev/ttyUSB0`), baud rate `115200`, and click **Connect**
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
| `ModuleNotFoundError: No module named 'PyQt6'` | Run `pip3 install -r requirements.txt`. |
| `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"` | Install `libxcb-cursor0`: `sudo apt-get install libxcb-cursor0`. |
| Serial port not found / permission denied | Add user to `dialout` group: `sudo usermod -aG dialout $USER`, then log out/in. |
| Serial port disappears after plugging in | Remove `brltty`: `sudo apt-get remove brltty`. |
| Gimbal connected but no telemetry | Check baud rate is `115200`. Try power-cycling the gimbal. |
| Motors won't turn on | Check the Dashboard diagnostics panel for system errors and follow the suggested fixes. |
