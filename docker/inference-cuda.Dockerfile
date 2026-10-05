FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY ai/requirements-inference-cuda.txt /app/ai/requirements-inference-cuda.txt
RUN pip install --no-cache-dir torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118
RUN pip install --no-cache-dir -r ai/requirements-inference-cuda.txt && pip check
COPY backend /app/backend
COPY ai /app/ai
RUN mkdir -p /app/assets && python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task', '/app/assets/face_landmarker.task')"
RUN python -c "from backend.workers.inference_worker import WorkerSettings; from backend.wrinkle.service import WrinkleAnalysisService; print('Worker imports OK')"
CMD ["arq", "backend.workers.inference_worker.WorkerSettings"]
