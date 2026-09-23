from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai.ffhq_wrinkle.quality import QualityAssessment, QualityGateError
from backend.core.db.models import AnalysisStatus
from backend.services.analysis_service import recommendations_for
from backend.workers import inference_worker


class FakeSession:
    def __init__(self, analysis):
        self.analysis = analysis
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, _model, _identifier):
        return self.analysis

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_worker_persists_wrinkle_response(monkeypatch) -> None:
    analysis = SimpleNamespace(
        id=uuid4(),
        status=AnalysisStatus.queued,
        object_key="users/example/original/image",
        content_type="image/png",
        result=None,
        error_category=None,
        completed_at=None,
    )
    session = FakeSession(analysis)
    observed = {}

    class Service:
        def analyze_bytes(self, payload, suffix):
            observed.update(payload=payload, suffix=suffix)
            return SimpleNamespace(
                model_dump=lambda **_kwargs: {
                    "analysis_id": str(uuid4()),
                    "status": "abstained",
                }
            )

    monkeypatch.setattr(inference_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(inference_worker, "get_bytes", lambda _key: b"image")

    await inference_worker.run_inference({"wrinkle_service": Service()}, str(analysis.id))

    assert observed == {"payload": b"image", "suffix": ".png"}
    assert analysis.status == AnalysisStatus.completed
    assert analysis.result == {"analysis_id": str(analysis.id), "status": "abstained"}
    assert analysis.error_category is None
    assert analysis.completed_at is not None
    assert session.commits == 2


def test_recommendations_require_ai_confidence() -> None:
    analysis = SimpleNamespace(
        status=AnalysisStatus.completed,
        image_quality_score=1.0,
        result={"recommendation_gate": {"eligible": False}},
    )

    result = recommendations_for(analysis, {})

    assert result == {
        "recommendations": [],
        "blocked_reason": "AI confidence gate did not pass.",
    }


@pytest.mark.asyncio
async def test_worker_rejects_image_failing_quality_gate(monkeypatch) -> None:
    analysis = SimpleNamespace(
        id=uuid4(),
        status=AnalysisStatus.queued,
        object_key="users/example/original/image",
        content_type="image/png",
        result=None,
        error_category=None,
        quality_flags=[],
        completed_at=None,
    )
    session = FakeSession(analysis)

    class Service:
        def analyze_bytes(self, _payload, _suffix):
            raise QualityGateError(QualityAssessment(False, ("no_face_detected",), {}))

    monkeypatch.setattr(inference_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(inference_worker, "get_bytes", lambda _key: b"image")

    await inference_worker.run_inference({"wrinkle_service": Service()}, str(analysis.id))

    assert analysis.status == AnalysisStatus.rejected
    assert analysis.error_category == "image_quality"
    assert analysis.quality_flags == ["no_face_detected"]
    assert analysis.result == {
        "status": "rejected",
        "quality_flags": ["no_face_detected"],
    }
