# Deploy to Hugging Face Spaces

This repository is set up as a **single Docker app**: **Streamlit** is the public UI (port **8501**), and **FastAPI** runs on `127.0.0.1:8000` inside the same container (`FRAUD_API_BASE` is set accordingly in the image).

## 1. Create the Space

1. Open [Create a new Space](https://huggingface.co/new-space).
2. Choose **Docker** as the SDK (not Streamlit SDK — we need the combined image).
3. Link your GitHub repository (or push this repo to a Hugging Face Space git remote).
4. Hardware: **CPU basic** is enough for demos; first build can take several minutes.

## 2. Space `README.md` (required metadata)

Hugging Face reads the **YAML block at the very top** of the repository root `README.md` to pick the SDK, port, and timeouts. The default `docker build .` uses the **`oneapp`** stage (last stage in `Dockerfile`).

**Option A — deploy branch (recommended for GitHub):** create a branch (e.g. `hf-space`), put the snippet from [`SPACE_README_SNIPPET.md`](./SPACE_README_SNIPPET.md) **first**, then your normal README body below the closing `---`.

**Option B — edit on HF:** after the Space exists, use the Space file editor and paste the same snippet at the top of `README.md`, then rebuild.

Critical fields:

| Field | Value | Why |
| --- | --- | --- |
| `sdk` | `docker` | Uses root `Dockerfile` |
| `app_port` | `8501` | Must match Streamlit (`scripts/run_oneapp.sh`) |

Optional: increase cold-start tolerance, for example:

```yaml
startup_duration_timeout: 20m
```

## 3. Secrets and variables (Space → Settings)

Add **Secrets** (or **Variables**) so the API and dashboard can call LLMs and optional API key auth:

| Name | Notes |
| --- | --- |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Investigation synthesis / narratives |
| `CEREBRAS_API_KEY` | Fast triage / optional paths |
| `ANTHROPIC_API_KEY` | If you wire Anthropic elsewhere |
| `API_KEY` | If set on the server, Streamlit must send `X-API-Key` (set the same value here) |

The image already sets:

- `SKIP_DATABASE_INIT=1` — no Postgres in the container (JSON / in-memory paths).
- `FRAUD_API_BASE=http://127.0.0.1:8000` — dashboard talks to the co-located API.

Do **not** point `FRAUD_API_BASE` at the public Space URL unless you intentionally split frontend and API across deployments.

## 4. Build and open

After the Space build succeeds, open the Space URL. You should see the **Agentic AI Fraud Investigator** Streamlit command center. `/docs` is not exposed on the public port; the UI calls the API internally.

## 5. Troubleshooting

- **API-only image:** `docker build --target api .` produces FastAPI on `:8000` (same dependency layer as `oneapp`).
- **Build fails on `pip install .`:** ensure `pyproject.toml`, `app/`, `dashboard/`, `.streamlit/`, and `scripts/` are present in the build context (root `Dockerfile` copies them explicitly).
- **Space unhealthy / timeout:** raise `startup_duration_timeout` in the README YAML; first `pip install` is heavy on CPU-basic.
- **401 from API:** set `API_KEY` in Space secrets to match what the FastAPI app expects, or clear `API_KEY` in your deployment so key checks stay disabled (demos only).

## Reference

- [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Spaces configuration](https://huggingface.co/docs/hub/spaces-config-reference)
