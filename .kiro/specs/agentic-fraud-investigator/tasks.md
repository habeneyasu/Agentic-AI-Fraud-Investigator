# Implementation Plan: Agentic AI Fraud Investigator

## Overview

Three-day implementation of the Andela Digital Bank fraud investigation platform. Each day maps to a distinct architectural layer: Day 1 builds the API foundation and deterministic control plane, Day 2 builds the LangGraph orchestration and AI agent layer, Day 3 builds the human review, resolution, observability, and demo scenarios.

All code is Python 3.11. PostgreSQL is the single primary database (via `asyncpg`). Property-based tests use Hypothesis. Unit tests use pytest + pytest-asyncio.

---

## Tasks

### Day 1 — API Foundation, Triage, and State Initialization

- [ ] 1. Set up project structure, dependencies, and configuration
  - Create directory layout: `app/`, `app/api/`, `app/agents/`, `app/core/`, `app/models/`, `app/services/`, `tests/`
  - Create `pyproject.toml` or `requirements.txt` with pinned versions: `fastapi`, `uvicorn`, `pydantic>=2`, `langgraph`, `anthropic`, `boto3`, `hypothesis`, `pytest`, `pytest-asyncio`
  - Create `app/config.py` with environment-based settings (API keys, DynamoDB table names, thresholds)
  - Create `conftest.py` with Hypothesis profiles (`ci` max_examples=100, `dev` max_examples=50)
  - _Requirements: 13.1, 13.4_

- [ ] 2. Define all Pydantic data models
  - [ ] 2.1 Implement core data models in `app/models/`
    - Write `AlertPayload`, `InvestigationState` (TypedDict), `TransactionResult`, `KYCResult`, `SanctionsResult`, `RiskResult`, `ExplanationEntry`, `WorkflowTraceEntry`, `AuditTrailEntry`, `FraudMemoryItem` exactly as specified in the design
    - Write `InvestigationStatus` enum covering all 11 states from the lifecycle diagram
    - _Requirements: 1.1, 3.1, 4.5, 4.6, 4.7, 5.5_

  - [ ]* 2.2 Write property test for Investigation state initialization completeness
    - **Property 5: Investigation State Initialization Completeness**
    - **Validates: Requirements 3.1**
    - Use `st.builds(AlertPayload)` to generate random alerts; assert all required fields are non-None after `init_node`

- [ ] 3. Provision PostgreSQL database
  - [ ] 3.1 Create database migration script in `app/core/db_setup.py`
    - Implement `create_tables()` that runs the SQL DDL from the design to create all six tables:
      `investigations`, `agent_outputs`, `audit_trail`, `fraud_memory`, `idempotency_keys`, `state_snapshots`
    - Ensure `audit_trail` has no UPDATE/DELETE permissions (enforce via DB role or application-level guard)
    - Add indexes as specified in the design schema
    - _Requirements: 3.2, 9.5, 11.4_

  - [ ] 3.2 Implement async PostgreSQL client wrapper in `app/core/db.py`
    - Write async helpers using `asyncpg`: `fetch_one`, `fetch_all`, `execute`, `execute_many`
    - Implement connection pool initialization (`asyncpg.create_pool`) in app startup
    - Raise a typed `DBConnectivityError` on connection failures for use by the intake layer
    - _Requirements: 1.6, 3.3_

- [ ] 4. Implement Alert Intake endpoint
  - [ ] 4.1 Implement idempotency service in `app/services/idempotency.py`
    - Write `compute_idempotency_key(transaction_id, alert_hash) -> str` using `sha256(transaction_id + alert_hash)`
    - Write `check_and_store(key, investigation_id)` that queries `idempotency_keys` table; returns existing `investigation_id` on hit or inserts and returns `None` on miss
    - _Requirements: 1.3, 1.4_

  - [ ]* 4.2 Write property test for idempotency key determinism
    - **Property 1: Idempotency Key Determinism**
    - **Validates: Requirements 1.3**
    - Use `st.text()` for `transaction_id` and `alert_hash`; assert same inputs always produce same key equal to `sha256(transaction_id + alert_hash)`

  - [ ]* 4.3 Write property test for duplicate alert deduplication
    - **Property 2: Duplicate Alert Deduplication**
    - **Validates: Requirements 1.4**
    - Use `st.builds(AlertPayload)`; submit same alert twice; assert second returns HTTP 200 with same `investigation_id` and no new DynamoDB item

  - [ ] 4.4 Implement `POST /v1/alerts` in `app/api/intake.py`
    - Validate `X-API-Key` header; return HTTP 401 on missing/invalid key
    - Call idempotency service; return HTTP 200 with existing status on duplicate
    - On new alert: insert Investigation record into PostgreSQL `investigations` table, return HTTP 202 with `investigation_id` within 500ms
    - Return HTTP 503 with `"retryable": true` on `DBConnectivityError`
    - Dispatch async orchestration task (fire-and-forget) after returning 202
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6_

  - [ ]* 4.5 Write property test for valid alert intake response
    - **Property 3: Valid Alert Intake Response**
    - **Validates: Requirements 1.5**
    - Use `st.builds(AlertPayload)` with valid API key; assert HTTP 202, non-empty `investigation_id`, and `RECEIVED` status in DynamoDB

