FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir torch==2.1.2 --index-url ${TORCH_INDEX_URL}
RUN pip install --no-cache-dir \
    "arq>=0.26,<0.27" "asyncpg>=0.30,<0.31" "boto3>=1.34,<2" \
    "mlflow>=2.20,<3.0" "numpy==1.26.4" "pillow>=11.1,<12.0" \
    "pydantic-settings>=2.7,<3.0" "sqlalchemy>=2.0.36,<2.1" "prometheus-client>=0.21,<0.25" \
    "fastapi>=0.115,<0.116" "minio>=7.2,<8.0" "label-studio-sdk>=1.0.20,<2.0"
COPY backend ./backend
COPY ai ./ai
CMD ["arq", "backend.workers.trainer_worker.WorkerSettings"]
