from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from backend.core import observability as obs


class LegacyWorkerQueueTests(IsolatedAsyncioTestCase):
    async def test_inference_payload_runs_on_undecorated_worker(self):
        calls = []

        async def legacy_worker(ctx, identifier):
            calls.append(identifier)

        class Pool:
            async def enqueue_job(self, function, *args, _queue_name=None, **kwargs):
                self.queue = _queue_name
                await legacy_worker({}, *args, **kwargs)
                return SimpleNamespace(job_id="legacy-job")

        pool = Pool()
        token = obs.request_id.set("b" * 32)
        try:
            await obs.enqueue_job(pool, "run_inference", "analysis-id", _queue_name="inference")
        finally:
            obs.request_id.reset(token)
        self.assertEqual(calls, ["analysis-id"])
        self.assertEqual(pool.queue, "inference")

    async def test_training_queue_retains_correlation(self):
        class Pool:
            async def enqueue_job(self, function, *args, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(job_id="training-job")

        pool = Pool()
        token = obs.request_id.set("c" * 32)
        try:
            await obs.enqueue_job(pool, "run_training", "run-id", _queue_name="training")
        finally:
            obs.request_id.reset(token)
        self.assertEqual(pool.kwargs, {"_queue_name": "training", "_request_id": "c" * 32})