- [ ] 5. Implement Triage Engine
  - [ ] 5.1 Implement `app/services/triage.py`
    - Write `classify(alert: AlertPayload) -> TriageResult` with the full 4-tier cost-aware routing:
      - `amount < 100` → `AUTO_CLOSE` (no agents, no LLM)
      - `amount > 1000` AND `recipient_country in HIGH_RISK_COUNTRIES` → `P1_CRITICAL` (full AI investigation)
      - `amount 100–1000` OR `recipient_country in MEDIUM_RISK_COUNTRIES` → `P2_STANDARD` (full AI investigation)
      - `amount 100–500`, no risk signals → `P3_LOW`: run rule-only score; if score < 30 → `CLOSED_LOW_RISK`; else escalate to P2
    - Define `HIGH_RISK_COUNTRIES = {"NG","KP","IR","SY","CU","VE","MM","BY"}` and `MEDIUM_RISK_COUNTRIES = {"RU","UA","PK","BD","GH","KE","TZ"}` as config constants
    - Ensure no LLM is invoked at any point; classification completes within 50ms
    - _Requirements: 2.1–2.6_

  - [ ]* 5.2 Write property test for triage routing correctness
    - **Property 4: Triage Routing Correctness**
    - **Validates: Requirements 2.1–2.4**
    - Use `st.floats(min_value=0)` for amount and `st.sampled_from(countries)` for country; assert exactly one disposition per alert, no alert falls through without a disposition

  - [ ]* 5.3 Write property test for triage LLM exclusion
    - **Property 5: Triage LLM Exclusion**
    - **Validates: Requirements 2.5**
    - Use `st.builds(AlertPayload)`; mock the LLM client and assert it is never called during triage classification

- [ ] 6. Implement Investigation initialization and checkpointing
  - [ ] 6.1 Implement `app/services/investigation.py`
    - Write `create_investigation(alert, priority) -> InvestigationState` that populates all required fields with defaults (`risk_score=0`, `confidence=1.0`, `retry_count=0`, `human_decision=None`, etc.)
    - Write `checkpoint(state: InvestigationState)` that serializes and upserts full state to `investigations.checkpoint_data` JSONB column in PostgreSQL
    - Write `load_checkpoint(investigation_id) -> InvestigationState` for recovery
    - Write `save_snapshot(investigation_id, stage, snapshot: StateSnapshot)` that inserts into `state_snapshots` table
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 6.2 Write property test for checkpoint recovery round-trip
    - **Property 6: Checkpoint Recovery Round-Trip**
    - **Validates: Requirements 3.3**
    - Use `st.builds(InvestigationState)` with non-terminal statuses; serialize to DynamoDB and deserialize; assert field-by-field equivalence

- [ ] 7. Implement mock banking integration endpoints
  - Create `app/api/mocks.py` with four FastAPI routes: `POST /mock/freeze-account`, `POST /mock/reverse-transaction`, `POST /mock/block-login`, `POST /mock/send-sms`
  - Each mock returns `{"success": true, "action": "<action_name>"}` after a simulated 50–200ms `asyncio.sleep` delay
  - _Requirements: 8.2_

- [ ] 8. Wire FastAPI app and run Day 1 checkpoint
  - Create `app/main.py` registering all routers (intake, mocks)
  - Implement API key validation as a FastAPI dependency in `app/core/auth.py`
  - Implement role enforcement dependency `require_role(*roles)` in `app/core/auth.py`
  - [ ] 8.1 Checkpoint — Ensure all Day 1 tests pass, ask the user if questions arise.

