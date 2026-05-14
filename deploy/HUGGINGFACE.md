# Deploy to Hugging Face Spaces

This repository is set up as a **single Docker app**: **Streamlit** is the public UI (port **8501**), and **FastAPI** runs on `127.0.0.1:8000` inside the same container (`FRAUD_API_BASE` is set accordingly in the image).

## Deploy to `habeneyasu/maulti-agent-ai-fraud-investigator`

**Space URL:** [https://huggingface.co/spaces/habeneyasu/maulti-agent-ai-fraud-investigator](https://huggingface.co/spaces/habeneyasu/maulti-agent-ai-fraud-investigator)

### Path A — GitHub-linked Space (recommended)

1. In the Space: **Settings** (gear) → **Repository** (or **Build** / **Linked repository**).
2. Set **GitHub repository** to `habeneyasu/Agentic-AI-Fraud-Investigator`.
3. Set **branch** to **`main`** (or `hf-space` if you prefer that branch).
4. Ensure the Space type is **Docker** (not Streamlit).
5. **Settings → Secrets:** `CEREBRAS_API_KEY`, `GEMINI_API_KEY` (and optionally `GOOGLE_API_KEY`, `API_KEY`) — use **Secrets**, not public Variables.
6. Push any commit to the linked branch on GitHub (`git push origin main`). Hugging Face will **rebuild** the Space automatically (watch **Logs**).

### Path B — Push this repo to the Space’s Git remote (no GitHub link)

Use this only if the Space is **not** connected to GitHub and you maintain code only on HF.

1. Install the CLI: `pip install huggingface_hub` then `huggingface-cli login` (use a **write** token with Spaces scope).
2. From your clone of **this** repository:

```bash
git remote add hf https://huggingface.co/spaces/habeneyasu/maulti-agent-ai-fraud-investigator
# if `hf` already exists: git remote set-url hf https://huggingface.co/spaces/habeneyasu/maulti-agent-ai-fraud-investigator

git push hf main:main
```

Use the branch name your Space tracks (often `main`). If the push is rejected, open the Space **Files** tab and confirm you are allowed to push; you may need to pull first: `git pull hf main --rebase` then push again.

3. After a successful push, open **Logs** and wait for the Docker build to finish, then open the **App** tab.

---

## 1. Create the Space

1. Open [Create a new Space](https://huggingface.co/new-space).
2. Choose **Docker** as the SDK (**not** “Streamlit”). If you pick Streamlit, Hugging Face serves its stock **“Welcome to Streamlit”** spiral demo (`/streamlit_app.py`) instead of this project — delete the Space and recreate it as **Docker**, or duplicate the Space with Docker selected.
3. Link your GitHub repository (or push this repo to a Hugging Face Space git remote).
4. Hardware: **CPU basic** is enough for demos; first build can take several minutes.

## 2. Space `README.md` (required metadata)

Hugging Face reads the **YAML block at the very top** of the repository root `README.md` to pick the SDK, port, and timeouts. The default `docker build .` uses the **`oneapp`** stage (last stage in `Dockerfile`).

**Recommended — branch `main`:** root `README.md` on **`main`** already includes the YAML front matter (same fields as [`SPACE_README_SNIPPET.md`](./SPACE_README_SNIPPET.md)). In your Space **Settings → Repository**, point the Space at the **`main`** branch so Hugging Face picks up `sdk: docker` and `app_port: 8501` automatically.

**Optional — branch `hf-space`:** an alternate branch kept aligned with `main`, useful if you ever want deploy-only edits without touching `main` first.

**Option — edit on HF:** after the Space exists, you can paste the snippet from [`SPACE_README_SNIPPET.md`](./SPACE_README_SNIPPET.md) at the top of the Space’s `README.md` in the web editor, then rebuild.

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

Use **Secrets** (private) for anything sensitive. **Do not** put `CEREBRAS_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `API_KEY` under **Variables** — those are visible in the Space UI and in Hub metadata as “public”.

| Name | Where to add | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | **Secrets** | Investigation synthesis / narratives |
| `CEREBRAS_API_KEY` | **Secrets** | Fast triage / optional paths |
| `ANTHROPIC_API_KEY` | **Secrets** | If you wire Anthropic elsewhere |
| `API_KEY` | **Secrets** | If set on the server, Streamlit must send `X-API-Key` (same value here) |

Reserve **Variables** only for non-sensitive flags (e.g. `ENVIRONMENT=production` if you add such wiring).

The image already sets:

- `SKIP_DATABASE_INIT=1` — no Postgres in the container (JSON / in-memory paths).
- `FRAUD_API_BASE=http://127.0.0.1:8000` — dashboard talks to the co-located API.

Do **not** point `FRAUD_API_BASE` at the public Space URL unless you intentionally split frontend and API across deployments.

## 4. Build and open

After the Space build succeeds, open the Space URL. You should see the **Agentic AI Fraud Investigator** Streamlit command center. `/docs` is not exposed on the public port; the UI calls the API internally.

## 5. Troubleshooting

- **“Welcome to Streamlit” + spiral sliders + “Edit /streamlit_app.py”:** the Space is using the **Streamlit** SDK template, not this repo’s **Docker** image. Recreate the Space (or switch SDK) so **Docker** is selected; confirm root `README.md` on the linked branch starts with YAML where `sdk: docker` and `app_port: 8501`.
- **API-only image:** `docker build --target api .` produces FastAPI on `:8000` (same dependency layer as `oneapp`).
- **Build fails on `pip install .`:** ensure `pyproject.toml`, `app/`, `dashboard/`, `.streamlit/`, and `scripts/` are present in the build context (root `Dockerfile` copies them explicitly).
- **Space unhealthy / timeout:** raise `startup_duration_timeout` in the README YAML; first `pip install` is heavy on CPU-basic.
- **401 from API:** set `API_KEY` in Space secrets to match what the FastAPI app expects, or clear `API_KEY` in your deployment so key checks stay disabled (demos only).

## Reference

- [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Spaces configuration](https://huggingface.co/docs/hub/spaces-config-reference)
