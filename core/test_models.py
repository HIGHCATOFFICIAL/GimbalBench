"""Data models for the gimbal validation test suite."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TestStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_USER = "WAITING_USER"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    ABORTED = "ABORTED"


class TestCategory(Enum):
    MOTOR_STARTUP = "Motor Startup"
    RECOVERY = "Recovery"
    SWEEP = "Axis Sweep"
    STABILITY = "Hold Stability"


@dataclass
class TelemetrySample:
    timestamp: float
    imu_angles: tuple[float, float, float]  # roll, pitch, yaw degrees
    motor_power: tuple[int, int, int]
    system_error: int
    balance_error: tuple[int, int, int]


@dataclass
class TestCaseResult:
    name: str
    category: TestCategory
    status: TestStatus = TestStatus.PENDING
    duration_s: float = 0.0
    message: str = ""
    samples: list[TelemetrySample] = field(default_factory=list)
    max_error_deg: float = 0.0
    mean_error_deg: float = 0.0


@dataclass
class TestSuiteConfig:
    speed_dps: float = 20.0
    angle_tolerance_deg: float = 3.0
    hold_tolerance_deg: float = 2.0
    move_timeout_s: float = 10.0
    startup_timeout_s: float = 20.0
    hold_duration_s: float = 5.0
    test_pitch: bool = True
    test_yaw: bool = True
    sweep_step_deg: float = 45.0