---

### Day 2 — LangGraph Orchestration, Parallel Agents, Risk Scoring, Decision Engine

- [ ] 9. Implement LangGraph graph structure and state machine
  - [ ] 9.1 Define LangGraph graph in `app/core/graph.py`
    - Define all 13 nodes from the design: `intake_node`, `triage_node`, `init_node`, `evidence_node`, `transaction_agent_node`, `kyc_agent_node`, `sanctions_agent_node`, `risk_scoring_node`, `decision_node`, `hitl_node`, `resolution_node`, `audit_node`, `close_node`
    - Wire conditional edges using `route_after_triage`, `route_after_decision`, `route_after_hitl` exactly as specified in the design
    - Enforce `asyncio.Semaphore(50)` concurrency at the graph entry point
    - _Requirements: 3.4, 4.1_

  - [ ]* 9.2 Write property test for concurrency limit enforcement
    - **Property 7: Concurrency Limit Enforcement**
    - **Validates: Requirements 3.4**
    - Use `st.integers(min_value=51, max_value=200)` for burst size; assert active investigation count never exceeds 50 using a mock semaphore counter

- [ ] 10. Implement parallel evidence collection with retry logic
  - [ ] 10.1 Implement agent retry wrapper in `app/core/retry.py`
    - Write `with_retry(agent_fn, max_attempts=3, base_delay=2, multiplier=2)` using exponential backoff (delays: 2s, 4s, 8s)
    - On all retries exhausted: return `None` and reduce confidence by 0.30
    - On Pydantic `ValidationError`: return `None` and reduce confidence by 0.20
    - Apply `max(0.10, confidence - accumulated_reductions)` floor
    - _Requirements: 4.2, 4.3, 4.4_

  - [ ]* 10.2 Write property test for agent retry policy
    - **Property 8: Agent Retry Policy**
    - **Validates: Requirements 4.2**
    - Use `st.just(always_failing_agent)`; assert agent is invoked exactly 3 times before being marked timed out, never a 4th time

  - [ ]* 10.3 Write property test for confidence reduction accumulation
    - **Property 9: Confidence Reduction Accumulation**
    - **Validates: Requirements 4.3, 4.4**
    - Use `st.integers(0, 3)` for timeout count and `st.integers(0, 3)` for schema failure count; assert `final_confidence == max(0.10, 1.0 - timeouts*0.30 - schema_failures*0.20)`

  - [ ] 10.4 Implement `evidence_node` in `app/core/graph.py`
    - Fan out to all three agents using `asyncio.gather` with individual retry wrappers
    - Accumulate confidence reductions from each agent's outcome
    - If all agents fail → transition to `FAILED` via `route_after_evidence`
    - If 1–2 agents fail → transition to `PARTIAL_EVIDENCE`, then continue to `SCORING`
    - Append `WorkflowTraceEntry` for each agent start, completion, timeout, and retry
    - Save `AFTER_EVIDENCE` state snapshot via `investigation.save_snapshot()`
    - _Requirements: 4.1, 4.3, 4.8, 4.9, 9.2_

  - [ ]* 10.5 Write property test for post-evidence transition to SCORING
    - **Property 14: Post-Evidence Transition**
    - **Validates: Requirements 4.8**
    - Use `st.builds(AlertPayload)`; assert Investigation always transitions to `SCORING` (via `PARTIAL_EVIDENCE` if applicable) after evidence phase regardless of individual agent outcomes

  - [ ]* 10.6 Write property test for partial evidence mode activation
    - **Property 11: Partial Evidence Mode Activation**
    - **Validates: Requirements 4.3, 13.7**
    - Use `st.integers(1, 2)` for agent failure count; assert `PARTIAL_EVIDENCE` state is set and Investigation reaches a terminal state

  - [ ]* 10.7 Write property test for all-agent failure leading to FAILED
    - **Property 12: All-Agent Failure Leads to FAILED**
    - **Validates: Requirements 4.9**
    - Inject all three agents as always-failing; assert Investigation transitions to `FAILED` and no scoring or remediation occurs

