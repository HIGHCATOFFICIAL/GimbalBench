"""Motor health threshold analysis."""
from dataclasses import dataclass, field
from sbgc.commands.realtime import RealtimeData4InCmd


@dataclass
class AxisHealth:
    name: str
    motor_power: int = 0
    balance_error: int = 0
    stator_rotor_angle: int = 0
    motor_out: int = 0
    power_status: str = "OK"      # OK / WARN / FAIL
    balance_status: str = "OK"


@dataclass
class SystemHealth:
    system_error: int = 0
    system_sub_error: int = 0
    i2c_errors: int = 0
    serial_errors: int = 0
    cycle_time: int = 0
    battery: int = 0
    imu_temperature: int = 0
    system_status: str = "OK"     # OK / WARN / FAIL
    i2c_status: str = "OK"
    cycle_status: str = "OK"
    battery_status: str = "OK"
    temp_status: str = "OK"


@dataclass
class HealthReport:
    axes: list[AxisHealth] = field(default_factory=list)
    system: SystemHealth = field(default_factory=SystemHealth)
    overall: str = "OK"  # PASS / WARNING / FAIL


# Thresholds
MOTOR_POWER_WARN = 180
MOTOR_POWER_CRIT = 230
BALANCE_ERROR_WARN = 20
BALANCE_ERROR_CRIT = 50
I2C_ERROR_WARN = 10
CYCLE_TIME_WARN = 15000  # microseconds
BATTERY_WARN = 10
TEMP_WARN = 60
TEMP_CRIT = 75


def analyze_health(data: RealtimeData4InCmd) -> HealthReport:
    """Analyze telemetry data and return a health report."""
    report = HealthReport()
    overall_worst = "PASS"

    # Per-axis analysis
    axis_names = ["Roll", "Pitch", "Yaw"]
    powers = [data.motor_power_1, data.motor_power_2, data.motor_power_3]
    balances = [data.balance_error_1, data.balance_error_2, data.balance_error_3]
    stators = [data.stator_rotor_angle_1, data.stator_rotor_angle_2, data.stator_rotor_angle_3]
    outputs = [data.motor_out_1, data.motor_out_2, data.motor_out_3]

    for i, name in enumerate(axis_names):
        ax = AxisHealth(name=name)
        ax.motor_power = powers[i]
        ax.balance_error = abs(balances[i])
        ax.stator_rotor_angle = stators[i]
        ax.motor_out = outputs[i]

        # Motor power check
        if ax.motor_power >= MOTOR_POWER_CRIT:
            ax.power_status = "FAIL"
            overall_worst = "FAIL"
        elif ax.motor_power >= MOTOR_POWER_WARN:
            ax.power_status = "WARN"
            if overall_worst != "FAIL":
                overall_worst = "WARNING"

        # Balance error check
        if ax.balance_error >= BALANCE_ERROR_CRIT:
            ax.balance_status = "FAIL"
            overall_worst = "FAIL"
        elif ax.balance_error >= BALANCE_ERROR_WARN:
            ax.balance_status = "WARN"
            if overall_worst != "FAIL":
                overall_worst = "WARNING"

        report.axes.append(ax)

    # System checks
    sys = report.system
    sys.system_error = data.system_error
    sys.system_sub_error = data.system_sub_error
    sys.i2c_errors = data.i2c_error_count
    sys.serial_errors = data.serial_err_cnt
    sys.cycle_time = data.cycle_time
    sys.battery = data.bat_level
    sys.imu_temperature = data.imu_temperature

    if data.system_error != 0:
        sys.system_status = "FAIL"
        overall_worst = "FAIL"

    if data.i2c_error_count > I2C_ERROR_WARN:
        sys.i2c_status = "WARN"
        if overall_worst == "PASS":
            overall_worst = "WARNING"

    if data.cycle_time > CYCLE_TIME_WARN:
        sys.cycle_status = "WARN"
        if overall_worst == "PASS":
            overall_worst = "WARNING"

    if 0 < data.bat_level < BATTERY_WARN:
        sys.battery_status = "WARN"
        if overall_worst == "PASS":
            overall_worst = "WARNING"

    if data.imu_temperature >= TEMP_CRIT:
        sys.temp_status = "FAIL"
        overall_worst = "FAIL"
    elif data.imu_temperature >= TEMP_WARN:
        sys.temp_status = "WARN"
        if overall_worst == "PASS":
            overall_worst = "WARNING"

    report.overall = overall_worst
    return report
