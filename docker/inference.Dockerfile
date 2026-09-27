FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY ai/requirements-runtime.txt ./ai/requirements-runtime.txt
COPY backend ./backend
RUN pip install --no-cache-dir torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r ai/requirements-runtime.txt
RUN pip install --no-cache-dir "numpy==1.26.4" "label-studio-sdk>=1.0.20,<2.0"
COPY ai ./ai
CMD ["arq", "backend.workers.inference_worker.WorkerSettings"]
