"""CSV export for gimbal test suite results."""
import csv
from datetime import datetime

from core.test_models import TestCaseResult


def export_results_csv(path: str, results: list[TestCaseResult]) -> None:
    """Write test results to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Test", "Category", "Status", "Duration (s)",
            "Message", "Max Error (deg)", "Mean Error (deg)", "Samples",
        ])
        for r in results:
            writer.writerow([
                r.name,
                r.category.value,
                r.status.value,
                f"{r.duration_s:.2f}",
                r.message,
                f"{r.max_error_deg:.2f}",
                f"{r.mean_error_deg:.2f}",
                len(r.samples),
            ])


def default_filename() -> str:
    return f"gimbal_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