- [ ] 11. Implement Transaction Agent
  - [ ] 11.1 Implement `app/agents/transaction_agent.py`
    - Write `analyze(alert: AlertPayload, fraud_memory: FraudMemoryService) -> TransactionResult`
    - Query Fraud_Memory for matches on `account_id`, device fingerprint, and IP from `alert.metadata`
    - Use Claude Haiku to analyze velocity and behavioral anomaly; parse response into `TransactionResult`
    - Return `TransactionResult` with all required fields: `velocity_score`, `behavioral_anomaly`, `fraud_memory_hit`, `findings_summary`
    - _Requirements: 4.5, 11.3_

  - [ ]* 11.2 Write property test for Transaction Agent schema conformance
    - **Property 10: Agent Output Schema Conformance (Transaction)**
    - **Validates: Requirements 4.5**
    - Use `st.builds(AlertPayload)`; assert returned object is a valid `TransactionResult` with all required fields present and correctly typed

- [ ] 12. Implement KYC Agent
  - [ ] 12.1 Implement `app/agents/kyc_agent.py`
    - Write `analyze(alert: AlertPayload) -> KYCResult` using deterministic rule-based logic (no LLM required)
    - Detect `new_device` from `alert.metadata.device_id` vs account history, `geo_mismatch` from IP geolocation vs account home country, `login_anomaly` from time-of-day patterns
    - Return `KYCResult` with all required fields: `new_device`, `geo_mismatch`, `login_anomaly`, `findings_summary`
    - _Requirements: 4.6_

  - [ ]* 12.2 Write property test for KYC Agent schema conformance
    - **Property 10: Agent Output Schema Conformance (KYC)**
    - **Validates: Requirements 4.6**
    - Use `st.builds(AlertPayload)`; assert returned object is a valid `KYCResult` with all required fields present and correctly typed

- [ ] 13. Implement Sanctions Agent
  - [ ] 13.1 Implement `app/agents/sanctions_agent.py`
    - Write `analyze(alert: AlertPayload) -> SanctionsResult` using Claude Haiku for contextual sanctions reasoning
    - Evaluate `high_risk_corridor` from `recipient_country` against `HIGH_RISK_COUNTRIES`, `country_risk_score` as a float 0–1
    - Return `SanctionsResult` with all required fields: `high_risk_corridor`, `sanctions_hit`, `country_risk_score`, `findings_summary`
    - _Requirements: 4.7_

  - [ ]* 13.2 Write property test for Sanctions Agent schema conformance
    - **Property 10: Agent Output Schema Conformance (Sanctions)**
    - **Validates: Requirements 4.7**
    - Use `st.builds(AlertPayload)`; assert returned object is a valid `SanctionsResult` with all required fields present and correctly typed

- [ ] 14. Implement Risk Scoring Engine
  - [ ] 14.1 Implement `app/services/risk_scoring.py`
    - Write `compute_rule_based_score(tx, kyc, san)` using partial evidence normalization when agents are `None`:
      - Full: `round((velocity×0.4 + new_device×0.3 + high_risk_country×0.3) × 100)`
      - Partial: normalize over sum of available weights only
    - Write `compute_ai_context_score(findings: dict) -> int` using Claude Haiku; parse integer 0–100 from response
    - Write `compute_final_score(rule_based, ai_context) -> int`: `round((rule_based×0.5) + (ai_context×0.5))`
    - Write `build_explanation(tx, kyc, san) -> list[ExplanationEntry]` linking each signal to its `evidence_id`
    - Apply accumulated confidence reductions before returning `RiskResult`
    - Save `AFTER_SCORING` state snapshot
    - _Requirements: 5.1–5.6_

  - [ ]* 14.2 Write property test for risk score formula correctness
    - **Property 15: Risk Score Formula Correctness**
    - **Validates: Requirements 5.1, 5.3**
    - Use `st.floats(0, 1)` for `velocity_score`, `st.booleans()` for `new_device` and `high_risk_country`; assert rule-based and final score formulas hold exactly

  - [ ]* 14.3 Write property test for partial evidence score normalization
    - **Property 16: Partial Evidence Score Normalization**
    - **Validates: Partial Investigation Mode design**
    - Use `st.integers(1, 2)` for number of available agents; assert score is normalized over available weight sum, not 1.0

  - [ ]* 14.4 Write property test for confidence floor application
    - **Property 17: Confidence Floor Application**
    - **Validates: Requirements 5.4**
    - Use `st.floats(0, 3)` for accumulated reductions; assert `confidence >= 0.10` always holds in `RiskResult`

  - [ ]* 14.5 Write property test for risk explanation structure
    - **Property 18: Risk Explanation Structure**
    - **Validates: Requirements 5.6**
    - Use `st.builds(RiskResult)`; assert every `ExplanationEntry` has non-empty `reason` and non-empty `evidence_id`

