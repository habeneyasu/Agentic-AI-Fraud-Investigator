# Agentic AI Fraud Investigator

> **Andela AI Engineering Bootcamp — Capstone Demo**  
> A production-oriented fraud operations platform for Andela Digital Bank.

The system automates the full fraud investigation lifecycle — from alert intake through parallel AI evidence collection, hybrid risk scoring, human review, and remediation — using multiple AI agents coordinated by a LangGraph orchestration engine.

The core architectural principle: **deterministic business controls** (triage rules, schema validation, retries, state management) are strictly separated from **probabilistic AI reasoning** (contextual fraud analysis via Cerebras + Gemini). AI operates within strict operational constraints and every decision is auditable and explainable.

---

## Demo Scenarios

**Scenario A — "The Midnight Mule"**  
A $15,000 offshore transfer at 2:30 AM from a student account. The system flags it P1_CRITICAL, runs parallel agents, scores risk at 92/100, pauses for human approval, and executes full remediation in under 4 minutes.

**Scenario B — "Legitimate Tuition Payment"**  
A $2,500 tuition payment to a known beneficiary. The system auto-clears it in under 10 seconds with risk score 18 — no analyst involvement.

**Resilience Demo**  
The Sanctions Agent is intentionally timed out mid-demo. The workflow retries, reduces confidence 0.95 → 0.70, and completes with partial evidence — demonstrating graceful degradation.

---

## Architecture

```
POST /v1/alerts
      │
      ▼
Alert Intake & Idempotency
      │
      ▼
Triage Engine (deterministic rules — no LLM)
      │
      ├── AUTO_CLOSE (amount < $100)
      ├── P3_LOW (rule-only scoring)
      └── P1/P2 → LangGraph Orchestrator
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
  Transaction       KYC Agent    Sanctions
    Agent          (device/geo)    Agent
          └─────────────┼─────────────┘
                        ▼
               Risk Scoring Engine
               (rules + Cerebras/Gemini)
                        │
               Decision Engine (policy)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        AUTO_APPROVE           HITL Review
              │                   │
              └─────────┬─────────┘
                        ▼
               Resolution Engine
               (freeze · reverse · block · SMS)
                        │
               Audit Trail + Fraud Memory
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 (Python 3.11) |
| Orchestration | LangGraph 0.1.5 |
| AI — Fast scoring | Cerebras `llama3.1-70b` |
| AI — Deep reasoning | Google Gemini 1.5 Flash |
| Schema validation | Pydantic v2 |
| Async HTTP | httpx |
| Dashboard | Streamlit 1.35 |
| Logging | structlog |
| Package manager | uv |

---

## Project Structure

```
app/
├── api/                    # FastAPI endpoints
│   ├── alerts.py           # POST /v1/alerts
│   ├── hitl.py             # POST /api/hitl/{id}/decision
│   ├── audit.py            # GET /audit/{id}
│   ├── transactions.py     # Transaction analysis
│   ├── kyc.py              # KYC / device analysis
│   ├── sanctions.py        # Sanctions screening
│   ├── triage.py           # Triage decisions
│   ├── investigation.py    # Investigation workflow
│   ├── fraud_memory.py     # Fraud memory store
│   └── investigate.py      # Full pipeline endpoint (agents + LLM)
│
├── core/                   # Config, logging, security
│   ├── config.py           # Settings (pydantic-settings)
│   ├── logging.py          # Structured logging (structlog)
│   └── security.py         # JWT + API key auth
│
├── llm/                    # LLM integration
│   ├── client.py           # Cerebras + Gemini async clients
│   ├── prompts.py          # Structured JSON prompt templates
│   └── orchestration.py    # Triage, synthesis, HITL recommendation
│
├── agents/                 # Deterministic evidence agents
│   ├── transaction.py      # Velocity + fraud memory analysis
│   ├── kyc_device.py       # Device, geo, login anomaly detection
│   └── sanctions.py        # Country risk + sanctions screening
│
├── graph/                  # LangGraph workflow
│   ├── state.py            # InvestigationState management
│   ├── workflow.py         # Graph nodes, edges, concurrency
│   └── scoring.py          # Hybrid rule + AI risk scoring
│
├── services/               # Business logic layer
│   ├── transaction_service.py
│   ├── kyc_service.py
│   ├── sanctions_service.py
│   ├── triage_service.py
│   ├── investigation_service.py
│   ├── fraud_memory_service.py
│   ├── ai_reasoning_service.py
│   └── action_engine.py
│
├── data/                   # Built-in demo dataset (JSON)
│   ├── transactions.json
│   ├── customers.json
│   ├── kyc_events.json
│   ├── sanctions_data.json
│   └── fraud_memory.json
│
├── shared/                 # Shared models and enums
│   ├── models.py
│   └── enums.py
│
└── main.py                 # FastAPI app entry point

