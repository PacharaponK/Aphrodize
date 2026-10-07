from io import BytesIO
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from backend.api.v1.routes import analyses
from backend.core.db.models import AnalysisStatus
from backend.services import analysis_service


class InferenceAvailabilityTests(IsolatedAsyncioTestCase):
    async def test_live_worker_allows_processing(self):
        redis = SimpleNamespace(exists=AsyncMock(return_value=1), aclose=AsyncMock())
        with patch.object(analysis_service, "get_arq_pool", AsyncMock(return_value=redis)):
            await analysis_service.require_inference_worker()
        redis.aclose.assert_awaited_once()

    async def test_redis_failure_returns_service_unavailable(self):
        redis = SimpleNamespace(
            exists=AsyncMock(side_effect=ConnectionError()), aclose=AsyncMock()
        )
        with patch.object(analysis_service, "get_arq_pool", AsyncMock(return_value=redis)):
            with self.assertRaises(HTTPException) as error:
                await analysis_service.require_inference_worker()
        self.assertEqual(error.exception.status_code, 503)
        redis.aclose.assert_awaited_once()

    async def test_unavailable_worker_rejects_before_storing_valid_photo(self):
        payload = BytesIO()
        Image.new("RGB", (512, 512)).save(payload, format="PNG")
        payload.seek(0)
        image = UploadFile(payload, headers=Headers({"content-type": "image/png"}))
        session = SimpleNamespace(
            scalar=AsyncMock(return_value=object()), add=Mock(),
            commit=AsyncMock(), refresh=AsyncMock(),
        )
        redis = SimpleNamespace(
            exists=AsyncMock(return_value=0), aclose=AsyncMock(),
            close=AsyncMock(), enqueue_job=AsyncMock(),
        )
        with (
            patch.object(analysis_service, "get_arq_pool", AsyncMock(return_value=redis)),
            patch.object(analysis_service, "put_bytes") as store,
        ):
            with self.assertRaises(HTTPException) as error:
                await analysis_service.create_analysis(session, uuid4(), image)
            self.assertEqual(error.exception.status_code, 503)
            store.assert_not_called()

    async def test_queued_job_reports_unavailable_without_changing_saved_status(self):
        item = SimpleNamespace(id=uuid4(), user_id=uuid4(), status=AnalysisStatus.queued)
        session = SimpleNamespace(get=AsyncMock(return_value=item))
        redis = SimpleNamespace(
            exists=AsyncMock(return_value=0), aclose=AsyncMock(),
            close=AsyncMock(), enqueue_job=AsyncMock(),
        )
        with (
            patch.object(analysis_service, "get_arq_pool", AsyncMock(return_value=redis)),
            patch.object(analyses, "serialize", return_value="queued-result"),
        ):
            with self.assertRaises(HTTPException) as error:
                await analyses.get_analysis(item.id, item.user_id, session)
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(item.status, AnalysisStatus.queued)

    async def test_completed_result_remains_readable_without_worker(self):
        item = SimpleNamespace(id=uuid4(), user_id=uuid4(), status=AnalysisStatus.completed)
        session = SimpleNamespace(get=AsyncMock(return_value=item))
        with patch.object(analyses, "serialize", return_value="saved-result"):
            self.assertEqual(
                await analyses.get_analysis(item.id, item.user_id, session), "saved-result"
            )

    async def test_worker_health_checked_only_after_ownership(self):
        item = SimpleNamespace(id=uuid4(), user_id=uuid4(), status=AnalysisStatus.queued)
        session = SimpleNamespace(get=AsyncMock(return_value=item))
        with self.assertRaises(HTTPException) as error:
            await analyses.get_analysis(item.id, uuid4(), session)
        self.assertEqual(error.exception.status_code, 404)
