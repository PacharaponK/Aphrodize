FROM python:3.11-slim
RUN pip install --no-cache-dir "mlflow>=2.20,<3.0" "psycopg2-binary>=2.9,<3.0" "boto3>=1.35,<2.0"
WORKDIR /app
COPY docker/mlflow-start.sh /app/start.sh
RUN chmod 755 /app/start.sh
EXPOSE 5000
