# AWS App Runner configuration

Use the **same container image** as Hugging Face / `docker compose` (root `Dockerfile`, default **oneapp** target). App Runner exposes a **single HTTP port**; Streamlit must listen on that port while FastAPI stays on loopback inside the container.

## Image

- Build: `docker build -f Dockerfile .` (default stage = `oneapp`)
- Push to ECR (or Container Registry of your choice) and reference that URI in App Runner.

## Port

- **Container port / App Runner port:** **8080** (App Runner default) or **8501** if your service allows it.
- Set **`STREAMLIT_SERVER_PORT=8080`** (or `8501`) so Streamlit binds to the port App Runner forwards. Do **not** change `FRAUD_API_BASE` from `http://127.0.0.1:8000` unless you split API and UI across services.

## Environment variables

| Variable | Example | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `production` | |
| `STREAMLIT_SERVER_PORT` | `8080` | Match App Runner port |
| `SKIP_DATABASE_INIT` | `1` | No Postgres in typical App Runner demo |
| `FRAUD_API_BASE` | `http://127.0.0.1:8000` | Co-located API (default in image) |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | (secret) | Optional LLM |
| `CEREBRAS_API_KEY` | (secret) | Optional LLM |
| `API_KEY` | (secret) | Optional; if set, clients must send `X-API-Key` |

## Health check

- **Path:** `/_stcore/health`
- **Port:** same as Streamlit (e.g. 8080)

## Steps

1. App Runner console → Create service → Container image from ECR.
2. Set port to **8080** (or align with `STREAMLIT_SERVER_PORT`).
3. Add secrets/variables as above.
