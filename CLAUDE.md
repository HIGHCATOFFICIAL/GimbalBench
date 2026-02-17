# CLAUDE.md - GimbalBench

## What is this project?

GimbalBench is a PyQt6 desktop application for validating and testing SimpleBGC gimbal controllers. It communicates with gimbals over serial (CH340/CH341 USB adapters) or UDP, providing real-time telemetry, manual control, and automated test suites.

## Quick start

```bash
git submodule update --init   # pull the Gimbal/sbgc library
pip3 install -r requirements.txt
python3 main.py
```

Verify the app launches: `timeout 5 python3 main.py` should exit cleanly with no errors.

## Project layout

```
GimbalBench/
    main.py               # Entry point - finds sbgc lib, launches QApplication
    Gimbal/               # Git submodule (https://github.com/HIGHCATOFFICIAL/Gimbal)
        sbgc/             # SimpleBGC protocol library (serial transport, commands, parsing)
    core/                 # Backend: connection, telemetry, commands, test engine
    ui/                   # Frontend: PyQt6 widgets, tabs, styles
        tabs/             # One file per tab (dashboard, control, motor_health, test_suite, log)
        widgets/          # Reusable widgets (LED indicator, angle gauge, sliders, etc.)
```

## Architecture

### Threading model

All cross-thread communication uses **PyQt6 signals/slots**. There are 3 QThread workers:

- **TelemetryWorker** (`core/telemetry_worker.py`) — polls `CMD_REALTIME_DATA_4` at ~10Hz, emits `data_received(object)` with parsed `RealtimeData4InCmd`
- **CommandWorker** (`core/command_worker.py`) — processes a queue of gimbal commands off the GUI thread. Use `submit(name, func, *args)` where `func(client, *args)` is called
- **TestRunner** (`core/test_runner.py`) — runs the test suite as a QThread. Does NOT do its own serial I/O

### Telemetry bridging pattern

TestRunner receives telemetry indirectly. MainWindow forwards TelemetryWorker's `data_received` signal:

```
TelemetryWorker → MainWindow._on_telemetry() → test_tab.on_telemetry(data) → runner.on_telemetry(data)
```

TestRunner stores the latest data behind `_telem_lock` (threading.Lock) and reads it from its own thread when needed. **Never** add direct serial reads to TestRunner.

### ConnectionManager

`core/connection_manager.py` owns the `SbgcClient` instance. Access via `connection_manager.client` and `connection_manager.is_connected`. Connection/probe runs in a background thread to avoid freezing the GUI.

## SBGC library (Gimbal submodule)

Key classes and functions used throughout the codebase:

- `SbgcClient` (`Gimbal/sbgc/client.py`) — main API: `set_angles()`, `home()`, `center_yaw()`, `set_rates()`, `motors_on()`, `motors_off()`, `release_control()`
- `encode(cmd_id, payload=b"")` — builds an SBGC v1 packet (start byte `0x3E`, checksums)
- `parse_realtime_data_4_cmd(payload)` — returns `RealtimeData4InCmd` NamedTuple
- `to_degree(raw)` — converts SBGC raw angle units to degrees

### Critical SBGC patterns

- **Lock discipline**: `SbgcClient._io_lock` is acquired internally by `_wait_for()`. Do NOT wrap `_t.write()` in `_io_lock` before calling `_wait_for()` — this causes deadlock.
- **Fetch pattern**: write outside the lock, then call `_wait_for()` which acquires the lock to pump RX and find the response.
- **Cached state**: call `client._set_last_state()` after parsing telemetry so that `set_rates()` and other methods that need current angles will work.
- **QThread lifecycle**: QThread cannot be restarted after `run()` finishes. Recreate the worker on each connect.

## UI conventions

- **Dark theme**: Catppuccin Mocha palette defined in `ui/styles.py`. Use the color constants (`BASE`, `SURFACE0`, `TEXT`, `RED`, `GREEN`, `BLUE`, etc.) and semantic aliases (`COLOR_OK`, `COLOR_WARN`, `COLOR_FAIL`).
- **LED indicators**: `ui/widgets/led_indicator.py` — use `set_color("green" | "red" | "yellow" | "gray")`.
- **Tab pattern**: each tab is a QWidget in `ui/tabs/`. Constructor receives `connection_manager` and/or `command_worker` as needed. Telemetry arrives via an `update_telemetry(data)` or `on_telemetry(data)` method called from MainWindow.

## Test suite

### Test categories

1. **Motor Startup** (wizard) — user physically positions gimbal, presses Ready, tool verifies motors start
2. **Recovery** (automatic) — sends extreme angles, commands home/center, verifies return
3. **Axis Sweep** (automatic) — steps through angle sequences, verifies each target reached
4. **Hold Stability** (automatic) — holds a position, measures deviation over time

### Wizard synchronization

Motor Startup tests use `threading.Event` (`_user_event`). The runner thread blocks on `_user_event.wait()`. The UI calls `runner.user_continue()` or `runner.user_skip()` to unblock.

### Motor state awareness

Automatic tests (Recovery, Sweep, Stability) call `_ensure_motors_on()` before running. This checks telemetry for `motor_power > 0`, sends `motors_on()` if needed, and waits for confirmation. Motor Startup tests do NOT do this — they test cold-start behavior.

### Test results

- `TestCaseResult` dataclass in `core/test_models.py` — holds status, duration, message, telemetry samples, deviation stats
- Test logs are persisted to `logs/test_run_YYYYMMDD_HHMMSS.log`
- CSV export via `core/test_export.py`

## Common tasks

### Adding a new test case

1. Define it in `core/test_cases.py` — add to the appropriate `build_*_tests()` function
2. If it needs a new action type, add handling in the corresponding `_run_*_test()` method in `core/test_runner.py`

### Adding a new SBGC command

1. Add the method to `Gimbal/sbgc/client.py` following existing patterns (write + `_wait_for`)
2. Import the command ID from `Gimbal/sbgc/ids.py`
3. Commit in the Gimbal submodule, then update the submodule pointer in GimbalBench

### Adding a new tab

1. Create `ui/tabs/my_tab.py` with a QWidget subclass
2. Add it in `ui/main_window.py` — instantiate and `addTab()`
3. If it needs telemetry, add a forwarding call in `MainWindow._on_telemetry()`

## System dependencies (Ubuntu/Debian)

```bash
sudo apt-get install python3 python3-pip libxcb-cursor0
```

`libxcb-cursor0` is required for the Qt6 XCB platform plugin. Without it the app won't launch on Linux.

## Serial port notes

- Default port: `/dev/ttyUSB0`, baud 115200, 8N1, no flow control
- User must be in the `dialout` group: `sudo usermod -aG dialout $USER`
- The `brltty` package conflicts with CH340/CH341 adapters — remove it if the port disappears after plugging in
