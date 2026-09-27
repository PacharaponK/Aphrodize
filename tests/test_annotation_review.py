from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.core.config import settings
from backend.services import annotation_service as review


@pytest.mark.asyncio
async def test_consented_image_is_staged_once_for_review(monkeypatch) -> None:
    monkeypatch.setattr(settings, "label_studio_project_id", 7)
    monkeypatch.setattr(settings, "label_studio_api_key", "test-token")
    monkeypatch.setattr(review, "has_annotation_consent", lambda *_: async_true())
    stored = []
    monkeypatch.setattr(review, "put_bytes", lambda *args: stored.append(args))

    class Session:
        def add(self, row):
            self.row = row

        async def commit(self):
            self.row.id = uuid4()

    class Redis:
        def __init__(self):
            self.jobs = []

        async def enqueue_job(self, *args, **kwargs):
            self.jobs.append((args, kwargs))

    analysis = SimpleNamespace(id=uuid4(), user_id=uuid4())
    session, redis = Session(), Redis()
    await review.stage_annotation(session, analysis, b"aligned", redis)

    assert session.row.analysis_id == analysis.id
    assert session.row.expires_at > datetime.now(UTC) + timedelta(days=29)
    assert stored == [
        (
            f"users/{analysis.user_id}/annotation/{analysis.id}/aligned_face.png",
            b"aligned",
            "image/png",
            settings.annotation_bucket,
        )
    ]
    assert [job[0][0] for job in redis.jobs] == [
        "publish_annotation_task",
        "expire_annotation_task",
    ]


async def async_true() -> bool:
    return True


@pytest.mark.asyncio
async def test_publish_reuses_existing_label_studio_task(monkeypatch) -> None:
    monkeypatch.setattr(settings, "label_studio_project_id", 7)
    monkeypatch.setattr(review, "has_annotation_consent", lambda *_: async_true())

    class Tasks:
        def list(self, **_kwargs):
            return [SimpleNamespace(id=42, data={"analysis_id": str(row.analysis_id)})]

        def create(self, **_kwargs):
            raise AssertionError("duplicate task")

    class Session:
        async def commit(self):
            self.commits += 1

        commits = 0

    row = SimpleNamespace(
        analysis_id=uuid4(),
        user_id=uuid4(),
        label_studio_task_id=None,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    monkeypatch.setattr(review, "get_label_studio_client", lambda: SimpleNamespace(tasks=Tasks()))
    session = Session()
    await review.publish_annotation(session, row)
    await review.publish_annotation(session, row)
    assert row.label_studio_task_id == 42
    assert session.commits == 1


def test_publish_embeds_staged_image_without_s3_storage(monkeypatch) -> None:
    monkeypatch.setattr(settings, "label_studio_project_id", 7)
    monkeypatch.setattr(review, "get_bytes", lambda *args: b"png")

    class Tasks:
        def list(self, **_kwargs):
            return []

        def create(self, **kwargs):
            self.data = kwargs["data"]
            return SimpleNamespace(id=42)

    tasks = Tasks()
    monkeypatch.setattr(review, "get_label_studio_client", lambda: SimpleNamespace(tasks=tasks))
    row = SimpleNamespace(analysis_id=uuid4(), object_key="review/image.png")
    assert review._publish(row) == 42
    assert tasks.data == {
        "image": "data:image/png;base64,cG5n",
        "analysis_id": str(row.analysis_id),
    }


@pytest.mark.asyncio
async def test_delete_removes_private_image_and_review_task(monkeypatch) -> None:
    removed = []
    deleted = []
    monkeypatch.setattr(review, "remove_objects", lambda *args: removed.append(args))
    monkeypatch.setattr(
        review,
        "get_label_studio_client",
        lambda: SimpleNamespace(tasks=SimpleNamespace(delete=lambda **args: deleted.append(args))),
    )

    class Session:
        async def delete(self, item):
            self.deleted = item

        async def commit(self):
            self.committed = True

    row = SimpleNamespace(object_key="review/image.png", label_studio_task_id=42)
    session = Session()
    await review.delete_annotation(session, row)
    assert removed == [([row.object_key], settings.annotation_bucket)]
    assert deleted == [{"id": "42"}]
    assert session.deleted is row and session.committed