- [ ] 15. Implement Decision Engine
  - [ ] 15.1 Implement `app/services/decision.py`
    - Write `route_investigation(risk_score: int, confidence: float) -> DecisionRoute` with exact thresholds from design:
      - `score ≤ 70 AND confidence ≥ 0.80` → `AUTO_APPROVE`
      - `score > 70` → `HITL`
      - `50 ≤ score ≤ 70 AND confidence < 0.80` → `HITL`
      - Remaining (score < 50 AND confidence < 0.80) → `AUTO_APPROVE`
    - Record `decision_route` and `THRESHOLDS` dict in the Investigation state for audit
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 15.2 Write property test for decision engine routing correctness
    - **Property 15: Decision Engine Routing Correctness**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Use `st.integers(0, 100)` for score and `st.floats(0, 1)` for confidence; assert every `(score, confidence)` pair produces exactly one deterministic route with no undefined cases

  - [ ]* 15.3 Write property test for decision routing recorded in audit trail
    - **Property 16: Decision Routing Recorded in Audit Trail**
    - **Validates: Requirements 6.4**
    - Use `st.builds(InvestigationState)`; assert `decision_route` and threshold values are present in the audit trail entry after `decision_node` executes

- [ ] 16. Implement Fraud Memory Store
  - [ ] 16.1 Implement `app/services/fraud_memory.py`
    - Write `query(indicator_type: str, indicator_value: str) -> FraudMemoryItem | None` querying `fraud_memory` PostgreSQL table within 200ms
    - Write `store(indicators: list[FraudMemoryItem])` inserting rows with `expires_at = confirmed_at + 365 days`
    - Use `ON CONFLICT (indicator_type, indicator_value) DO UPDATE` for upsert behavior
    - _Requirements: 11.1, 11.3, 11.4_

  - [ ]* 16.2 Write property test for fraud memory integrity
    - **Property 21: Fraud Memory Integrity**
    - **Validates: Requirements 8.4, 11.1, 11.2, 11.4**
    - Use `st.builds(FraudMemoryItem)`; store an item, query by `(indicator_type, indicator_value)`, assert round-trip equality and TTL ≈ `confirmed_at + 365 days`

- [ ] 17. Day 2 Checkpoint — Ensure all tests pass, ask the user if questions arise.

---

### Day 3 — HITL, Resolution, Audit Trail, Observability, Dashboard, Demo Scenarios

- [ ] 18. Implement HITL endpoints and orchestrator pause/resume
  - [ ] 18.1 Implement `POST /api/hitl/{investigation_id}/decision` in `app/api/hitl.py`
    - Validate `X-API-Key` (401) and `X-User-Role: Analyst` (403) using `require_role("Analyst")` dependency
    - Accept body: `decision` (`CONFIRM_FRAUD` | `FALSE_POSITIVE` | `REQUEST_MORE_INFO`), `analyst_id`, `notes`
    - Return HTTP 404 if investigation not found
    - Resume LangGraph orchestrator with the analyst decision
    - Return correct status per decision: `RESOLUTION_IN_PROGRESS`, `CLOSED_FALSE_POSITIVE`, or `AWAITING_HUMAN`
    - _Requirements: 7.3, 7.4, 7.5, 7.6, 7.8, 12.4_

  - [ ] 18.2 Implement HITL timeout handler in `app/services/hitl_timeout.py`
    - Write `check_hitl_timeouts()` that queries investigations in `AWAITING_HUMAN` older than 30 minutes
    - Log `HITL_TIMEOUT` to workflow trace and audit trail; re-notify analyst queue (log to CloudWatch)
    - _Requirements: 7.7_

  - [ ]* 18.3 Write property test for HITL safety invariant
    - **Property 17: HITL Safety Invariant**
    - **Validates: Requirements 7.2**
    - Use `st.builds(InvestigationState)` with `status=AWAITING_HUMAN`; assert `resolution_node` is never invoked and no mock banking endpoints are called

  - [ ]* 18.4 Write property test for HITL decision state transitions
    - **Property 18: HITL Decision State Transitions**
    - **Validates: Requirements 7.4, 7.5, 7.6**
    - Use `st.sampled_from(["CONFIRM_FRAUD", "FALSE_POSITIVE", "REQUEST_MORE_INFO"])`; assert each decision produces exactly the correct state transition with no other terminal states reachable

  - [ ]* 18.5 Write property test for RBAC enforcement
    - **Property 19: Role-Based Access Control Enforcement**
    - **Validates: Requirements 1.2, 7.8, 9.6, 12.4**
    - Use `st.text()` for role values; assert HTTP 403 for any role not in the allowed set, HTTP 401 for missing API key on all protected endpoints

