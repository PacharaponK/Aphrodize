#!/bin/sh
set -eu

encoded_password="$(python -c 'import os; from urllib.parse import quote; print(quote(os.environ["POSTGRES_PASSWORD"], safe=""))')"
exec mlflow server --host 0.0.0.0 --port 5000 \
  --backend-store-uri "postgresql://${POSTGRES_USER}:${encoded_password}@${POSTGRES_HOST}:5432/mlflow" \
  --default-artifact-root s3://mlflow
