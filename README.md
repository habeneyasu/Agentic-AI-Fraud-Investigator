# Agentic AI Fraud Investigator

Reference implementation of an **agentic fraud investigation pipeline** for digital banking and payments operations. The platform automates the investigation lifecycle—from alert intake through parallel evidence collection, hybrid risk scoring, human-in-the-loop (HITL) review, and remediation—using coordinated AI agents and a **LangGraph** orchestration layer.

**Design principle:** deterministic controls (triage rules, schema validation, retries, workflow state) are separated from probabilistic reasoning (contextual fraud analysis via Cerebras and Google Gemini). Model outputs are constrained by policy, and outcomes are intended to be **auditable** and **traceable**.

---

## Table of contents

- [Capabilities](#capabilities)
- [Demo scenarios](#demo-scenarios)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [API surface](#api-surface)
- [Getting started](#getting-started)
- [Hugging Face Spaces](#hugging-face-spaces)
- [Dashboard](#dashboard)
- [LLM usage](#llm-usage)
- [Risk scoring](#risk-scoring)
- [Investigation lifecycle](#investigation-lifecycle)
- [Security](#security)
- [Testing](#testing)
- [License](#license)

---

## Capabilities

- Idempotent **alert ingestion** and rule-first **triage** (no LLM on the fast path where configured).
- **Parallel specialist agents** (transactions, KYC/device, sanctions) with orchestrated aggregation.
- **Hybrid scoring** combining rule-based signals and LLM-assisted context.
- **HITL** gates for high/uncertain risk with structured analyst decisions and audit retrieval.
- **Resolution** actions (e.g. freeze, reverse, block, notify) and **fraud memory** updates for downstream detection.
- **Streamlit** walkthrough for end-to-end demos and stakeholder reviews.

Synthetic demo data is included for local evaluation; adapt data sources and policies before any production deployment.

---

## Demo scenarios

| Scenario | Description |
| --- | --- |
| **A — High-value off-hours transfer** | A large offshore transfer from a low-typical-activity account: escalated severity, parallel agents, elevated risk score, HITL approval, then remediation. |
| **B — Known-beneficiary payment** | A tuition-style payment to a known counterparty: low risk, fast auto-clearance with minimal latency. |
| **Resilience** | Sanctions agent timeout: workflow retries, reduced confidence (e.g. 0.95 → 0.70), completion with partial evidence to illustrate degradation behavior. |

---

## Architecture

```
POST /v1/alerts
      │
      ▼
Alert intake & idempotency
      │
      ▼
Triage engine (deterministic rules — no LLM)
      │
      ├── AUTO_CLOSE (example: amount < $100)
      ├── P3_LOW (rule-only scoring)
      └── P1/P2 → LangGraph orchestrator
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
  Transaction       KYC agent     Sanctions
    agent          (device/geo)     agent
          └─────────────┼─────────────┘
                        ▼
               Risk scoring engine
               (rules + Cerebras / Gemini)
                        │
               Decision engine (policy)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        AUTO_APPROVE           HITL review
              │                   │
              └─────────┬─────────┘
                        ▼
               Resolution engine
               (freeze · reverse · block · SMS)
                        │
               Audit trail + fraud memory
```

---

## Technology stack

| Layer | Technology |
| --- | --- |
| API | FastAPI 0.111 (Python 3.11) |
| Orchestration | LangGraph 0.1.5 |
| Fast path / triage LLM | Cerebras `llama3.1-70b` |
| Synthesis / briefing LLM | Google Gemini 1.5 Flash |
| Validation | Pydantic v2 |
| HTTP client | httpx |
| Dashboard | Streamlit 1.35 |
| Logging | structlog |
| Packaging | uv |

---

## Repository layout

```
app/
├── api/                    # HTTP routes
│   ├── alerts.py           # POST /v1/alerts
│   ├── hitl.py             # POST /api/hitl/{id}/decision
│   ├── audit.py            # GET /audit/{id}
│   ├── transactions.py     # Transaction analysis
│   ├── kyc.py              # KYC / device analysis
│   ├── sanctions.py        # Sanctions screening
│   ├── triage.py           # Triage decisions
│   ├── investigation.py    # Investigation workflow
│   ├── fraud_memory.py     # Fraud memory store
│   └── investigate.py      # Full pipeline (agents + LLM)
├── core/                   # Configuration, logging, security
├── llm/                    # LLM clients, prompts, orchestration helpers
├── agents/                 # Evidence-oriented agents
├── graph/                  # LangGraph state, workflow, scoring
├── services/               # Domain services and action engine
├── data/                   # Demo JSON datasets
├── shared/                 # Shared models and enums
└── main.py                 # Application entrypoint

dashboard/
└── streamlit_app.py        # Guided demo UI

tests/
deploy/                     # Hugging Face Spaces README snippet + deploy guide
docker-compose.yml          # default: one app (:8501); profile `fullstack`: API + Postgres + Redis
pyproject.toml
```

---

## API surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness / health |
| `POST` | `/v1/alerts` | Ingest fraud alert (append to runtime queue) |
| `POST` | `/v1/alerts/generate` | Policy engine: create alerts from transactions / KYC |
| `POST` | `/v1/triage/assess` | Deterministic triage (+ optional narrative) |
| `POST` | `/v1/investigation/customer-langgraph-deep` | LangGraph agents + synthesis + HITL payload |
| `POST` | `/v1/investigation/hitl-recommendation` | Analyst briefing (LLM) |
| `POST` | `/api/hitl/{id}/decision` | Submit analyst decision |
| `GET` | `/audit/{id}` | Audit trail |
| `POST` | `/v1/transactions/analyze` | Transaction agent |
| `POST` | `/v1/kyc/analyze` | KYC / device agent |
| `POST` | `/v1/sanctions/analyze` | Sanctions agent |
| `GET` | `/v1/sanctions` | Sanctions reference (`resource=watchlist`, `country_risks`, or `all`) |
| `POST` | `/v1/sanctions` | Append rows: canonical ``{"resource","items"}``, or legacy ``sanctions_data.json`` shape ``{"sanctions_entries":[...],"country_risks":[...]}`` (either or both keys) |
| `POST` | `/v1/triage/alert` | Rule-based triage |
| `GET` | `/v1/fraud-memory` | Patterns or stats (`view=patterns|stats`; patterns use `filter` + optional slice params) |
| `POST` | `/v1/fraud-memory` | Mutations (`operation=add_pattern|cleanup|bump_frequency|delete`) |
| `GET` | `/v1/fraud-memory/health` | Fraud memory liveness (no API key) |
| `GET` | `/docs` | OpenAPI (Swagger UI) |

**Note:** Older scattered sanctions routes (`/v1/sanctions/list`, `…/create`, `…/create-bulk`, country-risk mirrors) and fraud-memory routes (`/patterns`, `/patterns/entity/…`, `PUT …/frequency`, `POST /search`, etc.) are folded into the consolidated `GET`/`POST` pairs above.

---

## Getting started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- API keys: [Cerebras](https://console.cerebras.ai), [Google AI Studio](https://aistudio.google.com) (Gemini)

### Install

```bash
git clone https://github.com/habeneyasu/Agentic-AI-Fraud-Investigator.git
cd Agentic-AI-Fraud-Investigator

uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[test]"
```

### Configuration

Copy `.env.example` to `.env` and set at least:

```bash
CEREBRAS_API_KEY=your-cerebras-api-key
GEMINI_API_KEY=your-gemini-api-key
CEREBRAS_MODEL=llama3.1-70b
GEMINI_MODEL=gemini-1.5-flash
```

Use strong, non-default secrets in any shared or internet-facing environment. Optionally set `API_KEY` on the API so clients must send matching `X-API-Key`; if unset, key checks are disabled for local demos.

### Run locally

```bash
# API
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Dashboard (separate terminal)
uv run streamlit run dashboard/streamlit_app.py --server.port 8501
```

- API documentation: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`

### Docker (one app)

The root **`Dockerfile`** defines two build targets (same dependency install from `pyproject.toml`):

| Target | Use | Exposed |
| --- | --- | --- |
| `oneapp` (default) | `docker compose up`, Hugging Face | Streamlit **8501**; FastAPI on `127.0.0.1:8000` inside the container |
| `api` | `docker compose --profile fullstack` | FastAPI **8000** only (with Postgres + Redis) |

The default image runs **FastAPI and Streamlit in one container**: the API listens on `127.0.0.1:8000` inside the container, and the dashboard is exposed on **port 8501** (same layout as Hugging Face Docker Spaces).

```bash
docker compose up --build
```

Open **http://localhost:8501** for the command center. OpenAPI is still available from inside the network; to reach `/docs` from your host, use `docker compose exec app curl -s http://127.0.0.1:8000/docs | head`, or run the **API-only** stack below.

Optional **Postgres + Redis + API-only** (no Streamlit; FastAPI on **:8000**):

```bash
docker compose --profile fullstack up -d
```

### Hugging Face Spaces

Deploy as **one Docker Space** (same image as `docker compose up`): FastAPI + Streamlit in one container; the Space must expose **port 8501** to the internet.

1. [Create a Docker Space](https://huggingface.co/new-space) and connect this repository.
2. Put the YAML card from [`deploy/SPACE_README_SNIPPET.md`](deploy/SPACE_README_SNIPPET.md) at the **very top** of root `README.md` (see branch / editor options in the guide), with **`sdk: docker`** and **`app_port: 8501`**.
3. In Space **Settings → Secrets**, add optional `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `CEREBRAS_API_KEY`, and `API_KEY` if you use keyed routes.

Full walkthrough: [`deploy/HUGGINGFACE.md`](deploy/HUGGINGFACE.md).

---

## Dashboard

The Streamlit application walks through **ten stages**: data sources, alert generation, queue, triage, parallel agent execution, AI-assisted risk scoring, HITL review, resolution, audit trail, and summary metrics. It is intended for demos, training, and integration smoke tests against a running API.

---

## LLM usage

| Task | Model | Rationale |
| --- | --- | --- |
| Alert triage | Cerebras `llama3.1-70b` | Low-latency classification |
| Investigation synthesis | Gemini 1.5 Flash | Multi-signal reasoning |
| HITL briefing | Gemini 1.5 Flash | Structured narrative for analysts |

If provider APIs are unavailable, the implementation falls back to rule-based logic where implemented.

---

## Risk scoring

Deep investigation responses expose two numbers: **pipeline risk** (`rule_based_score`, LangGraph aggregate) and **final risk** (`final_risk_score`, from the LLM synthesis JSON). The dashboard treats the latter as the case score; it reflects narrative reasoning over agent outputs, not an embedding “context quality” metric.

| Score | Tier | Typical routing |
| --- | --- | --- |
| ≥ 80 | CRITICAL | HITL |
| 60–79 | HIGH | HITL |
| 50–69 with confidence < 0.80 | MEDIUM (uncertain) | HITL |
| < 70 with confidence ≥ 0.80 | LOW / MEDIUM | Auto-approve (policy-dependent) |

Example rule weights: velocity spike (0.4), new device (0.3), high-risk country (0.3). Tune weights and thresholds to your risk appetite and governance requirements.

---

## Investigation lifecycle

```
RECEIVED → TRIAGE → INVESTIGATING → SCORING → DECIDING
                                                    │
                              ┌─────────────────────┤
                              ▼                     ▼
                        AUTO_APPROVE          AWAITING_HUMAN
                              │                     │
                              └──────────┬──────────┘
                                         ▼
                               RESOLUTION_IN_PROGRESS
                                         │
                    ┌────────────────────┤
                    ▼                    ▼
         CLOSED_FRAUD_CONFIRMED   CLOSED_FALSE_POSITIVE

Also: CLOSED_AUTO_CLEARED · CLOSED_LOW_RISK · PARTIAL_EVIDENCE · FAILED
```

---

## Security

- When `API_KEY` is set in the environment, business routes require matching `X-API-Key` (see `app/api/deps.py`). If `API_KEY` is unset or empty, key checks are skipped (local demos only). `/health` and `/` are typically unauthenticated.
- HITL and audit routes also expect `X-User-Role` (`Analyst` / `Auditor`) where enforced in code.
- JWT utilities exist for future auth expansion.
- Request bodies validated with Pydantic v2.

Treat this as a **reference** stack: harden networking, secrets management, and identity before any production or regulated deployment.

---

## Testing

```bash
uv run pytest
uv run pytest --cov=app tests/
```

**Demo JSON (`app/data/`)** is aligned with the Streamlit walkthrough and investigator console:

| Step | Customer | Role |
| --- | --- | --- |
| **Midnight mule / HITL** | `CUST003` | Off-hours IR transfer (`TXN10001`) + high-value KP wire (`TXN10004`); KYC geo mismatch same night; fraud-memory hits. |
| **Escalated corridor** | `CUST001` | RU destination + device-change KYC (`TXN10002`). |
| **Velocity / medium** | `CUST002` | CN purchase + brute-force KYC story (`TXN10003`). |
| **Auto-clear / low risk** | `CUST002` | Small US withdrawal `TXN10006`; `CUST001` US purchase `TXN10005` for benign baseline. |

Timestamps are **May 2026** so triage recency logic treats them as current. `runtime_alerts.json` ships as **`[]`**; run **`POST /v1/alerts/generate`** (or the dashboard **View alerts** button) to materialise alerts from Postgres-backed transactions.

---

## License

MIT — see [LICENSE](LICENSE).
