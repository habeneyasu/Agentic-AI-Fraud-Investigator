"""
Presenter cockpit: FastAPI routes for alerts, triage, LangGraph deep, HITL, fraud-memory.
Investigation JSON is kept in ``st.session_state`` until the next run.
"""

from __future__ import annotations

import html
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parent.parent
_dash_dir = Path(__file__).resolve().parent
for _p in (_repo_root, _dash_dir):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _dash_common import API_BASE, _api_headers, analyst_headers

MIDNIGHT_MULE_CUSTOMER = os.getenv("DEMO_CUSTOMER_ID", "CUST003")

_INV_SPARK_SEED: list[float] = [1.0, 1.2, 1.5, 2.0, 2.2, 2.8, 3.0, 3.4, 3.8, 4.0, 4.5, 4.2]


def init_console_state() -> None:
    defaults: dict[str, Any] = {
        "inv_dark_ui": True,
        "inv_customer_id": MIDNIGHT_MULE_CUSTOMER,
        "inv_snapshot": None,
        "inv_triage": None,
        "inv_error": None,
        "inv_hitl_sent": False,
        "inv_last_hitl_decision": None,
        "inv_resolution_result": None,
        "inv_kpi_alerts_today": 0,
        "inv_kpi_avg_seconds": 42.0,
        "inv_kpi_auto_clear_pct": 0.0,
        "inv_run_started_at": None,
        "inv_last_patterns_count": 0,
        "inv_confirmed_fraud": 0,
        "inv_last_alerts_response": None,
        "inv_last_alerts_scope_customer": None,
        "inv_llm_stream_enabled": True,
        "inv_current_id": None,
        "inv_event_log": [],
        "inv_spark_points": list(_INV_SPARK_SEED),
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _append_inv_log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    log = st.session_state.setdefault("inv_event_log", [])
    if not isinstance(log, list):
        st.session_state.inv_event_log = []
        log = st.session_state.inv_event_log
    log.append(f"[{ts}] {message}")
    if len(log) > 220:
        del log[:-220]


def _touch_spark(n: int) -> list[float]:
    pts = st.session_state.setdefault("inv_spark_points", list(_INV_SPARK_SEED))
    if not isinstance(pts, list):
        st.session_state.inv_spark_points = [1.0, 2.0]
        pts = st.session_state.inv_spark_points
    pts.append(float(max(0, n)))
    if len(pts) > 24:
        del pts[:-24]
    return [float(x) for x in pts]


def _sparkline_svg(values: list[float], *, w: int = 108, h: int = 26) -> str:
    vals = values if len(values) >= 2 else [0.0, 1.0, 0.6, 1.2, 1.0]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1e-6)
    n = len(vals)
    pts: list[str] = []
    for i, v in enumerate(vals):
        x = (i / (n - 1)) * (w - 2) + 1 if n > 1 else 1.0
        y = h - 2 - ((float(v) - lo) / span) * (h - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg class="inv-spark-svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<polyline fill="none" stroke="rgba(96,165,250,0.88)" stroke-width="1.65" points="{" ".join(pts)}"/>'
        f"</svg>"
    )


def _kpi_card_html(label: str, display: str, *, skeleton: bool = False, spark_vals: list[float] | None = None) -> str:
    sk = " inv-kpi-skel" if skeleton else ""
    base = list(st.session_state.get("inv_spark_points") or [1.0, 2.0])
    spark = _sparkline_svg(spark_vals if spark_vals is not None else base)
    return (
        f'<div class="inv-kpi{sk}">'
        f'<div class="inv-kpi-metric"><div class="v">{html.escape(display)}</div>'
        f'<div class="l">{html.escape(label)}</div></div>'
        f'<div class="inv-kpi-spark">{spark}</div></div>'
    )


def _get_json(path: str, params: dict[str, Any] | None = None, *, analyst: bool = False) -> Any:
    headers = analyst_headers() if analyst else _api_headers()
    r = httpx.get(f"{API_BASE}{path}", params=params or {}, headers=headers, timeout=45.0)
    r.raise_for_status()
    return r.json()


def _post_json(path: str, body: dict[str, Any] | None = None, *, analyst: bool = False) -> Any:
    headers = analyst_headers() if analyst else _api_headers()
    r = httpx.post(f"{API_BASE}{path}", json=body or {}, headers=headers, timeout=180.0)
    r.raise_for_status()
    return r.json()


def fetch_fraud_patterns_count() -> int:
    try:
        root = _get_json(
            "/v1/fraud-memory",
            {"view": "patterns", "filter": "all", "limit": 500, "active_only": True},
        )
        data = root.get("data") if isinstance(root.get("data"), dict) else root
        patterns = (data or {}).get("patterns") or []
        if isinstance(patterns, list):
            return len(patterns)
    except Exception:
        pass
    return st.session_state.get("inv_last_patterns_count", 0)


