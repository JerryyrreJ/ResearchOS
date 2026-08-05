FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MACROTRACE_ENV=production \
    MACROTRACE_SERVE_FRONTEND=true \
    MACROTRACE_DATABASE_PATH=/app/runtime/macrotrace.duckdb \
    MACROTRACE_ARTIFACT_DIR=/app/runtime/artifacts

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt /app/requirements.runtime.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.runtime.txt

COPY . /app
RUN mkdir -p /app/runtime/artifacts

EXPOSE 8000

CMD ["python", "scripts/container_entrypoint.py"]