- [ ] 19. Implement Resolution Engine
  - [ ] 19.1 Implement `app/services/resolution.py`
    - Write `execute_remediation(state: InvestigationState) -> list[ActionResult]` calling mock endpoints in strict order: freeze → reverse → block → SMS
    - Each action is independent: on failure, log `ActionResult(status="FAILURE")` to `audit_trail` and continue to next action
    - After all actions complete: call `fraud_memory.store()` with confirmed indicators, transition to `CLOSED_FRAUD_CONFIRMED`
    - Write each `ActionResult` to the `audit_trail` table in PostgreSQL
    - _Requirements: 8.1–8.5, 11.2_

  - [ ]* 19.2 Write property test for resolution engine ordering and resilience
    - **Property 20: Resolution Engine Ordering and Resilience**
    - **Validates: Requirements 8.1, 8.3**
    - Use `st.builds(InvestigationState)` with random single-action failures injected; assert all four actions are always attempted in order and failures are logged without halting

- [ ] 20. Implement Audit Trail service and endpoint
  - [ ] 20.1 Implement `app/services/audit.py`
    - Write `write_audit_trail(state: InvestigationState)` that inserts an `AuditTrailEntry` into the `audit_trail` PostgreSQL table using INSERT only (never UPDATE — immutable)
    - Include full `workflow_trace`, `agent_outputs`, `risk_result`, `decision_route`, `human_decision`, `resolution_actions`, and `explanation` array as JSONB
    - Use millisecond-precision ISO8601 timestamps
    - Write `append_event(investigation_id, event_type, event_data)` for incremental audit entries during workflow execution
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

  - [ ] 20.2 Implement `GET /audit/{investigation_id}` in `app/api/audit.py`
    - Validate `X-API-Key` (401) and `X-User-Role` in `["Analyst", "Auditor"]` (403) using `require_role("Analyst", "Auditor")`
    - Return HTTP 404 for non-existent `investigation_id`
    - Return full `AuditTrailEntry` on success
    - _Requirements: 9.4, 9.6, 12.2, 12.3_

  - [ ]* 20.3 Write property test for audit trail completeness
    - **Property 22: Audit Trail Completeness**
    - **Validates: Requirements 9.1, 9.2, 9.3**
    - Use `st.builds(InvestigationState)` for completed investigations; assert audit trail contains at least one entry per event category (state transitions, agent invocations, decision routing, resolution actions) and every `WorkflowTraceEntry` conforms to schema

  - [ ]* 20.4 Write property test for audit trail retrieval round-trip
    - **Property 23: Audit Trail Retrieval Round-Trip**
    - **Validates: Requirements 9.4**
    - Use `st.builds(InvestigationState)`; write audit trail, retrieve via `GET /audit/{id}`, assert full `explanation` array is present; assert HTTP 404 for random non-existent IDs

  - [ ] 21. Implement investigation status endpoints
  - Implement `GET /investigations` in `app/api/investigations.py` with `?status=` and `?limit=` query params, querying `investigations` table with index on `status`
  - Implement `GET /investigations/{investigation_id}` returning full `InvestigationState` including state snapshots
  - Apply `require_role("Analyst", "Auditor")` dependency to both routes
  - _Requirements: 10.3, 12.2, 12.3_

