FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY ai/requirements-runtime.txt ./ai/requirements-runtime.txt
COPY backend ./backend
RUN pip install --no-cache-dir torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r ai/requirements-runtime.txt
COPY ai ./ai
CMD ["arq", "backend.workers.inference_worker.WorkerSettings"]
