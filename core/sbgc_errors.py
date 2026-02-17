"""SBGC system_error / system_sub_error mappings from the SimpleBGC protocol.

system_error is a bitmask — multiple errors can be active simultaneously.
system_sub_error is a single code indicating the most recent sub-error.
"""

# system_error bit flags  →  (short_name, description, fix)
SYSTEM_ERRORS: dict[int, tuple[str, str, str]] = {
    0x0001: (
        "No sensor",
        "IMU sensor is not connected or not detected.",
        "Turn off power and check the I2C sensor cable. "
        "NEVER connect the sensor while the board is powered.",
    ),
    0x0002: (
        "Accel not calibrated",
        "The accelerometer has not been calibrated.",
        "Level the sensor horizontally and run accelerometer calibration "
        "(CALIB_ACC) from the SimpleBGC GUI.",
    ),
    0x0004: (
        "Power not set",
        "Motor power parameter is zero or too low.",
        "Increase POWER from a low value (e.g. 50) in the SimpleBGC GUI "
        "until the motor holds position without overheating.",
    ),
    0x0008: (
        "Poles not set",
        "Motor pole count has not been calibrated.",
        "Run AUTO calibration in the SimpleBGC GUI to detect pole count "
        "and direction. Verify it equals the number of magnets in the motor.",
    ),
    0x0010: (
        "License invalid",
        "Firmware cannot run on this board.",
        "Upload proper firmware for your board, or contact your supplier.",
    ),
    0x0020: (
        "Serial data corrupted",
        "Communication data is corrupted.",
        "Re-connect the board. Ensure the correct serial port is selected "
        "and firmware/GUI versions are compatible.",
    ),
    0x0040: (
        "Low battery",
        "Battery voltage is low.",
        "Charge or replace the battery soon.",
    ),
    0x0080: (
        "CRITICAL battery",
        "Battery voltage is critically low.",
        "IMMEDIATELY turn off the system and charge the battery!",
    ),
    0x0100: (
        "GUI version mismatch",
        "GUI and firmware versions are incompatible.",
        "Use a GUI version that matches your firmware version.",
    ),
    0x0200: (
        "Motor missing steps",
        "A motor is skipping steps — likely mechanical overload or obstruction.",
        "Check for mechanical obstructions, reduce payload weight, "
        "or increase motor power. Inspect motor/belt for damage.",
    ),
    0x0400: (
        "Internal system error",
        "Code assertion failed, critical resource exhausted, or hardware fault.",
        "Power cycle the gimbal. If the error persists, update firmware "
        "or contact support.",
    ),
    0x0800: (
        "Emergency stop",
        "A serious fault condition triggered an emergency stop.",
        "Press a menu button or power cycle to restart. "
        "Investigate what caused the fault before resuming operation.",
    ),
    0x1000: (
        "Motor over-temperature",
        "Motor temperature warning — risk of permanent damage.",
        "Turn off the system and let motors cool down! "
        "Reduce continuous load or improve ventilation.",
    ),
    0x2000: (
        "Motor driver error",
        "The motor driver reported a fault.",
        "Check wiring and motor connections. Power cycle the system. "
        "If persistent, the driver IC may be damaged.",
    ),
}

# system_sub_error codes  →  (short_name, description, fix)
SUB_ERRORS: dict[int, tuple[str, str, str]] = {
    1: (
        "Sensor error",
        "IMU sensor communication failed.",
        "Check sensor cable and connections.",
    ),
    2: (
        "Driver over-temperature",
        "Motor driver is overheated.",
        "Let the system cool down and reduce load.",
    ),
    3: (
        "Driver fault",
        "Under-voltage, over-current, or short circuit detected.",
        "Remove the cause of the problem and power cycle.",
    ),
    13: (
        "Motor over-temp cutoff",
        "Motors were cut off due to excessive load over time.",
        "Check heating-cooling model parameters in settings. Reduce load.",
    ),
    14: (
        "Motor locked",
        "Motor is locked and cannot finish an automated task.",
        "Remove obstacles and restart the system.",
    ),
    25: (
        "Avg current exceeded",
        "Motor average current exceeds the configured limit.",
        "Check driver/motor health or adjust the average current limit.",
    ),
    26: (
        "Driver unknown error",
        "Motor driver reported an unrecognized error.",
        "Update firmware to the latest version.",
    ),
    44: (
        "Motors OFF during calibration",
        "Calibration requires motors to be ON.",
        "Turn motors ON before running calibration.",
    ),
}


def decode_system_errors(system_error: int) -> list[tuple[int, str, str, str]]:
    """Decode system_error bitmask into list of (bit, name, description, fix)."""
    active = []
    for bit, (name, desc, fix) in SYSTEM_ERRORS.items():
        if system_error & bit:
            active.append((bit, name, desc, fix))
    return active


def decode_sub_error(sub_error: int) -> tuple[str, str, str] | None:
    """Decode a single sub_error code. Returns (name, description, fix) or None."""
    return SUB_ERRORS.get(sub_error)


def format_error_summary(system_error: int, sub_error: int) -> str:
    """Return a short one-line summary of active errors."""
    if system_error == 0 and sub_error == 0:
        return "No errors"
    parts = []
    for bit, (name, _, _) in SYSTEM_ERRORS.items():
        if system_error & bit:
            parts.append(name)
    if sub_error != 0:
        sub = SUB_ERRORS.get(sub_error)
        if sub:
            parts.append(f"Sub: {sub[0]}")
        else:
            parts.append(f"Sub error #{sub_error}")
    return " | ".join(parts) if parts else "Unknown error"
