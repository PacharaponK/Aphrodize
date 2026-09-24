FROM api_image
RUN pip install --no-cache-dir "psycopg2-binary>=2.9,<3.0" "boto3>=1.35,<2.0"
WORKDIR /app
COPY docker/mlflow-start.sh /app/start.sh
RUN chmod 755 /app/start.sh
EXPOSE 5000