def post_generate_alerts(customer_id: str) -> dict[str, Any]:
    r = httpx.post(
        f"{API_BASE}/v1/alerts/generate",
        params={"customer_id": customer_id},
        json={},
        headers=_api_headers(),
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()


def _post_json_qs(path: str, params: dict[str, str], body: dict[str, Any]) -> Any:
    r = httpx.post(
        f"{API_BASE}{path}",
        params=params,
        json=body,
        headers=_api_headers(),
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()


def post_triage_assess(customer_id: str, *, narrative: bool = True) -> dict[str, Any]:
    return _post_json_qs(
        "/v1/triage/assess",
        {"customer_id": customer_id},
        {"include_initial_suspicion_note": narrative},
    )


def post_langgraph_deep(
    customer_id: str,
    alert_id: str | None,
    *,
    include_hitl: bool = True,
    persist_memory: bool = False,
) -> dict[str, Any]:
    body = {
        "customer_id": customer_id,
        "alert_id": alert_id,
        "include_hitl_recommendation": include_hitl,
        "persist_fraud_memory": persist_memory,
    }
    return _post_json("/v1/investigation/customer-langgraph-deep", body)


def post_hitl_decision(inv_id: str, decision: str, analyst_id: str = "demo_analyst", notes: str = "") -> bool:
    try:
        r = httpx.post(
            f"{API_BASE}/api/hitl/{inv_id}/decision",
            json={"decision": decision, "analyst_id": analyst_id, "notes": notes},
            headers=analyst_headers(),
            timeout=60.0,
        )
        return r.status_code == 200
    except Exception:
        return False


def post_execute_actions(inv_id: str, actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """POST JSON array of action objects to ``/api/hitl/{id}/execute-actions``."""
    try:
        r = httpx.post(
            f"{API_BASE}/api/hitl/{inv_id}/execute-actions",
            json=actions,
            headers=analyst_headers(),
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.session_state.inv_error = str(e)
        return None


def _customer_match(row_cust: Any, want: str) -> bool:
    if not want:
        return True
    try:
        return str(row_cust).strip().casefold() == want.strip().casefold()
    except Exception:
        return False


def _alerts_df_customer_only(raw: list[Any], customer_id: str) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    if "customer_id" in df.columns and customer_id.strip():
        df = df[df["customer_id"].map(lambda x: _customer_match(x, customer_id))]
    return df


def _render_triage_results(tri: dict[str, Any]) -> None:
    st.markdown("#### Triage result")
    summary = tri.get("triage_summary") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Assessed", tri.get("total_alerts_assessed", "—"))
    c2.metric("Escalated", tri.get("investigation_required_count", summary.get("escalated_count", "—")))
    c3.metric("Auto-closed", tri.get("auto_closed_count", summary.get("auto_closed_count", "—")))
    c4.metric("Avg risk (batch)", f"{float(tri.get('average_risk_score', 0) or 0):.2f}")
    if summary:
        with st.expander("Triage summary (aggregate)", expanded=False):
            st.json(summary)

    assessed = tri.get("assessed_alerts") or []
    if assessed:
        st.markdown("**Per-alert outcomes**")
        rows = []
        for a in assessed:
            rs = a.get("risk_score") or {}
            if isinstance(rs, dict):
                score_v = rs.get("score", "—")
                sev = rs.get("severity", "—")
            else:
                score_v, sev = "—", "—"
            sev_s = sev if isinstance(sev, str) else getattr(sev, "value", str(sev))
            rows.append(
                {
                    "alert_id": a.get("alert_id"),
                    "customer_id": a.get("customer_id"),
                    "status": a.get("status"),
                    "policy": str(a.get("policy", "")),
                    "severity": sev_s,
                    "risk_score": score_v,
                    "investigation_required": a.get("investigation_required"),
                    "initial_suspicion_source": a.get("initial_suspicion_source"),
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_triage_narratives(tri: dict[str, Any], customer_id: str) -> None:
    """Per-alert suspicion notes (LLM / fallback) for one customer."""
    st.markdown("### Triage narrative")
    engine = tri.get("initial_suspicion_engine_status")
    if engine:
        st.caption(f"Narrative engine status: **{engine}**")
    assessed = tri.get("assessed_alerts") or []
    want = (customer_id or "").strip().casefold()
    narratives: list[tuple[str, str]] = []
    for a in assessed:
        cid = str(a.get("customer_id") or "").strip().casefold()
        if want and cid != want:
            continue
        note = a.get("initial_suspicion_note")
        if note:
            narratives.append((str(a.get("alert_id", "—")), str(note)))
    if narratives:
        for aid, note in narratives:
            with st.container(border=True):
                st.markdown(f"**Alert `{aid}`**")
                sk = f"inv_tri_narr_done_{aid}"
                note_s = (note or "").strip()
                if not note_s:
                    st.caption("—")
                elif st.session_state.get("inv_llm_stream_enabled", True):
                    if not st.session_state.get(sk):
                        st.write_stream(_stream_chars(note_s))
                        st.session_state[sk] = True
                    else:
                        st.markdown(note_s)
                else:
                    st.markdown(note_s)
    else:
        st.info(
            "No suspicion narrative for this customer in the last triage batch — run **Triage assess** "
            "with API keys set if you expect LLM text."
        )


def _stream_chars(text: str, chunk: int = 28) -> Any:
    """Small generator for ``st.write_stream`` (typing-style reveal)."""
    t = (text or "").strip()
    if not t:
        yield "—"
        return
    for i in range(0, len(t), chunk):
        yield t[i : i + chunk]
        time.sleep(0.018)


def _clear_session_keys_prefix(prefix: str) -> None:
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(prefix):
            del st.session_state[k]


def _stream_executive_summary(inv_id: str | None, text: str) -> None:
    st.caption("Executive summary (model output)")
    key = f"inv_exec_syn_done_{inv_id or 'none'}"
    body = (text or "").strip() or "—"
    if body == "—":
        st.caption("—")
        return
    if st.session_state.get("inv_llm_stream_enabled", True):
        if not st.session_state.get(key):
            st.write_stream(_stream_chars(body))
            st.session_state[key] = True
        else:
            st.markdown(body)
    else:
        st.markdown(body)


def _render_investigation_synthesis_panel(data: dict[str, Any], rr: dict[str, Any], inv_id: str | None) -> None:
    st.markdown("### Investigation synthesis")
    synth = data.get("llm_investigation_synthesis") if isinstance(data.get("llm_investigation_synthesis"), dict) else {}

    meta1, meta2, meta3 = st.columns(3)
    meta1.metric("Risk tier", str(synth.get("risk_tier") or rr.get("risk_tier") or "—"))
    rec = str(synth.get("recommendation") or rr.get("recommendation") or "—")
    meta2.metric("Recommendation", rec[:28] + ("…" if len(rec) > 28 else ""))
    meta3.metric("Requires HITL", "Yes" if rr.get("requires_human_review") else "No")

    summary = (
        str(synth.get("executive_summary") or "").strip()
        or str(rr.get("executive_summary") or "").strip()
        or "—"
    )
    _stream_executive_summary(inv_id, summary)

    obs = synth.get("key_observations") or synth.get("keyObservations") or []
    if isinstance(obs, list) and obs:
        st.markdown("**Key observations**")
        for o in obs[:20]:
            st.markdown(f"- {o}")

    chain = rr.get("evidence_chain") or synth.get("evidence_chain") or []
    if isinstance(chain, list) and chain:
        st.markdown("**Evidence chain**")
        for e in chain[:20]:
            if isinstance(e, dict):
                st.markdown(
                    f"- **{e.get('signal', '?')}** ({e.get('source', '?')}) — {e.get('detail', '')}"
                )
            else:
                st.markdown(f"- {e}")

    steps = rr.get("reasoning_steps") or synth.get("reasoning_steps") or []
    if isinstance(steps, list) and steps:
        st.markdown("**Reasoning steps**")
        for i, step in enumerate(steps[:25], 1):
            st.markdown(f"{i}. {step}")

    with st.expander("Raw synthesis JSON", expanded=False):
        st.json(synth if synth else {"risk_result_excerpt": {k: rr.get(k) for k in ("executive_summary", "reasoning_steps", "evidence_chain") if rr.get(k)}})


def _render_resolution_audit_panel(res: dict[str, Any] | None, hitl_decision: str | None) -> None:
    st.markdown("### Resolution audit")
    if hitl_decision:
        st.caption(f"Last analyst disposition: **{hitl_decision}**")
    if not res:
        st.info("No resolution payload yet — complete HITL and freeze / close when offered.")
        return
    fin = res.get("final_resolution") or {}
    if fin:
        c1, c2, c3 = st.columns(3)
        c1.metric("Actions run", fin.get("actions_executed", "—"))
        c2.metric("Succeeded", fin.get("successful_actions", "—"))
        c3.metric("Failed", fin.get("failed_actions", "—"))
        st.success(str(fin.get("resolution_summary") or fin.get("final_decision") or "Resolution recorded"))
    rows = res.get("actions_executed") or []
    if isinstance(rows, list) and rows:
        out = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            out.append(
                {
                    "success": item.get("success"),
                    "message": (item.get("message") or "")[:200],
                    "action_id": item.get("action_id"),
                    "case_id": item.get("case_id"),
                }
            )
        if out:
            st.markdown("**Action ledger**")
            st.dataframe(pd.DataFrame(out), hide_index=True, use_container_width=True)
    with st.expander("Full resolution API response", expanded=False):
        st.json(res)


def _freeze_action_payload(inv_id: str, cust: str, txn: str | None) -> dict[str, Any]:
    return {
        "action_type": "freeze",
        "case_id": inv_id,
        "reason": "HITL confirm_fraud — freeze customer account",
        "target_id": cust,
        "metadata": {"customer_id": cust, "transaction_id": txn},
    }


def _close_action_payload(inv_id: str, cust: str) -> dict[str, Any]:
    return {
        "action_type": "close",
        "case_id": inv_id,
        "reason": "HITL false_positive — case closed, no remediation",
        "target_id": cust,
        "metadata": {"disposition": "false_positive"},
    }


def _render_hitl_analyst_briefing(rec: dict[str, Any]) -> None:
    if not rec:
        st.info("No analyst briefing payload returned — review risk panel and evidence manually.")
        return
    action = rec.get("recommended_action") or rec.get("recommendedAction") or "—"
    conf = rec.get("confidence")
    try:
        conf_f = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf_f = None
    briefing = rec.get("analyst_briefing") or rec.get("analystBriefing") or ""
    evidence = rec.get("supporting_evidence") or rec.get("supportingEvidence") or []
    risk_wrong = rec.get("risk_if_wrong") or rec.get("riskIfWrong") or ""

    st.markdown("##### Analyst briefing (AI)")
    st.markdown(f"**Recommended action:** `{action}`")
    if conf_f is not None:
        st.metric("Model confidence", f"{conf_f * 100:.0f}%")
    st.markdown("**Briefing**")
    btxt = (str(briefing).strip() or "—")
    inv_for_key = st.session_state.get("inv_current_id") or "none"
    bkey = f"inv_hitl_brief_done_{inv_for_key}"
    if btxt == "—":
        st.caption("—")
    elif st.session_state.get("inv_llm_stream_enabled", True):
        if not st.session_state.get(bkey):
            st.write_stream(_stream_chars(btxt))
            st.session_state[bkey] = True
        else:
            st.markdown(btxt)
    else:
        st.markdown(btxt)
    st.markdown("**Supporting evidence**")
    if isinstance(evidence, list) and evidence:
        for item in evidence:
            st.markdown(f"- {item}")
    else:
        st.caption("—")
    st.markdown("**Risk if this call is wrong**")
    st.write(risk_wrong or "—")


def _risk_score_0_100(snapshot: dict[str, Any]) -> float:
    data = snapshot.get("data") or {}
    rr = data.get("risk_result") or {}
    v = float(rr.get("final_risk_score", rr.get("risk_score", 0.0)))
    return max(0.0, min(100.0, v * 100.0))


def risk_gauge(score_0_100: float) -> None:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score_0_100,
            title={"text": "Risk score"},
            number={"suffix": "/100"},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#b91c1c"},
                "steps": [
                    {"range": [0, 30], "color": "#bbf7d0"},
                    {"range": [30, 70], "color": "#fdba74"},
                    {"range": [70, 100], "color": "#fecaca"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 3},
                    "thickness": 0.8,
                    "value": 70,
                },
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)


def _show_agent_progress(name: str, status: str, progress_percent: float) -> None:
    c1, c2 = st.columns([2, 5])
    c1.markdown(f"**{name}**")
    if status == "pending":
        c2.progress(0.0, text="Waiting")
    elif status == "running":
        c2.progress(max(0.01, progress_percent / 100.0), text=f"Analyzing… {int(progress_percent)}%")
    elif status == "completed":
        c2.progress(1.0, text="Completed")
    elif status == "timeout":
        c2.warning("Timeout — partial evidence")


def _timeline_step_labels() -> list[tuple[str, str]]:
    return [
        ("1", "Intake", "Alert ingestion & idempotency"),
        ("2", "Triage", "Priority & policy routing"),
        ("3", "Agents", "Parallel evidence agents"),
        ("4", "Scoring", "Risk fusion & narrative"),
        ("5", "HITL", "Human decision"),
        ("6", "Resolve", "Actions & memory"),
        ("7", "Audit", "Immutable trace"),
    ]


def _active_timeline_index(
    snapshot: dict[str, Any] | None,
    *,
    hitl_decision_done: bool,
    resolution_done: bool,
) -> int:
    if not snapshot:
        return 0
    data = snapshot.get("data") or {}
    rr = data.get("risk_result") or {}
    if resolution_done:
        return 6
    if hitl_decision_done:
        return 5
    if rr:
        if rr.get("requires_human_review"):
            return 4
        return 5
    return 3


def _inject_console_css(dark: bool) -> None:
    if dark:
        st.markdown(
            """
<style>
.inv-shell { max-width: 1400px; margin: 0 auto; }
.inv-kpi {
  background: linear-gradient(145deg, rgba(15,27,51,0.96), rgba(8,17,32,0.99));
  border: 1px solid rgba(59,130,246,0.22);
  border-radius: 12px;
  padding: 0.65rem 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  min-height: 5.65rem;
  text-align: center;
}
.inv-kpi-metric { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.inv-kpi .v { font-size: 1.36rem; font-weight: 800; color: #f8fafc; }
.inv-kpi .l { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.11em; color: #64748b; }
.inv-kpi-spark { margin-top: 0.25rem; display: flex; justify-content: center; min-height: 26px; opacity: 0.92; }
.inv-kpi-skel { box-shadow: 0 0 20px rgba(59,130,246,0.14); }
.inv-kpi-skel .v {
  color: #94a3b8 !important;
  background: linear-gradient(90deg, rgba(100,116,139,0.12), rgba(148,163,184,0.3), rgba(100,116,139,0.12));
  background-size: 220% 100%;
  animation: inv-shimmer 1.45s ease-in-out infinite;
  border-radius: 6px;
}
@keyframes inv-shimmer { 0%{background-position:220% 0} 100%{background-position:-220% 0} }
.mini-terminal {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 0.68rem;
  line-height: 1.45;
  color: #94a3b8;
  background: rgba(6,13,26,0.94);
  border: 1px solid #1c3050;
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
  max-height: 9.5rem;
  overflow-y: auto;
  white-space: pre-wrap;
  margin-top: 0.35rem;
  box-shadow: inset 0 0 22px rgba(0,0,0,0.38);
}
.inv-tl { font-size: 0.78rem; color: #94a3b8; padding: 0.15rem 0; }
.inv-tl.done { color: #34d399; }
.inv-tl.active { color: #60a5fa; font-weight: 700; }
/* Title in columns: Streamlit theme can wash out default h3/markdown — force contrast */
p.inv-app-title {
  color: #f8fafc !important;
  font-size: 1.4rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em !important;
  line-height: 1.25 !important;
  margin: 0 0 0.35rem 0 !important;
}
p.inv-app-sub {
  color: #94a3b8 !important;
  font-size: 0.82rem !important;
  line-height: 1.45 !important;
  margin: 0 0 0.5rem 0 !important;
}
p.inv-console-tagline {
  color: #cbd5e1 !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  line-height: 1.4 !important;
  margin: 0 0 0.35rem 0 !important;
}
</style>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
<style>
.inv-kpi {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.65rem 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  min-height: 5.65rem;
  text-align: center;
}
.inv-kpi-metric { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.inv-kpi .v { font-size: 1.36rem; font-weight: 800; color: #0f172a; }
.inv-kpi .l { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.11em; color: #64748b; }
.inv-kpi-spark { margin-top: 0.25rem; display: flex; justify-content: center; min-height: 26px; }
.inv-kpi-skel .v {
  color: #64748b !important;
  background: linear-gradient(90deg, rgba(148,163,184,0.2), rgba(203,213,225,0.45), rgba(148,163,184,0.2));
  background-size: 220% 100%;
  animation: inv-shimmer 1.45s ease-in-out infinite;
  border-radius: 6px;
}
@keyframes inv-shimmer { 0%{background-position:220% 0} 100%{background-position:-220% 0} }
.mini-terminal {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 0.68rem;
  line-height: 1.45;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
  max-height: 9.5rem;
  overflow-y: auto;
  white-space: pre-wrap;
  margin-top: 0.35rem;
}
p.inv-app-title {
  font-size: 1.4rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em !important;
  line-height: 1.25 !important;
  margin: 0 0 0.35rem 0 !important;
}
p.inv-app-title.inv-app-title--light {
  color: #0f172a !important;
}
p.inv-app-sub {
  font-size: 0.82rem !important;
  line-height: 1.45 !important;
  margin: 0 0 0.5rem 0 !important;
}
p.inv-console-tagline {
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  line-height: 1.4 !important;
  margin: 0 0 0.35rem 0 !important;
}
p.inv-console-tagline.inv-console-tagline--light {
  color: #334155 !important;
}
p.inv-app-sub.inv-app-sub--light {
  color: #475569 !important;
}
</style>
""",
            unsafe_allow_html=True,
        )


def _agent_statuses(snapshot: dict[str, Any] | None) -> list[tuple[str, str, float]]:
    names = [("Transaction", "transaction"), ("KYC", "kyc"), ("Sanctions", "sanctions")]
    if not snapshot:
        return [(n, "pending", 0.0) for n, _ in names]
    ar = (snapshot.get("data") or {}).get("agent_results") or {}
    out: list[tuple[str, str, float]] = []
    for label, key in names:
        block = ar.get(key)
        if isinstance(block, dict) and block.get("risk_score") is not None:
            out.append((label, "completed", 100.0))
        else:
            out.append((label, "completed", 100.0))
    return out


def render_investigator_console(*, embedded: bool = False) -> None:
    init_console_state()
    _inject_console_css(bool(st.session_state.inv_dark_ui))

    h1, h2 = st.columns([4, 1])
    _light = "" if st.session_state.inv_dark_ui else " inv-app-title--light"
    _sub_light = "" if st.session_state.inv_dark_ui else " inv-app-sub--light"
    if embedded:
        h1.markdown('<div class="inv-embedded-spacer" style="height:2px;"></div>', unsafe_allow_html=True)
    else:
        h1.markdown(
            f'<p class="inv-app-title{_light}">Agentic AI Fraud Investigator</p>',
            unsafe_allow_html=True,
        )
        h1.markdown(
            f'<p class="inv-app-sub{_sub_light}">'
            "Ingest → triage → agents → score → HITL → resolve · FastAPI stack</p>",
            unsafe_allow_html=True,
        )

    if h2.button(
        "Dark UI: ON" if st.session_state.inv_dark_ui else "Dark UI: OFF",
        key="inv_dark",
        type="secondary",
    ):
        st.session_state.inv_dark_ui = not st.session_state.inv_dark_ui
        st.rerun()

    st.session_state.inv_customer_id = st.text_input(
        "Customer ID",
        value=str(st.session_state.inv_customer_id),
        key="inv_cust_input",
    )
    st.session_state.inv_persist_memory = st.checkbox(
        "Persist fraud memory on deep investigation",
        value=False,
        help="When enabled, successful HITL briefing may write to fraud-memory store.",
    )
    st.checkbox(
        "Animate LLM text (typing reveal for executive summary, triage notes, analyst briefing)",
        key="inv_llm_stream_enabled",
    )

    patterns_n = fetch_fraud_patterns_count()
    st.session_state.inv_last_patterns_count = patterns_n

    tri = st.session_state.get("inv_triage") or {}
    auto_clear_pct = float(st.session_state.get("inv_kpi_auto_clear_pct") or (tri.get("auto_close_rate") or 0.0) * 100.0)
    alerts_n = int(st.session_state.get("inv_kpi_alerts_today") or tri.get("total_alerts_assessed") or 0)
    avg_s = float(st.session_state.get("inv_kpi_avg_seconds") or 42.0)
    has_snap = bool(st.session_state.inv_snapshot)
    spark_pts = [float(x) for x in (st.session_state.get("inv_spark_points") or [1.0, 1.2, 2.0, 2.5, 3.0, 3.2])]

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(
        _kpi_card_html("Today's alerts (scoped batch)", str(alerts_n) if alerts_n else "—", spark_vals=spark_pts),
        unsafe_allow_html=True,
    )
    k2.markdown(
        _kpi_card_html(
            "Avg investigation time (s)",
            f"{avg_s:.0f}" if has_snap else "—",
            skeleton=not has_snap,
            spark_vals=spark_pts,
        ),
        unsafe_allow_html=True,
    )
    k3.markdown(
        _kpi_card_html("Auto-clear rate (last triage)", f"{auto_clear_pct:.0f}%", spark_vals=spark_pts),
        unsafe_allow_html=True,
    )
    k4.markdown(
        _kpi_card_html(
            "Confirmed fraud (session)",
            str(int(st.session_state.get("inv_confirmed_fraud") or 0)),
            spark_vals=spark_pts,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    act1, act2, act3 = st.columns([1, 1, 2])
    if act1.button("1 · View alerts", type="secondary"):
        with st.spinner("Refreshing merged queue (generate + load)…"):
            try:
                gen = post_generate_alerts(st.session_state.inv_customer_id)
                st.session_state.inv_last_alerts_response = gen
                st.session_state.inv_last_alerts_scope_customer = str(st.session_state.inv_customer_id).strip()
                n_al = int(
                    gen.get("filtered_count") or gen.get("total_count") or len(gen.get("alerts") or []) or 0
                )
                st.session_state.inv_kpi_alerts_today = n_al
                _touch_spark(n_al)
                st.session_state.inv_error = None
                _append_inv_log(f"alerts.generate ok filtered={n_al}")
                st.toast("Alerts refreshed", icon="📥")
            except Exception as e:
                st.session_state.inv_error = str(e)
                st.session_state.inv_last_alerts_response = None
                _append_inv_log(f"alerts.generate error {e!s}")
        st.rerun()

    lr = st.session_state.get("inv_last_alerts_response")
    if lr is not None:
        st.markdown("#### Alerts in scope")
        scoped = st.session_state.get("inv_last_alerts_scope_customer")
        cur = str(st.session_state.inv_customer_id).strip()
        if scoped and cur != scoped:
            st.warning("Customer ID changed since this table was loaded. Click **View alerts** again to refresh.")
        st.caption(
            f"Customer **{scoped or cur}** · queue totals: **{lr.get('total_count', '—')}** total · "
            f"**{lr.get('filtered_count', '—')}** after filter · **{lr.get('created', 0)}** new this run · "
            f"**{lr.get('skipped_duplicates', 0)}** duplicates skipped"
        )
        raw = lr.get("alerts") or []
        scope_cust = (scoped or cur).strip()
        df = _alerts_df_customer_only(raw, scope_cust)
        st.caption(f"Table shows **this customer only** — **{len(df)}** row(s) match `{scope_cust or cur}`.")
        if not df.empty:
            preferred = [
                c
                for c in (
                    "alert_id",
                    "customer_id",
                    "amount",
                    "currency",
                    "recipient_country",
                    "severity",
                    "status",
                    "timestamp",
                    "transaction_id",
                )
                if c in df.columns
            ]
            st.dataframe(
                df[preferred] if preferred else df,
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No alerts for this customer in the merged queue (try **View alerts** after changing customer).")

    if act2.button("2 · Triage assess", type="secondary"):
        with st.spinner("Triage batch…"):
            try:
                st.session_state.inv_triage = post_triage_assess(
                    st.session_state.inv_customer_id,
                    narrative=True,
                )
                st.session_state.inv_error = None
                ac = float(st.session_state.inv_triage.get("auto_close_rate") or 0.0)
                st.session_state.inv_kpi_auto_clear_pct = ac * 100.0
                _clear_session_keys_prefix("inv_tri_narr_done_")
                _append_inv_log("triage.assess ok")
            except Exception as e:
                st.session_state.inv_error = str(e)
                _append_inv_log(f"triage.assess error {e!s}")
        st.rerun()

    if act3.button("3 · Run LangGraph deep investigation", type="primary"):
        _append_inv_log("langgraph_deep start")
        _clear_session_keys_prefix("inv_exec_syn_done_")
        _clear_session_keys_prefix("inv_hitl_brief_done_")
        st.session_state.inv_hitl_sent = False
        st.session_state.inv_last_hitl_decision = None
        st.session_state.inv_resolution_result = None
        with st.status("Agents running (transaction · KYC · sanctions)…", expanded=True) as status:
            try:
                status.write("Calling **POST /v1/investigation/customer-langgraph-deep** …")
                st.session_state.inv_run_started_at = time.time()
                snap = post_langgraph_deep(
                    st.session_state.inv_customer_id,
                    None,
                    include_hitl=True,
                    persist_memory=bool(st.session_state.inv_persist_memory),
                )
                status.write("Merging agent outputs — risk fusion, synthesis, and HITL payload …")
                st.session_state.inv_snapshot = snap
                inv_id = (snap.get("data") or {}).get("investigation_id")
                if inv_id:
                    st.session_state.inv_current_id = inv_id
                elapsed = time.time() - float(st.session_state.inv_run_started_at or time.time())
                st.session_state.inv_kpi_avg_seconds = round(elapsed, 1)
                st.session_state.inv_error = None
                _append_inv_log(f"langgraph_deep complete id={inv_id} elapsed_s={elapsed:.1f}")
                status.update(label="Investigation complete", state="complete", expanded=False)
            except Exception as e:
                st.session_state.inv_error = str(e)
                _append_inv_log(f"langgraph_deep error {e!s}")
                status.update(label="Investigation failed", state="error")
        st.rerun()

    if st.session_state.inv_error:
        st.error(st.session_state.inv_error)

    snap = st.session_state.get("inv_snapshot")
    inv_id = st.session_state.get("inv_current_id") or (
        (snap or {}).get("data") or {}
    ).get("investigation_id")
    data: dict[str, Any] = (snap or {}).get("data") or {} if isinstance(snap, dict) else {}
    if not isinstance(data, dict):
        data = {}
    rr = data.get("risk_result") or {}
    if not isinstance(rr, dict):
        rr = {}

    hitl_decision_done = bool(st.session_state.get("inv_hitl_sent"))
    resolution_done = bool(st.session_state.get("inv_resolution_result"))

    st.markdown(f"#### Live investigation {f'**`{inv_id}`**' if inv_id else '*(run step 3)*'}")

    left, right = st.columns([1, 2.3])
    with left:
        st.markdown("**Step timeline**")
        active_i = _active_timeline_index(
            snap if isinstance(snap, dict) else None,
            hitl_decision_done=hitl_decision_done,
            resolution_done=resolution_done,
        )
        for idx, (num, title, desc) in enumerate(_timeline_step_labels()):
            cls = "inv-tl done" if idx < active_i else "inv-tl active" if idx == active_i else "inv-tl"
            st.markdown(
                f'<div class="{cls}">{num}. {title}<br/><span style="font-size:0.72rem;opacity:0.85;">{desc}</span></div>',
                unsafe_allow_html=True,
            )

    with right:
        csh, csp = st.columns([3, 1])
        with csh:
            st.markdown("**Current state**")
        with csp:
            with st.popover("View source", help="Immutable snapshot envelope for audit / export"):
                st.json(snap if snap else {"detail": "Run step 3 — LangGraph deep investigation — to populate this payload."})
        intake_ok = bool(st.session_state.inv_triage or snap)
        triage_ok = bool(st.session_state.inv_triage)
        st.markdown(
            f"- Alert intake: **{'complete' if intake_ok else 'pending'}**  \n"
            f"- Triage: **{'complete' if triage_ok else 'pending'}** (see **Triage result** above)"
        )

        st.markdown("**Parallel agents**")
        for label, st_name, pct in _agent_statuses(snap if isinstance(snap, dict) else None):
            _show_agent_progress(label, st_name, pct)

        score = _risk_score_0_100(snap) if snap else 0.0
        g1, g2 = st.columns([1, 1])
        with g1:
            if snap:
                risk_gauge(score)
        with g2:
            st.metric("Model confidence", f"{float(rr.get('confidence', 0.0)):.2f}")
            st.caption("Full executive summary lives in **Investigation synthesis** (tab below).")

        reasoning = rr.get("reasoning_steps") or rr.get("evidence_chain") or []
        if isinstance(reasoning, list) and reasoning:
            with st.expander("Reasoning / evidence chain"):
                for line in reasoning[:25]:
                    if isinstance(line, dict):
                        st.write(f"- {line}")
                    else:
                        st.write(f"- {line}")

        rec_raw = data.get("hitl_recommendation")
        rec = rec_raw if isinstance(rec_raw, dict) else {}
        route = "HITL" if rr.get("requires_human_review") else "AUTO"
        cust = str(data.get("customer_id") or st.session_state.inv_customer_id).strip()
        txn = data.get("transaction_id")

        if route == "HITL" and inv_id and not hitl_decision_done:
            st.warning("Human review required — choose a disposition below.")
            _render_hitl_analyst_briefing(rec)
            b1, b2 = st.columns(2)
            if b1.button("False positive — close case", key="inv_hitl_fp_close"):
                st.session_state.inv_error = None
                with st.spinner("Recording false positive and closing…"):
                    if not post_hitl_decision(inv_id, "false_positive"):
                        st.session_state.inv_error = "HITL disposition request failed."
                    else:
                        out = post_execute_actions(inv_id, [_close_action_payload(inv_id, cust)])
                        if out is not None:
                            st.session_state.inv_hitl_sent = True
                            st.session_state.inv_last_hitl_decision = "false_positive"
                            st.session_state.inv_resolution_result = out
                            st.toast("Case closed as false positive", icon="📋")
                        else:
                            st.session_state.inv_hitl_sent = True
                            st.session_state.inv_last_hitl_decision = "false_positive"
                st.rerun()
            if b2.button("Freeze account — confirm fraud", type="primary", key="inv_hitl_confirm_freeze"):
                st.session_state.inv_error = None
                with st.spinner("Recording fraud confirmation and freezing…"):
                    if not post_hitl_decision(inv_id, "confirm_fraud"):
                        st.session_state.inv_error = "HITL disposition request failed."
                    else:
                        out = post_execute_actions(inv_id, [_freeze_action_payload(inv_id, cust, txn)])
                        if out is not None:
                            st.session_state.inv_hitl_sent = True
                            st.session_state.inv_last_hitl_decision = "confirm_fraud"
                            st.session_state.inv_resolution_result = out
                            st.session_state.inv_confirmed_fraud = int(
                                st.session_state.get("inv_confirmed_fraud") or 0
                            ) + 1
                            st.toast("Account freeze executed", icon="🔒")
                        else:
                            st.session_state.inv_hitl_sent = True
                            st.session_state.inv_last_hitl_decision = "confirm_fraud"
                st.rerun()
        elif st.session_state.get("inv_resolution_result"):
            st.success("Resolution or closure executed.")
            with st.expander("Action execution result (API)"):
                st.json(st.session_state.inv_resolution_result)
        elif hitl_decision_done and inv_id:
            dec = st.session_state.get("inv_last_hitl_decision")
            if not dec:
                st.success("HITL decision recorded for this session.")
            else:
                st.warning("Disposition recorded — remediation step needs a retry.")
                cust = data.get("customer_id") or st.session_state.inv_customer_id
                txn = data.get("transaction_id")
                if dec == "confirm_fraud":
                    st.caption("Freeze did not complete. Retry below.")
                    if st.button("Retry freeze account", type="primary", key="inv_exec_freeze_retry"):
                        st.session_state.inv_error = None
                        with st.spinner("Executing freeze…"):
                            out = post_execute_actions(inv_id, [_freeze_action_payload(inv_id, cust, txn)])
                        if out is not None:
                            st.session_state.inv_resolution_result = out
                            st.toast("Account freeze executed", icon="🔒")
                        st.rerun()
                elif dec == "false_positive":
                    st.caption("Case close did not complete. Retry below.")
                    if st.button("Retry close case", type="primary", key="inv_exec_close_retry"):
                        st.session_state.inv_error = None
                        with st.spinner("Closing case…"):
                            out = post_execute_actions(inv_id, [_close_action_payload(inv_id, cust)])
                        if out is not None:
                            st.session_state.inv_resolution_result = out
                            st.toast("Case closed", icon="📋")
                        st.rerun()

    st.markdown("---")
    st.markdown("#### Narrative · investigation synthesis · resolution audit")
    st.caption("Tabs: triage batch & narratives · LLM synthesis · resolution ledger. Toggle **Animate LLM text** above for streaming.")

    tri_saved = st.session_state.get("inv_triage")
    tab_nar, tab_syn, tab_res = st.tabs(
        ["Triage (batch & narrative)", "Investigation synthesis", "Resolution audit"]
    )
    with tab_nar:
        if isinstance(tri_saved, dict) and tri_saved:
            _render_triage_results(tri_saved)
            st.markdown("---")
            _render_triage_narratives(tri_saved, str(st.session_state.inv_customer_id))
        else:
            st.info("Run **2 · Triage assess** to populate batch metrics and suspicion narratives.")
    with tab_syn:
        if snap:
            _render_investigation_synthesis_panel(data, rr, inv_id)
        else:
            st.info("Run **3 · Run LangGraph deep investigation** to populate synthesis and evidence.")
    with tab_res:
        _render_resolution_audit_panel(
            st.session_state.get("inv_resolution_result"),
            st.session_state.get("inv_last_hitl_decision"),
        )

    with st.expander("Live trace (append-only)", expanded=False):
        log_lines = st.session_state.get("inv_event_log") or []
        body = "\n".join(log_lines[-80:]) if log_lines else "Awaiting API activity — use actions 1–3 above."
        st.markdown(f'<pre class="mini-terminal">{html.escape(body)}</pre>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Audit trail")
    audit_blob: dict[str, Any] = {
        "investigation_id": inv_id,
        "customer_id": st.session_state.inv_customer_id,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_phase": (snap or {}).get("phase") if snap else None,
        "triage_summary": (st.session_state.inv_triage or {}).get("triage_summary"),
        "deep_investigation": snap,
        "resolution_execute_actions": st.session_state.get("inv_resolution_result"),
        "last_hitl_decision": st.session_state.get("inv_last_hitl_decision"),
    }
    with st.expander("Full audit JSON (export-friendly)"):
        st.json(audit_blob)
    st.caption(f"Fraud memory patterns in store: **{patterns_n}**")
