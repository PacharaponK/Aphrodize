from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.api.v1.routes.monitoring import summarize_analyses
from backend.core.db.models import AnalysisStatus


def test_analysis_health_groups_models_without_user_data() -> None:
    now = datetime.now(UTC)
    rows = [
        SimpleNamespace(
            model_version="sha-a",
            status=AnalysisStatus.completed,
            quality_flags=[],
            created_at=now,
            completed_at=now + timedelta(seconds=3),
        ),
        SimpleNamespace(
            model_version="sha-a",
            status=AnalysisStatus.failed,
            quality_flags=["blur"],
            created_at=now,
            completed_at=now + timedelta(seconds=5),
        ),
    ]
    summary = summarize_analyses(rows)
    assert summary["sample_count"] == 2
    assert summary["models"]["sha-a"] == {
        "status": {"completed": 1, "failed": 1},
        "quality_flags": {"blur": 1},
        "failure_rate": 0.5,
        "p95_seconds": 5.0,
    }
