"""Test case definitions for the gimbal validation suite."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.test_models import TestCategory, TestSuiteConfig


@dataclass
class TestCaseDefinition:
    name: str
    category: TestCategory
    instruction: str = ""          # wizard instruction for user (motor startup tests)
    params: dict[str, Any] = field(default_factory=dict)


def build_motor_startup_tests() -> list[TestCaseDefinition]:
    return [
        TestCaseDefinition(
            name="Normal startup",
            category=TestCategory.MOTOR_STARTUP,
            instruction="Power cycle the gimbal in its normal upright orientation.\n"
                        "Press 'Ready' once the gimbal has been power-cycled.",
        ),
        TestCaseDefinition(
            name="Inverted startup",
            category=TestCategory.MOTOR_STARTUP,
            instruction="Hold the gimbal upside-down, then power cycle it.\n"
                        "Press 'Ready' once the gimbal has been power-cycled.",
        ),
        TestCaseDefinition(
            name="90\u00b0 pitch-down startup",
            category=TestCategory.MOTOR_STARTUP,
            instruction="Hold the gimbal pitched 90\u00b0 downward, then power cycle.\n"
                        "Press 'Ready' once the gimbal has been power-cycled.",
        ),
        TestCaseDefinition(
            name="90\u00b0 roll startup",
            category=TestCategory.MOTOR_STARTUP,
            instruction="Hold the gimbal rolled 90\u00b0 sideways, then power cycle.\n"
                        "Press 'Ready' once the gimbal has been power-cycled.",
        ),
        TestCaseDefinition(
            name="Random orientation startup",
            category=TestCategory.MOTOR_STARTUP,
            instruction="Hold the gimbal at any unusual angle, then power cycle.\n"
                        "Press 'Ready' once the gimbal has been power-cycled.",
        ),
    ]


def build_recovery_tests(cfg: TestSuiteConfig) -> list[TestCaseDefinition]:
    tests: list[TestCaseDefinition] = []

    if cfg.test_pitch:
        tests.append(TestCaseDefinition(
            name="Home from pitch -90\u00b0",
            category=TestCategory.RECOVERY,
            params={"action": "home_from_angle", "pitch_deg": -90.0},
        ))
        tests.append(TestCaseDefinition(
            name="Home from pitch +45\u00b0",
            category=TestCategory.RECOVERY,
            params={"action": "home_from_angle", "pitch_deg": 45.0},
        ))

    if cfg.test_yaw:
        tests.append(TestCaseDefinition(
            name="Center yaw from -90\u00b0",
            category=TestCategory.RECOVERY,
            params={"action": "center_yaw_from", "yaw_deg": -90.0},
        ))
        tests.append(TestCaseDefinition(
            name="Center yaw from +90\u00b0",
            category=TestCategory.RECOVERY,
            params={"action": "center_yaw_from", "yaw_deg": 90.0},
        ))

    if cfg.test_yaw:
        tests.append(TestCaseDefinition(
            name="Home after rate spin",
            category=TestCategory.RECOVERY,
            params={"action": "home_after_rate", "yaw_dps": 15.0, "spin_duration_s": 3.0},
        ))

    return tests


def build_sweep_tests(cfg: TestSuiteConfig) -> list[TestCaseDefinition]:
    tests: list[TestCaseDefinition] = []
    step = cfg.sweep_step_deg

    if cfg.test_pitch:
        # Pitch: 0 -> -45 -> -90 -> -45 -> 0
        angles: list[float] = [0.0]
        a = 0.0
        while a > -90.0:
            a = max(a - step, -90.0)
            angles.append(a)
        while a < 0.0:
            a = min(a + step, 0.0)
            angles.append(a)
        tests.append(TestCaseDefinition(
            name="Pitch full sweep",
            category=TestCategory.SWEEP,
            params={"axis": "pitch", "angles": angles},
        ))

    if cfg.test_yaw:
        # Yaw: 0 -> -45 -> -90 -> -45 -> 0 -> 45 -> 90 -> 45 -> 0
        angles = [0.0]
        a = 0.0
        while a > -90.0:
            a = max(a - step, -90.0)
            angles.append(a)
        while a < 90.0:
            a = min(a + step, 90.0)
            angles.append(a)
        while a > 0.0:
            a = max(a - step, 0.0)
            angles.append(a)
        tests.append(TestCaseDefinition(
            name="Yaw full sweep",
            category=TestCategory.SWEEP,
            params={"axis": "yaw", "angles": angles},
        ))

    if cfg.test_pitch and cfg.test_yaw:
        tests.append(TestCaseDefinition(
            name="Combined sweep",
            category=TestCategory.SWEEP,
            params={"axis": "combined"},
        ))

    return tests


def build_stability_tests(cfg: TestSuiteConfig) -> list[TestCaseDefinition]:
    tests: list[TestCaseDefinition] = []

    tests.append(TestCaseDefinition(
        name="Hold home (0\u00b0, 0\u00b0)",
        category=TestCategory.STABILITY,
        params={"pitch_deg": 0.0, "yaw_deg": 0.0},
    ))

    if cfg.test_pitch:
        tests.append(TestCaseDefinition(
            name="Hold pitch -45\u00b0",
            category=TestCategory.STABILITY,
            params={"pitch_deg": -45.0, "yaw_deg": None},
        ))
        tests.append(TestCaseDefinition(
            name="Hold pitch -90\u00b0",
            category=TestCategory.STABILITY,
            params={"pitch_deg": -90.0, "yaw_deg": None},
        ))

    if cfg.test_yaw:
        tests.append(TestCaseDefinition(
            name="Hold yaw 45\u00b0",
            category=TestCategory.STABILITY,
            params={"pitch_deg": 0.0, "yaw_deg": 45.0},
        ))

    return tests


def build_test_suite(
    cfg: TestSuiteConfig,
    *,
    motor_startup: bool = True,
    recovery: bool = True,
    sweep: bool = True,
    stability: bool = True,
) -> list[TestCaseDefinition]:
    tests: list[TestCaseDefinition] = []
    if motor_startup:
        tests.extend(build_motor_startup_tests())
    if recovery:
        tests.extend(build_recovery_tests(cfg))
    if sweep:
        tests.extend(build_sweep_tests(cfg))
    if stability:
        tests.extend(build_stability_tests(cfg))
    return tests
