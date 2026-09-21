FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN pip install --no-cache-dir .
CMD ["arq", "backend.workers.trainer_worker.WorkerSettings"]
