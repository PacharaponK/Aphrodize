FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.11-slim AS build
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock README.md ./
COPY models ./models
COPY backend ./backend
RUN uv sync --locked --no-default-groups --group production --no-install-package opencv-python

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/backend /app/backend
COPY --from=build /app/models /app/models
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
