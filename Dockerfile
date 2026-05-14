# Multi-target image (last stage = default `docker build .` — Hugging Face & local one-app):
#   docker build .                         → Streamlit :8501 + FastAPI on 127.0.0.1:8000
#   docker build --target api .            → FastAPI only on :8000 (Postgres/Redis compose profile)
#
# Dependency source of truth: pyproject.toml (`pip install .`).

FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY dashboard ./dashboard
COPY .streamlit ./.streamlit
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

# ── API only (use with `docker compose --profile fullstack up`) ──────────────
FROM base AS api

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── One container: co-located FastAPI + Streamlit (HF, default compose) ─────
FROM base AS oneapp

ENV SKIP_DATABASE_INIT=1 \
    REQUIRE_DATABASE=0 \
    PYTHONUNBUFFERED=1 \
    FRAUD_API_BASE=http://127.0.0.1:8000 \
    STREAMLIT_SERVER_HEADLESS=true

RUN chmod +x /app/scripts/run_oneapp.sh

EXPOSE 8501

CMD ["/app/scripts/run_oneapp.sh"]