dashboard/
└── streamlit_app.py        # 10-stage end-to-end demo UI

tests/                      # Test suite
docker-compose.yml
pyproject.toml
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/v1/alerts` | Ingest fraud alert (idempotent) |
| `POST` | `/v1/investigate/triage` | AI triage via Cerebras |
| `POST` | `/v1/investigate/full` | Full pipeline: agents + Gemini synthesis |
| `POST` | `/v1/investigate/hitl-recommendation` | Gemini analyst briefing |
| `POST` | `/api/hitl/{id}/decision` | Submit analyst decision |
| `GET` | `/audit/{id}` | Retrieve audit trail |
| `POST` | `/v1/transactions/analyze` | Transaction agent |
| `POST` | `/v1/kyc/analyze` | KYC / device agent |
| `POST` | `/v1/sanctions/analyze` | Sanctions agent |
| `POST` | `/v1/triage/alert` | Rule-based triage |
| `GET` | `/v1/fraud-memory/stats` | Fraud memory statistics |
| `GET` | `/docs` | Swagger UI |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Cerebras API key — [console.cerebras.ai](https://console.cerebras.ai)
- Gemini API key — [aistudio.google.com](https://aistudio.google.com)

### Setup

```bash
# Clone
git clone https://github.com/habeneyasu/Agentic-AI-Fraud-Investigator.git
cd Agentic-AI-Fraud-Investigator

# Create virtual environment and install dependencies
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[test]"
```

### Configure environment

```bash
# Edit .env and add your API keys
CEREBRAS_API_KEY=your-cerebras-api-key
GEMINI_API_KEY=your-gemini-api-key
CEREBRAS_MODEL=llama3.1-70b
GEMINI_MODEL=gemini-1.5-flash
API_KEY=dev-secret-api-key
```

### Run

```bash
# Terminal 1 — Backend API
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Streamlit Dashboard
uv run streamlit run dashboard/streamlit_app.py --server.port 8501
```

- API docs → http://localhost:8000/docs
- Dashboard → http://localhost:8501

### Docker

```bash
docker-compose up -d
```

---

## Demo Dashboard — 10 Stages

The Streamlit dashboard guides the audience through the full investigation lifecycle as a cinematic narrative:

| Stage | What it shows |
|---|---|
| 1 · Data Sources | Upload custom data or use built-in dataset (transactions, KYC, sanctions, fraud memory) |
| 2 · Generate Alert | Flag a suspicious transaction → calls `POST /v1/alerts` |
| 3 · Alerts Queue | Live feed with severity pills, status, and investigation trigger |
| 4 · Triage Gate | Cerebras Llama classifies the alert (AUTO_CLOSE vs ESCALATE) |
| 5 · Agent Lab | Three parallel agents run via `asyncio.gather` with live `st.status()` spinners |
| 6 · AI Risk Scoring | Gemini synthesizes all findings → risk score, evidence chain, reasoning steps |
| 7 · HITL Review | Gemini briefs the analyst → analyst makes the final decision |
| 8 · Resolution | Action engine executes freeze/reverse/block/SMS + fraud memory update |
| 9 · Audit Trail | Full timestamped event log + raw trace + agent evidence archive |
| 10 · Live Dashboard | Real-time metrics, active investigations, risk distribution, fraud trends |

---

## LLM Strategy

| Task | Model | Why |
|---|---|---|
| Alert triage | Cerebras `llama3.1-70b` | Low latency, cost-efficient for fast classification |
| Investigation synthesis | Gemini 1.5 Flash | Strong reasoning for multi-signal evidence analysis |
| HITL analyst briefing | Gemini 1.5 Flash | Structured natural language recommendation |

Both providers have graceful fallback to rule-based logic if the API is unavailable — the demo never breaks.

---

## Risk Scoring

Final score = `(rule_based_score × 0.5) + (ai_context_score × 0.5)`

| Score | Tier | Routing |
|---|---|---|
| ≥ 80 | CRITICAL | HITL required |
| 60–79 | HIGH | HITL required |
| 50–69, confidence < 0.80 | MEDIUM (uncertain) | HITL required |
| < 70, confidence ≥ 0.80 | LOW/MEDIUM | Auto-approve |

Rule weights: velocity spike (0.4) · new device (0.3) · high-risk country (0.3)

---

## Investigation Lifecycle

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

- `X-API-Key` header required on all endpoints
- `X-User-Role` header enforced on HITL and audit endpoints (`Analyst` / `Auditor`)
- JWT token support for future auth expansion
- Input validation via Pydantic v2 on all request bodies

---

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app tests/
```

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built by Haben Eyasu Akelom for the Andela AI Engineering Bootcamp.*
