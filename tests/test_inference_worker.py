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


class FakeRedis:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, *args, **kwargs):
        self.jobs.append((args, kwargs))
        return object()


@pytest.mark.asyncio
async def test_worker_persists_wrinkle_response(monkeypatch) -> None:
    analysis = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
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
        def analyze_bytes(self, payload, suffix, *, artifact_sink):
            observed.update(payload=payload, suffix=suffix)
            artifact_sink({"overlay": b"overlay", "mask": b"mask"})
            return SimpleNamespace(
                model_dump=lambda **_kwargs: {
                    "analysis_id": str(uuid4()),
                    "status": "abstained",
                }
            )

    monkeypatch.setattr(inference_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(inference_worker, "get_bytes", lambda _key: b"image")
    stored = []
    removed = []
    monkeypatch.setattr(
        inference_worker, "put_bytes", lambda *args: stored.append(args)
    )
    monkeypatch.setattr(
        inference_worker, "remove_objects", lambda keys: removed.extend(keys)
    )
    redis = FakeRedis()

    await inference_worker.run_inference(
        {"wrinkle_service": Service(), "redis": redis}, str(analysis.id)
    )

    assert observed == {"payload": b"image", "suffix": ".png"}
    assert analysis.status == AnalysisStatus.completed
    assert analysis.result["analysis_id"] == str(analysis.id)
    assert analysis.result["status"] == "abstained"
    assert analysis.result["artifacts_expires_at"]
    assert len(stored) == 2
    assert removed == [analysis.object_key]
    assert redis.jobs[0][0][0] == "expire_analysis_artifacts"
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
        user_id=uuid4(),
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
        def analyze_bytes(self, _payload, _suffix, *, artifact_sink):
            raise QualityGateError(QualityAssessment(False, ("no_face_detected",), {}))

    monkeypatch.setattr(inference_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(inference_worker, "get_bytes", lambda _key: b"image")
    removed = []
    monkeypatch.setattr(
        inference_worker, "remove_objects", lambda keys: removed.extend(keys)
    )

    await inference_worker.run_inference({"wrinkle_service": Service()}, str(analysis.id))

    assert analysis.status == AnalysisStatus.rejected
    assert analysis.error_category == "image_quality"
    assert analysis.quality_flags == ["no_face_detected"]
    assert analysis.result == {
        "status": "rejected",
        "quality_flags": ["no_face_detected"],
    }
    assert removed == [analysis.object_key]


@pytest.mark.asyncio
async def test_expiry_job_removes_both_private_artifacts(monkeypatch) -> None:
    user_id, analysis_id = uuid4(), uuid4()
    removed = []
    monkeypatch.setattr(inference_worker, "remove_objects", lambda keys: removed.extend(keys))

    await inference_worker.expire_analysis_artifacts({}, str(user_id), str(analysis_id))

    assert removed == [
        f"users/{user_id}/derived/{analysis_id}/overlay.png",
        f"users/{user_id}/derived/{analysis_id}/mask.png",
    ]