- [ ] 22. Implement observability
  - [ ] 22.1 Implement structured logging in `app/core/observability.py`
    - Write `log_investigation_event(state: InvestigationState, event: str)` emitting structured JSON to stdout/file with all required fields: `investigation_id`, `status`, `risk_score`, `confidence`, `retry_count`, `investigation_duration_ms`
    - _Requirements: 10.1_

  - [ ] 22.2 Implement metrics tracking
    - Write `increment_metric(metric_name: str)` that updates in-memory counters for: `InvestigationsStarted`, `AutoClosed`, `EscalatedToHITL`, `FraudConfirmed`, `FalsePositives`
    - Expose metrics via `GET /metrics` endpoint for dashboard polling
    - Call from the appropriate LangGraph nodes (`close_node`, `hitl_node`, `resolution_node`)
    - _Requirements: 10.2_

  - [ ]* 22.3 Write property test for log structure
    - **Property 29: CloudWatch Log Structure**
    - **Validates: Requirements 10.1**
    - Use `st.builds(InvestigationState)`; assert every emitted log entry contains all 6 required fields with no null values

- [ ] 23. Implement Streamlit dashboard
  - [ ] 23.1 Create `dashboard/app.py` as a standalone Streamlit application
    - Display active investigations table: `investigation_id`, `status`, `risk_score`, `confidence`, `priority`, `created_at`
    - Display per-investigation detail view: lifecycle state, risk score gauge, confidence score, agent timeline from `workflow_trace`, per-agent latency bar chart
    - Display state evolution panel: show `StateSnapshot` for each stage (`AFTER_TRIAGE`, `AFTER_EVIDENCE`, `AFTER_SCORING`, `AFTER_DECISION`, `AFTER_RESOLUTION`) as a step-by-step progression with risk score and confidence at each stage
    - Highlight `PARTIAL_EVIDENCE` investigations with a visual indicator showing which agents contributed vs failed
    - Poll `GET /investigations?status=ACTIVE` every 5 seconds using `st.rerun()` with `time.sleep(5)`
    - _Requirements: 10.3, 10.4_

- [ ] 24. Implement end-to-end demo scenarios as integration tests
  - [ ] 24.1 Write Scenario A integration test: "The Midnight Mule"
    - In `tests/test_scenarios.py`, write `test_midnight_mule()` that submits `{amount: 2500, country: "NG", timestamp: 2:15 AM}`
    - Assert: triage → `P1_CRITICAL`, agents run in parallel, risk score ≈ 92, routed to HITL, analyst submits `CONFIRM_FRAUD`, all 4 remediation actions execute, final status `CLOSED_FRAUD_CONFIRMED`, fraud memory updated
    - Assert total elapsed time (excluding HITL wait) < 4 minutes
    - _Requirements: 13.1, 8.1, 8.4_

  - [ ] 24.2 Write Scenario B integration test: "Legitimate Tuition Payment"
    - Write `test_tuition_payment()` that submits `{amount: 2500, country: "US", known_device: true}`
    - Assert: triage → `P2_STANDARD`, risk score ≈ 18, routed to `AUTO_APPROVE`, final status `CLOSED_FALSE_POSITIVE`, no remediation actions, total elapsed < 10 seconds
    - _Requirements: 13.2, 6.1_

  - [ ] 24.3 Write Resilience Demo integration test: Sanctions Agent timeout
    - Write `test_sanctions_timeout()` that injects a consistently-failing Sanctions Agent mock
    - Assert: 3 retry attempts with exponential backoff, `confidence` reduced from 0.95 → 0.65, `sanctions_result=None`, workflow reaches terminal state (not `FAILED`), `SANCTIONS_AGENT_TIMEOUT` in `workflow_trace`
    - _Requirements: 4.2, 4.3, 13.7_

  - [ ]* 24.4 Write property test for partial evidence resilience
    - **Property 25: Partial Evidence Resilience**
    - **Validates: Requirements 13.7**
    - Use `st.integers(0, 2)` for agent failure count (0–2 agents fail); assert Investigation always reaches a terminal state when at least one agent succeeds; `FAILED` only when all three agents fail

- [ ] 25. Final checkpoint — Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with the `ci` profile (100 iterations minimum)
- Every property test must include the tag comment: `# Feature: agentic-fraud-investigator, Property {N}: {title}`
- All banking integrations (freeze, reverse, block, SMS) are mocked — no real payment rails
- PostgreSQL can be run locally via Docker: `docker run -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:16`
- The Streamlit dashboard (`dashboard/app.py`) is a separate process from the FastAPI app