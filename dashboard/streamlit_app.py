"""Streamlit command center: walkthrough stages + live investigator; calls FastAPI (``FRAUD_API_BASE``)."""

from __future__ import annotations

import html
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_root = Path(__file__).resolve().parent.parent
_dash = Path(__file__).resolve().parent
for _p in (_dash, _root):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import httpx
import pandas as pd
import streamlit as st

from app.shared.country_risk import HIGH_RISK_COUNTRIES as HIGH_RISK, MEDIUM_RISK_COUNTRIES as MED_RISK
from _dash_common import API_BASE, _api_headers

from investigator_console import render_investigator_console

DATA_DIR = _root / "app" / "data"

STAGE_LABELS = [
    "Data Sources",
    "Generate Alert",
    "Alerts Queue",
    "Triage",
    "Agent Investigation",
    "AI Risk Scoring",
    "HITL Review",
    "Resolution",
    "Audit Trail",
    "Live Dashboard",
]

PIPELINE_STEP_LABELS = ["Intake", "Detect", "Triage", "Investigate", "Score", "HITL", "Resolve"]
STAGE_TO_PIPELINE_INDEX: dict[int, int] = {1: 0, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 6, 10: 6}

NARRATIVE_BEATS = [
    ("01", "Ground truth",        "Load or upload the datasets your agents will reason over."),
    ("02", "Signal → case",       "Promote a suspicious movement into a formal alert with API idempotency."),
    ("03", "Queue discipline",    "Prioritise work the way an operations floor would."),
    ("04", "Policy first",        "Separate fast rules from slower model-assisted classification."),
    ("05", "Evidence in parallel","Let independent specialists build an auditable fact base."),
    ("06", "Synthesis",           "Collapse multi-source noise into one risk narrative."),
    ("07", "Human control",       "Reserve material outcomes for an analyst with a structured decision."),
    ("08", "Execute",             "Close the loop with actions and memory updates."),
    ("09", "Prove it",            "Export the immutable trace regulators expect."),
    ("10", "Steer the program",   "Roll up outcomes for leadership without losing fidelity."),
]

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM — CSS
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg:          #060d1a;
  --surface:     #0d1b2e;
  --surface-hi:  #132338;
  --border:      #1c3050;
  --border-act:  #2a4a7f;
  --primary:     #3b82f6;
  --primary-glow:rgba(59,130,246,0.12);
  --amber:       #f59e0b;
  --amber-glow:  rgba(245,158,11,0.12);
  --red:         #ef4444;
  --red-glow:    rgba(239,68,68,0.12);
  --green:       #10b981;
  --green-glow:  rgba(16,185,129,0.12);
  --purple:      #8b5cf6;
  --text:        #f0f6ff;
  --text-sec:    #8ba3c7;
  --text-muted:  #4a6080;
}

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
  background: #060d1a !important;
  color: #f0f6ff !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }

#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
  background: #0d1b2e !important;
  border-right: 1px solid #1c3050 !important;
}

.block-container {
  max-width: 1400px !important;
  /* Extra top padding: first markdown can sit under Streamlit’s inner chrome when toolbar is hidden */
  padding: 2.25rem 2rem 3rem !important;
}

[data-testid="stMainBlockContainer"] {
  padding-top: 0.75rem !important;
}

/* ── PIPELINE STEPPER (walkthrough journey) ── */
.pipeline-stepper-wrap {
  margin-bottom: 1.15rem;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid #1c3050;
}
.pipeline-track {
  height: 4px;
  background: #132338;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.65rem;
}
.pipeline-fill {
  height: 100%;
  background: linear-gradient(90deg,#1d4ed8,#3b82f6,#60a5fa);
  border-radius: 3px;
  transition: width 0.35s ease;
  box-shadow: 0 0 12px rgba(59,130,246,0.35);
}
.pipeline-steps {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.2rem;
}
.pipe-step {
  flex: 1;
  text-align: center;
  min-width: 0;
}
.pipe-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #1c3050;
  margin: 0 auto 0.32rem;
  display: block;
}
.pipe-step.done .pipe-dot {
  background: #10b981;
  box-shadow: 0 0 10px rgba(16,185,129,0.45);
}
.pipe-step.active .pipe-dot {
  background: #3b82f6;
  box-shadow: 0 0 14px rgba(59,130,246,0.65);
}
.pipe-lab {
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #4a6080;
  line-height: 1.25;
  display: block;
}
.pipe-step.active .pipe-lab { color: #93c5fd; }
.pipe-step.done .pipe-lab { color: #6ee7b7; }

/* ── SYSTEM STATUS (technical context, low prominence) ── */
.system-status-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin: -0.35rem 0 1rem 0;
}
.sys-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.65rem;
  font-weight: 600;
  color: #8ba3c7;
  background: rgba(13,27,46,0.85);
  border: 1px solid #1c3050;
  border-radius: 999px;
  padding: 0.22rem 0.65rem;
}
.sys-pill-mono { font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; color: #64748b; }
.sys-pill-live .sys-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 8px rgba(52,211,153,0.7);
  animation: pulse-dot 1.8s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

/* ── FORMS: consistent rounding ── */
[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] > label {
  border-radius: 8px !important;
}

/* ── STAGE HERO ── */
.stage-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 1rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #1c3050;
}
.stage-hero-left { min-width: 0; }
.stage-hero-kicker {
  font-size: .65rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #4a6080;
  margin-bottom: .35rem;
}
.stage-hero-title {
  font-size: 1.2rem;
  font-weight: 800;
  color: #f0f6ff;
  letter-spacing: -.02em;
  line-height: 1.25;
  margin-bottom: .3rem;
}
.stage-hero-desc {
  font-size: .83rem;
  color: #8ba3c7;
  line-height: 1.55;
}

/* ── STAT CARDS ── */
.stat-card {
  background: linear-gradient(145deg,#0d1b2e,#0a1525);
  border: 1px solid #1c3050;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  text-align: center;
}
.stat-value {
  font-size: 1.9rem;
  font-weight: 800;
  line-height: 1;
  margin-bottom: .2rem;
  letter-spacing: -.03em;
}
.stat-label {
  font-size: .65rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #4a6080;
}

/* ── ALERT CARDS ── */
.alert-card {
  background: linear-gradient(145deg,#0d1b2e,#0a1525);
  border: 1px solid #1c3050;
  border-radius: 12px;
  padding: 1rem 1.2rem;
  margin-bottom: .65rem;
  transition: border-color .2s;
}
.alert-card.critical { border-left: 3px solid #ef4444; }
.alert-card.high     { border-left: 3px solid #f59e0b; }
.alert-card.medium   { border-left: 3px solid #3b82f6; }
.alert-card.selected { border-color: #3b82f6; box-shadow: 0 0 0 1px rgba(59,130,246,.25); }

/* ── PILLS ── */
.pill {
  display: inline-flex;
  align-items: center;
  padding: .18rem .6rem;
  border-radius: 6px;
  font-size: .63rem;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
}
.pill-critical { background: rgba(239,68,68,.12);  color: #fca5a5; border: 1px solid rgba(239,68,68,.3); }
.pill-high     { background: rgba(245,158,11,.12); color: #fde68a; border: 1px solid rgba(245,158,11,.3); }
.pill-medium   { background: rgba(59,130,246,.12); color: #93c5fd; border: 1px solid rgba(59,130,246,.3); }
.pill-low      { background: rgba(16,185,129,.12); color: #6ee7b7; border: 1px solid rgba(16,185,129,.3); }
.pill-new      { background: rgba(245,158,11,.12); color: #fbbf24; border: 1px solid rgba(245,158,11,.4); }
.pill-closed   { background: rgba(71,85,105,.2);   color: #94a3b8; border: 1px solid #334155; }
.pill-hitl     { background: rgba(139,92,246,.12); color: #c4b5fd; border: 1px solid rgba(139,92,246,.3); }
.pill-investigating { background: rgba(59,130,246,.12); color: #93c5fd; border: 1px solid rgba(59,130,246,.3); }

/* ── AGENT CARDS ── */
.agent-card {
  background: linear-gradient(145deg,#0d1b2e,#0a1525);
  border: 1px solid #1c3050;
  border-radius: 12px;
  padding: 1.2rem;
}
.agent-card.success { border-top: 3px solid #10b981; }
.agent-card.warning { border-top: 3px solid #f59e0b; }
.agent-card.danger  { border-top: 3px solid #ef4444; }
.agent-name {
  font-size: .75rem;
  font-weight: 700;
  letter-spacing: .07em;
  text-transform: uppercase;
  margin-bottom: .8rem;
  padding-bottom: .5rem;
  border-bottom: 1px solid #1c3050;
}
.agent-finding {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .35rem 0;
  border-bottom: 1px solid #1c3050;
  font-size: .78rem;
}
.agent-finding:last-child { border-bottom: none; }
.fk { color: #4a6080; }
.fv { font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: .75rem; }
.fv-t { color: #10b981; }
.fv-f { color: #4a6080; }
.fv-h { color: #ef4444; }
.fv-m { color: #f59e0b; }

/* ── EVIDENCE CARDS ── */
.evidence-card {
  background: #0d1b2e;
  border: 1px solid #1c3050;
  border-left: 3px solid #8b5cf6;
  border-radius: 0 10px 10px 0;
  padding: .75rem 1rem;
  margin-bottom: .5rem;
}
.evidence-reason { font-size: .82rem; font-weight: 600; color: #f0f6ff; margin-bottom: .2rem; }
.evidence-meta   { font-size: .7rem; color: #4a6080; font-family: 'JetBrains Mono', monospace; }

/* ── RISK DISPLAY ── */
.risk-display {
  background: linear-gradient(145deg,#0d1b2e,#0a1525);
  border: 1px solid #1c3050;
  border-radius: 16px;
  padding: 1.75rem 1.5rem;
  text-align: center;
  margin-bottom: 1rem;
}
.risk-number {
  font-size: 4.5rem;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -.05em;
  font-family: 'JetBrains Mono', monospace;
}
.gauge-track {
  height: 8px;
  border-radius: 4px;
  background: #1c3050;
  overflow: hidden;
  margin: .75rem 0 .35rem;
}
.gauge-fill { height: 100%; border-radius: 4px; }

/* ── HITL ALERT ── */
.hitl-alert {
  background: linear-gradient(135deg,rgba(245,158,11,.1),rgba(245,158,11,.04));
  border: 1px solid rgba(245,158,11,.35);
  border-radius: 12px;
  padding: 1.2rem 1.4rem;
  margin-bottom: 1.5rem;
}
.hitl-title { font-size: 1rem; font-weight: 700; color: #fbbf24; margin-bottom: .4rem; }
.hitl-body  { font-size: .83rem; color: #d97706; line-height: 1.5; }

/* ── SUMMARY CARDS ── */
.summary-card {
  background: #0d1b2e;
  border: 1px solid #1c3050;
  border-radius: 10px;
  padding: 1rem 1.2rem;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .38rem 0;
  border-bottom: 1px solid #1c3050;
  font-size: .82rem;
}
.summary-row:last-child { border-bottom: none; }
.summary-note {
  font-size: .7rem;
  color: #5a7090;
  line-height: 1.4;
  padding: .4rem 0 .6rem;
  border-bottom: 1px solid #1c3050;
}
.sk { color: #4a6080; }
.sv { font-weight: 600; color: #f0f6ff; font-family: 'JetBrains Mono', monospace; font-size: .78rem; }

/* ── ACTION ROWS ── */
.action-row {
  background: rgba(16,185,129,.06);
  border: 1px solid rgba(16,185,129,.2);
  border-radius: 10px;
  padding: .75rem 1rem;
  margin-bottom: .4rem;
  display: flex;
  align-items: center;
  gap: .75rem;
}
.action-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: .78rem;
  color: #34d399;
  font-weight: 600;
}

/* ── MEMORY ROWS ── */
.memory-row {
  background: rgba(16,185,129,.05);
  border: 1px solid rgba(16,185,129,.15);
  border-radius: 8px;
  padding: .6rem .9rem;
  margin-bottom: .35rem;
  font-size: .78rem;
  display: flex;
  align-items: center;
  gap: .6rem;
}
.memory-type {
  font-size: .63rem;
  font-weight: 700;
  letter-spacing: .07em;
  text-transform: uppercase;
  background: rgba(16,185,129,.12);
  color: #34d399;
  padding: .15rem .45rem;
  border-radius: 4px;
  flex-shrink: 0;
}
.memory-val { font-family: 'JetBrains Mono', monospace; color: #8ba3c7; font-size: .75rem; }

/* ── TIMELINE ROWS ── */
.timeline-row {
  display: flex;
  gap: .75rem;
  padding: .5rem 0;
  border-bottom: 1px solid #1c3050;
  font-size: .78rem;
  align-items: flex-start;
}
.timeline-ts  { font-family: 'JetBrains Mono', monospace; color: #3b82f6; font-size: .68rem; flex-shrink: 0; min-width: 160px; }
.timeline-evt { color: #8ba3c7; line-height: 1.45; }

/* ── INFO / WARN / SUCCESS PANELS ── */
.info-panel    { background: rgba(59,130,246,.07);  border: 1px solid rgba(59,130,246,.2);  border-radius: 10px; padding: .85rem 1rem; margin-bottom: 1rem; font-size: .83rem; color: #93c5fd; }
.warn-panel    { background: rgba(245,158,11,.07);  border: 1px solid rgba(245,158,11,.3);  border-radius: 10px; padding: .85rem 1rem; margin-bottom: 1rem; font-size: .83rem; color: #fbbf24; }
.success-panel { background: rgba(16,185,129,.07);  border: 1px solid rgba(16,185,129,.3);  border-radius: 10px; padding: .85rem 1rem; margin-bottom: 1rem; font-size: .83rem; color: #34d399; }

/* ── FLAG ROWS ── */
.flag-row {
  display: flex;
  align-items: flex-start;
  gap: .75rem;
  padding: .7rem 1rem;
  border-radius: 10px;
  margin-bottom: .4rem;
  background: #0d1b2e;
  border: 1px solid #1c3050;
}
.flag-label  { font-size: .78rem; font-weight: 700; color: #f0f6ff; }
.flag-detail { font-size: .72rem; color: #4a6080; margin-top: 1px; }

/* ── SIDEBAR STATS ── */
.sb-divider { border: none; border-top: 1px solid #1c3050; margin: .6rem 0; }
.sb-nav-group { padding: 0.05rem 0 0.35rem; margin-bottom: 0.1rem; }
.sb-header  {
  font-size: .58rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #5a7090;
  margin: .85rem 0 .4rem;
  display: flex;
  align-items: center;
  gap: .4rem;
}
.sb-nav-group:first-of-type .sb-header { margin-top: 0.15rem !important; }
.sb-header-icon { font-size: .75rem; opacity: 0.9; }
.sb-stat    { display: flex; justify-content: space-between; align-items: center; padding: .32rem 0; border-bottom: 1px solid #1c3050; }
.sb-stat:last-child { border-bottom: none; }
.sb-stat-label { font-size: .73rem; color: #4a6080; }
.sb-stat-val   { font-size: .82rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.sb-nav-item   { display: flex; align-items: center; gap: .45rem; padding: .3rem .1rem; font-size: .73rem; color: #4a6080; }
.sb-nav-item.done   { color: #34d399; }
.sb-nav-item.active { color: #93c5fd; font-weight: 700; }
.sb-nav-icon { font-size: .65rem; width: 1em; text-align: center; flex-shrink: 0; }

/* ── API BADGE ── */
.api-badge       { display: inline-flex; align-items: center; gap: .3rem; background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.25); border-radius: 6px; padding: .15rem .5rem; font-size: .63rem; font-weight: 700; color: #34d399; font-family: 'JetBrains Mono', monospace; }
.api-badge.error { background: rgba(239,68,68,.1); border-color: rgba(239,68,68,.25); color: #fca5a5; }

/* ── SECTION LABEL ── */
.section-label { font-size: .65rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #4a6080; margin-bottom: .75rem; display: block; }

/* ── PLATFORM HEADER ── */
.platform-header {
  display: flex;
  align-items: flex-start;
  gap: .75rem;
  padding: 1rem 1.15rem 1rem 1.1rem;
  background: linear-gradient(135deg,#0d1b2e,#0a1525);
  border: 1px solid #1c3050;
  border-radius: 12px;
  margin-top: 0.25rem;
  margin-bottom: 1.25rem;
  overflow: visible;
  position: relative;
  z-index: 1;
}
.platform-logo {
  font-size: 1.15rem;
  line-height: 1.35;
  flex-shrink: 0;
  padding-top: 0.12rem;
}
.platform-header > div:last-child {
  min-width: 0;
  flex: 1;
}
/* !important: Streamlit main/sidebar CSS can override nested markdown colors */
.platform-header .platform-name {
  font-size: 1.05rem;
  font-weight: 800;
  color: #f8fafc !important;
  letter-spacing: -.02em;
  line-height: 1.35;
  padding-top: 0.05rem;
  margin: 0;
}
.platform-header .platform-sub {
  font-size: .74rem;
  color: #94a3b8 !important;
  margin-top: 0.2rem;
  line-height: 1.35;
  margin-bottom: 0;
}

/* ── ANIMATIONS ── */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-amber {
  0%,100% { box-shadow: 0 0 0 0 rgba(245,158,11,0); }
  50%      { box-shadow: 0 0 0 8px rgba(245,158,11,.12); }
}
@keyframes glow-red {
  0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
  50%      { box-shadow: 0 0 0 8px rgba(239,68,68,.15); }
}
.fadeInUp    { animation: fadeInUp .45s ease-out; }
.pulse-amber { animation: pulse-amber 2.2s infinite; }
.glow-red    { animation: glow-red 2s infinite; }

/* ── BUTTONS ── */
button[kind="primary"],
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg,#2563eb,#1d4ed8) !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 14px rgba(37,99,235,.3) !important;
  color: #fff !important;
}
button[kind="secondary"],
.stButton > button[kind="secondary"] {
  background: #0d1b2e !important;
  border: 1px solid #2a4a7f !important;
  color: #93c5fd !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}
.stButton > button { transition: all .2s ease !important; }
.stButton > button:hover:not(:disabled) { transform: translateY(-1px) !important; }

/* ── FORMS / INPUTS ── */
[data-testid="stForm"] { background: #0d1b2e; border: 1px solid #1c3050; border-radius: 12px; padding: 1.2rem; }
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] select,
textarea {
  background: #0a1525 !important;
  border: 1px solid #1c3050 !important;
  color: #f0f6ff !important;
  border-radius: 8px !important;
}

/* ── TABS ── */
[data-testid="stTabs"] [role="tab"] {
  font-size: .78rem !important;
  font-weight: 600 !important;
  color: #4a6080 !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: #93c5fd !important;
  border-bottom-color: #3b82f6 !important;
}

/* ── DATAFRAMES ── */
[data-testid="stDataFrame"] { border: 1px solid #1c3050 !important; border-radius: 10px !important; overflow: hidden; }

/* ── METRICS (audit stage only) ── */
[data-testid="stMetric"] { background: #0d1b2e; border: 1px solid #1c3050; border-radius: 10px; padding: .75rem 1rem; }
[data-testid="stMetricLabel"] { font-size: .65rem !important; font-weight: 700 !important; letter-spacing: .08em !important; text-transform: uppercase !important; color: #4a6080 !important; }
[data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 800 !important; color: #f0f6ff !important; }

hr { border-color: #1c3050 !important; margin: 1.5rem 0 !important; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def api_post(path: str, payload: dict, params: dict | None = None, timeout: float = 60) -> dict:
    try:
        r = httpx.post(
            f"{API_BASE}{path}",
            json=payload,
            headers=_api_headers(),
            timeout=timeout,
            params=params or {},
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get(path: str, params: dict | None = None) -> dict:
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, headers=_api_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def _coerce_pattern_type_label(v: Any) -> str:
    if v is None:
        return "?"
    if isinstance(v, dict):
        inner = v.get("value") if "value" in v else v.get("pattern_type")
        return str(inner if inner is not None else "?")
    return str(v)


def _fraud_memory_row_from_api_entry(p: dict[str, Any]) -> dict[str, Any]:
    """Map ``GET /v1/fraud-memory`` pattern objects to the walkthrough UI row shape."""
    meta = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
    desc = (
        meta.get("description")
        or meta.get("detail")
        or meta.get("analyst_note")
        or ""
    )
    if not desc:
        desc = "—"
    return {
        "pattern_type": _coerce_pattern_type_label(p.get("pattern_type")),
        "entity_id": str(p.get("entity_id") or "?"),
        "entity_type": str(p.get("entity_type") or "customer"),
        "confidence": float(p.get("confidence") or 0.0),
        "risk_score": float(p.get("risk_score") or 0.0),
        "status": str(p.get("status") or "ACTIVE"),
        "description": desc,
        "memory_id": str(p.get("memory_id") or ""),
    }


def sync_fraud_memory_from_api(*, force: bool = False) -> None:
    """Hydrate ``st.session_state.fraud_memory`` from ``GET /v1/fraud-memory`` (in-memory API store)."""
    if force:
        st.session_state.pop("_fm_synced_v1", None)
    if st.session_state.get("_fm_synced_v1"):
        return
    st.session_state._fm_synced_v1 = True
    st.session_state.pop("_fm_sync_error", None)
    resp = api_get(
        "/v1/fraud-memory",
        params={"view": "patterns", "filter": "all", "limit": 500},
    )
    if not isinstance(resp, dict) or not resp.get("success"):
        err = str(resp.get("error", "Could not load fraud memory")) if isinstance(resp, dict) else "Invalid response"
        st.session_state["_fm_sync_error"] = err
        st.session_state.fraud_memory = []
        return
    data = resp.get("data") or {}
    raw = data.get("patterns")
    if not isinstance(raw, list):
        raw = []
    st.session_state.fraud_memory = [_fraud_memory_row_from_api_entry(p) for p in raw if isinstance(p, dict)]


def api_badge(label: str, ok: bool = True) -> str:
    cls = "api-badge" if ok else "api-badge error"
    icon = "✓" if ok else "✗"
    return f'<span class="{cls}">{icon} {label}</span>'


def _legacy_triage_from_assessed(assessed: list[dict], alert_id: str) -> dict | None:
    """Map ``POST /v1/triage/assess`` ``AssessedAlert`` JSON to the legacy walkthrough triage dict."""
    for a in assessed:
        if (a.get("alert_id") or "").strip() != (alert_id or "").strip():
            continue
        inv_dec = a.get("decision") or {}
        if not isinstance(inv_dec, dict):
            inv_dec = {}
        action = inv_dec.get("action")
        if isinstance(action, dict):
            action = action.get("value", action)
        reasoning = (inv_dec.get("reasoning") or "").strip()
        conf = inv_dec.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 0.75
        except (TypeError, ValueError):
            conf_f = 0.75
        rs = a.get("risk_score") or {}
        score = float(rs.get("score", 0.0)) if isinstance(rs, dict) else 0.0
        sev = rs.get("severity", "MEDIUM")
        sev_s = sev if isinstance(sev, str) else str(getattr(sev, "value", sev))
        priority = (
            "CRITICAL"
            if "critical" in sev_s.lower()
            else "HIGH"
            if "high" in sev_s.lower()
            else "MEDIUM"
        )
        note = (a.get("initial_suspicion_note") or "").strip()
        if note:
            reasoning = f"{reasoning}\n\n**Narrative:** {note}" if reasoning else f"**Narrative:** {note}"
        hits = a.get("sanctions_hits") or []
        if isinstance(hits, list) and hits:
            key_flags = [str(h.get("country_code") or h.get("tier") or h) for h in hits[:8]]
        else:
            md = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
            key_flags = list(md.get("risk_indicators") or []) or [f"policy:{a.get('policy', '')}"]
        return {
            "decision": str(action or "REVIEW"),
            "priority": priority,
            "risk_score": score,
            "confidence": conf_f,
            "reasoning": reasoning or "Triage assessment complete.",
            "key_flags": key_flags,
        }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    return json.loads(path.read_text()) if path.exists() else []


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def utcnow_clock() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def trace(msg: str) -> None:
    st.session_state.audit_trail.append({"timestamp": utcnow_iso(), "event": msg})


def pill(label: str, kind: str) -> str:
    cls = {
        "NEW": "pill-new", "CRITICAL": "pill-critical", "HIGH": "pill-high",
        "MEDIUM": "pill-medium", "LOW": "pill-low", "CLOSED": "pill-closed",
        "HITL": "pill-hitl", "INVESTIGATING": "pill-investigating",
    }.get(kind.upper(), "pill-medium")
    return f'<span class="pill {cls}">{html.escape(label)}</span>'


def risk_color(s: float) -> str:
    return "#ef4444" if s >= 0.8 else "#f59e0b" if s >= 0.6 else "#3b82f6" if s >= 0.4 else "#10b981"


def risk_gradient(s: float) -> str:
    return ("linear-gradient(90deg,#ef4444,#dc2626)" if s >= 0.8 else
            "linear-gradient(90deg,#f59e0b,#d97706)" if s >= 0.6 else
            "linear-gradient(90deg,#3b82f6,#2563eb)" if s >= 0.4 else
            "linear-gradient(90deg,#10b981,#059669)")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state() -> None:
    defaults: dict[str, Any] = {
        "stage": 1,
        "alerts": [],
        "selected_alert_id": None,
        "fraud_memory_updates": [],
        "audit_trail": [{"timestamp": utcnow_iso(), "event": "SESSION_START — command center initialised"}],
        "metrics": {"total_alerts": 0, "blocked": 0, "auto_closed": 0, "hitl_pending": 0, "confirmed_fraud": 0},
        "transactions": load_json("transactions.json"),
        "customers":    load_json("customers.json"),
        "kyc_events":   load_json("kyc_events.json"),
        "sanctions":    load_json("sanctions_data.json"),
        "fraud_memory": [],
        "data_source":  "built-in",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def render_platform_header() -> None:
    st.markdown(
        '<div class="platform-header">'
        '<span class="platform-logo">🏛️</span>'
        '<div>'
        '<div class="platform-name">Agentic AI Fraud Investigator</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_system_status_strip() -> None:
    raw = (API_BASE or "").strip()
    try:
        host = urlparse(raw).netloc or raw.split("://", 1)[-1].split("/", 1)[0] or "—"
    except Exception:
        host = "—"
    pv = html.escape(str(st.session_state.get("primary_view", "Walkthrough (10 stages)")))
    st.markdown(
        '<div class="system-status-strip">'
        '<span class="sys-pill sys-pill-live"><span class="sys-dot"></span>FastAPI + LangGraph</span>'
        f'<span class="sys-pill">{pv}</span>'
        f'<span class="sys-pill sys-pill-mono">{html.escape(host)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_pipeline_stepper(current: int) -> None:
    cur = max(1, min(10, int(current)))
    ai = STAGE_TO_PIPELINE_INDEX.get(cur, 0)
    fill_pct = min(100.0, (ai + 1) / 7.0 * 100.0)
    parts: list[str] = []
    for i, lab in enumerate(PIPELINE_STEP_LABELS):
        if i < ai:
            cls = "pipe-step done"
        elif i == ai:
            cls = "pipe-step active"
        else:
            cls = "pipe-step"
        parts.append(
            f'<span class="{cls}"><span class="pipe-dot"></span>'
            f'<span class="pipe-lab">{html.escape(lab)}</span></span>'
        )
    st.markdown(
        f'<div class="pipeline-stepper-wrap">'
        f'<div class="pipeline-track"><div class="pipeline-fill" style="width:{fill_pct:.1f}%"></div></div>'
        f'<div class="pipeline-steps">{"".join(parts)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def stage_hero(
    stage_num: int,
    title: str,
    description: str,
    badge_label: str = "",
    badge_ok: bool = True,
    learning: str = "",
) -> None:
    color  = "#34d399" if badge_ok else "#fbbf24"
    border = "rgba(52,211,153,.35)" if badge_ok else "rgba(251,191,36,.35)"
    bg     = "rgba(16,185,129,.08)" if badge_ok else "rgba(245,158,11,.1)"
    badge_html = ""
    if badge_label:
        badge_html = (
            f'<span style="font-size:.63rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;'
            f'background:{bg};border:1px solid {border};border-radius:8px;padding:.28rem .65rem;'
            f'color:{color};white-space:nowrap;flex-shrink:0;">'
            f'{html.escape(badge_label)}</span>'
        )
    kicker = f'STAGE {stage_num:02d} OF 10 &nbsp;·&nbsp; {html.escape(STAGE_LABELS[stage_num - 1].upper())}'
    st.markdown(
        f'<div class="stage-hero fadeInUp">'
        f'<div class="stage-hero-left">'
        f'<div class="stage-hero-kicker">{kicker}</div>'
        f'<div class="stage-hero-title">{html.escape(title)}</div>'
        f'<div class="stage-hero-desc">{html.escape(description)}</div>'
        f'</div>'
        f'<div style="padding-top:.2rem;">{badge_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def action_button(label: str, key: str, next_stage: int) -> None:
    _, col = st.columns([3, 1])
    with col:
        if st.button(label, type="primary", key=key, use_container_width=True):
            st.session_state.stage = next_stage
            st.rerun()


def render_sidebar() -> None:
    current = st.session_state.stage
    m = st.session_state.metrics

    with st.sidebar:
        st.markdown(
            '<div style="padding:.75rem 0 .5rem;">'
            '<div style="font-size:.95rem;font-weight:800;color:#f0f6ff;letter-spacing:-.02em;">🏛️ Command Center</div>'
            '<div style="font-size:.7rem;color:#4a6080;margin-top:2px;">Andela Digital Bank · Fraud AI</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # Live clock
        st.markdown(
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.72rem;color:#3b82f6;'
            f'text-align:center;padding:.25rem 0;">{utcnow_clock()}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # Stats block — no st.metric
        fraud_stopped = m["confirmed_fraud"] + m["blocked"]
        stats_html = (
            '<div class="sb-stat"><span class="sb-stat-label">Total Alerts</span>'
            f'<span class="sb-stat-val" style="color:#f0f6ff;">{m["total_alerts"]}</span></div>'
            '<div class="sb-stat"><span class="sb-stat-label">Fraud Confirmed</span>'
            f'<span class="sb-stat-val" style="color:#ef4444;">{m["confirmed_fraud"]}</span></div>'
            '<div class="sb-stat"><span class="sb-stat-label">Auto-Closed</span>'
            f'<span class="sb-stat-val" style="color:#10b981;">{m["auto_closed"]}</span></div>'
            '<div class="sb-stat"><span class="sb-stat-label">HITL Pending</span>'
            f'<span class="sb-stat-val" style="color:#f59e0b;">{m["hitl_pending"]}</span></div>'
            '<div class="sb-stat"><span class="sb-stat-label">Accts Blocked</span>'
            f'<span class="sb-stat-val" style="color:#ef4444;">{m["blocked"]}</span></div>'
        )
        st.markdown(stats_html, unsafe_allow_html=True)
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # Navigation groups
        nav_groups = [
            ("🗄️", "INGESTION", [
                (1, "Data Sources"),
                (2, "Generate Alert"),
                (3, "Alerts Queue"),
            ]),
            ("📡", "ANALYSIS", [
                (4, "Triage"),
                (5, "Agent Investigation"),
                (6, "AI Risk Scoring"),
            ]),
            ("⚖️", "DECISION", [
                (7, "HITL Review"),
                (8, "Resolution"),
                (9, "Audit Trail"),
                (10, "Live Dashboard"),
            ]),
        ]
        for gicon, group_name, items in nav_groups:
            st.markdown(
                f'<span class="sb-header"><span class="sb-header-icon">{gicon}</span>{html.escape(group_name)}</span>',
                unsafe_allow_html=True,
            )
            for idx, label in items:
                icon = "✓ " if idx < current else "▸ " if idx == current else "○ "
                if st.button(f"{icon}{label}", key=f"nav_{idx}", use_container_width=True):
                    st.session_state.stage = idx
                    st.rerun()

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)
        if st.button("↺  Reset Demo", key="reset_demo", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — DATA SOURCES
# ─────────────────────────────────────────────────────────────────────────────
def stage_data_sources() -> None:
    src_label = "Built-in" if st.session_state.get("data_source", "built-in") == "built-in" else "Uploaded"
    stage_hero(
        1,
        "Establish the evidence base",
        "Load the reference pack (transactions, KYC, sanctions) or swap in your own JSON. Fraud memory patterns are loaded from the FastAPI store (``GET /v1/fraud-memory``); use the demo loader only if you want the bundled JSON fixtures.",
        badge_label="",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        r1, r2 = st.columns([5, 2])
        with r1:
            source = st.radio(
                "Dataset",
                ["Built-in dataset", "Upload custom data"],
                horizontal=True,
                key="data_source_radio",
                label_visibility="visible",
            )
        with r2:
            st.markdown(
                f'<div style="text-align:right;padding-top:.5rem;">'
                f'<span style="font-size:.72rem;color:#4a6080;">Active · </span>'
                f'<span style="font-size:.72rem;font-weight:700;color:#34d399;">{src_label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if source == "Upload custom data":
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">Upload JSON Data Files</span>', unsafe_allow_html=True)
            st.caption("Each file must be a JSON array matching the built-in schema.")
            col1, col2, col3 = st.columns(3)
            with col1:
                txn_file = st.file_uploader("Transactions (JSON)", type="json", key="upload_txn")
                if txn_file:
                    st.session_state.transactions = json.load(txn_file)
                    st.session_state.data_source = "uploaded"
                    st.success(f"✓ {len(st.session_state.transactions)} transactions loaded")
            with col2:
                kyc_file = st.file_uploader("KYC Events (JSON)", type="json", key="upload_kyc")
                if kyc_file:
                    st.session_state.kyc_events = json.load(kyc_file)
                    st.success(f"✓ {len(st.session_state.kyc_events)} KYC events loaded")
            with col3:
                cust_file = st.file_uploader("Customers (JSON)", type="json", key="upload_cust")
                if cust_file:
                    st.session_state.customers = json.load(cust_file)
                    st.success(f"✓ {len(st.session_state.customers)} customers loaded")
            with st.expander("View expected JSON schemas"):
                st.code(json.dumps({
                    "transactions": [{"transaction_id": "TXN001", "customer_id": "CUST001", "amount": 15000, "currency": "USD", "timestamp": "2025-01-10T02:30:00Z", "destination_country": "IR", "device_id": "DEV001", "ip_address": "185.1.2.3", "risk_indicators": ["high_value_rush"]}],
                    "kyc_events":   [{"customer_id": "CUST001", "event_type": "login_attempt", "timestamp": "2025-01-10T02:30:00Z", "ip_address": "185.1.2.3", "device_info": {"device_type": "desktop", "os": "Windows 10", "browser": "Chrome"}, "geo_location": {"country": "RU", "city": "Moscow", "latitude": 55.75, "longitude": 37.61}, "anomaly_type": "geo_location_mismatch", "risk_score": 0.85}],
                    "customers":    [{"customer_id": "CUST001", "name": "John Smith", "account_type": "premium", "risk_profile": "medium", "total_transactions": 1247, "total_amount": 284750}],
                }, indent=2), language="json")

        st.markdown("<hr>", unsafe_allow_html=True)

        txns  = st.session_state.transactions
        kyc   = st.session_state.kyc_events
        san   = st.session_state.sanctions
        mem   = st.session_state.fraud_memory
        custs = st.session_state.customers

        flagged     = len([t for t in txns if t.get("risk_indicators")])
        kyc_anom    = len([k for k in kyc if k.get("anomaly_type")])
        san_entries = san.get("sanctions_entries", []) if isinstance(san, dict) else []

        st.markdown(
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.6rem;margin-bottom:1.25rem;">'
            f'<div class="stat-card"><div class="stat-value" style="color:#3b82f6;">{len(txns)}</div><div class="stat-label">Transactions</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{flagged}</div><div class="stat-label">Flagged</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#f59e0b;">{kyc_anom}</div><div class="stat-label">KYC Anomalies</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#8b5cf6;">{len(san_entries)}</div><div class="stat-label">Sanctioned Entities</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{len(mem)}</div><div class="stat-label">Fraud Patterns</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        tab_tx, tab_kyc, tab_san, tab_mem, tab_cust = st.tabs(
            ["Transactions", "KYC Events", "Sanctions", "Fraud Memory", "Customers"]
        )

        with tab_tx:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search_term = st.text_input("Search", placeholder="Txn ID, customer, country…", label_visibility="visible")
            with col2:
                min_amount = st.number_input("Min $", value=0.0, key="min_amount")
            with col3:
                max_amount = st.number_input("Max $", value=100000.0, key="max_amount")

            filtered_txns = []
            for t in txns:
                if search_term and search_term.lower() not in str(t.get("transaction_id", "")).lower() \
                        and search_term.lower() not in str(t.get("customer_id", "")).lower() \
                        and search_term.lower() not in str(t.get("destination_country", "")).lower():
                    continue
                if min_amount and t.get("amount", 0) < min_amount:
                    continue
                if max_amount and t.get("amount", 0) > max_amount:
                    continue
                filtered_txns.append(t)

            st.markdown(
                f'<div style="margin-bottom:.75rem;font-size:.82rem;color:#8ba3c7;">'
                f'Showing <b style="color:#f0f6ff;">{min(10, len(filtered_txns))}</b> of <b style="color:#f0f6ff;">{len(filtered_txns)}</b> transactions</div>',
                unsafe_allow_html=True,
            )

            for t in filtered_txns[:10]:
                amount  = float(t.get("amount", 0) or 0)
                country = str(t.get("destination_country", "UNKNOWN"))
                tid     = str(t.get("transaction_id", "UNKNOWN"))
                cid     = str(t.get("customer_id", "UNKNOWN"))
                rl      = "CRITICAL" if country in HIGH_RISK else "HIGH" if country in MED_RISK else "MEDIUM"
                inds    = [str(x) for x in (t.get("risk_indicators") or [])]
                inds_txt = ", ".join(inds) if inds else "—"
                inds_pills = " ".join(
                    f'<span style="background:rgba(239,68,68,.1);color:#fca5a5;border:1px solid rgba(239,68,68,.25);'
                    f'padding:.12rem .45rem;border-radius:5px;font-size:.62rem;font-weight:700;">{html.escape(i)}</span>'
                    for i in inds
                ) if inds else '<span style="color:#4a6080;font-size:.72rem;">—</span>'
                rc = "#ef4444" if rl == "CRITICAL" else "#f59e0b" if rl == "HIGH" else "#3b82f6"
                st.markdown(
                    f'<div class="alert-card {rl.lower()}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem;">'
                    f'<div style="display:flex;align-items:center;gap:.5rem;">{pill(rl, rl)}'
                    f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.78rem;color:#f0f6ff;font-weight:700;">{html.escape(tid)}</span>'
                    f'<span style="color:#4a6080;font-size:.75rem;">{html.escape(cid)}</span></div>'
                    f'<span style="font-size:1rem;font-weight:800;color:{rc};">${amount:,.2f}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">'
                    f'<span style="font-size:.72rem;color:#4a6080;">→ {html.escape(country)}</span>'
                    f'<span style="color:#1c3050;">·</span>{inds_pills}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if len(filtered_txns) > 10:
                st.info(f"Showing first 10 of {len(filtered_txns)} transactions. Use search to narrow results.")

        with tab_kyc:
            for ev in kyc:
                geo = ev.get("geo_location") or {}
                dev = ev.get("device_info") or {}
                rs  = ev.get("risk_score", 0)
                rc  = "#ef4444" if rs > 0.8 else "#f59e0b" if rs > 0.6 else "#3b82f6"
                st.markdown(
                    f'<div class="alert-card high">'
                    f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem;">'
                    f'{pill(ev.get("anomaly_type", "unknown").upper().replace("_", " "), "HIGH")}'
                    f'<b style="color:#f0f6ff;">{html.escape(ev["customer_id"])}</b>'
                    f'<span style="color:#4a6080;font-size:.75rem;">{html.escape(ev["event_type"])}</span>'
                    f'</div>'
                    f'<div style="font-size:.73rem;color:#4a6080;font-family:\'JetBrains Mono\',monospace;">'
                    f'📍 {html.escape(str(geo.get("city","?")))} {html.escape(str(geo.get("country","?")))} &nbsp;·&nbsp; '
                    f'💻 {html.escape(str(dev.get("os","?")))} &nbsp;·&nbsp; '
                    f'Risk: <b style="color:{rc};">{rs}</b> &nbsp;·&nbsp; {html.escape(ev["timestamp"])}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        with tab_san:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<span class="section-label">Sanctioned Entities</span>', unsafe_allow_html=True)
                if san_entries:
                    st.dataframe(
                        pd.DataFrame(san_entries)[["entity_name", "entity_type", "sanctions_list", "risk_level", "risk_score"]],
                        hide_index=True, use_container_width=True,
                    )
            with c2:
                st.markdown('<span class="section-label">Country Risk Profiles</span>', unsafe_allow_html=True)
                countries = san.get("country_risks", []) if isinstance(san, dict) else []
                if countries:
                    st.dataframe(
                        pd.DataFrame(countries)[["country_code", "country_name", "risk_level", "risk_score", "sanctions_active"]],
                        hide_index=True, use_container_width=True,
                    )

        with tab_mem:
            err = st.session_state.get("_fm_sync_error")
            if err:
                st.warning(f"Fraud memory API: {html.escape(str(err))}")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Refresh from API", key="fm_refresh_api", help="GET /v1/fraud-memory?view=patterns&filter=all"):
                    sync_fraud_memory_from_api(force=True)
                    st.rerun()
            with c2:
                if st.button("Load demo JSON (fixtures)", key="fm_load_demo_json"):
                    st.session_state.fraud_memory = load_json("fraud_memory.json")
                    st.rerun()
            if mem:
                for p in mem:
                    c = p.get("confidence", 0)
                    cc = "#ef4444" if c > 0.85 else "#f59e0b" if c > 0.7 else "#3b82f6"
                    st.markdown(
                        f'<div class="memory-row">'
                        f'<span class="memory-type">{html.escape(str(p.get("pattern_type", "?")))}</span>'
                        f'<span class="memory-val">{html.escape(str(p.get("entity_id", "?")))}</span>'
                        f'<span style="margin-left:auto;font-size:.72rem;color:#4a6080;">'
                        f'conf: <b style="color:{cc};">{c}</b> &nbsp;·&nbsp; '
                        f'risk: <b style="color:{cc};">{p.get("risk_score","?")}</b> &nbsp;·&nbsp; '
                        f'{html.escape(str(p.get("description","")))}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div class="info-panel">No fraud-memory patterns from the API yet. '
                    "After HITL / deep investigation persists patterns, use <b>Refresh from API</b>. "
                    "For a scripted demo only, use <b>Load demo JSON</b>.</div>",
                    unsafe_allow_html=True,
                )

        with tab_cust:
            df_cu = pd.DataFrame(custs)
            st.dataframe(
                df_cu[["customer_id", "name", "account_type", "risk_profile", "total_transactions", "total_amount", "last_login"]],
                hide_index=True, use_container_width=True,
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        action_button("→ Proceed to Stage 02", "s1_next", 2)

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — GENERATE ALERT
# ─────────────────────────────────────────────────────────────────────────────
def stage_generate_alert() -> None:
    stage_hero(
        2,
        "Promote a signal into an operational alert",
        "POST /v1/alerts exercises the same intake contract your channels team would call — payload validation, idempotency hooks, and correlation identifiers for downstream work.",
        badge_label="API · POST /v1/alerts",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        txns = [t for t in st.session_state.transactions if t.get("risk_indicators")]

        st.markdown('<span class="section-label">Suspicious Transactions</span>', unsafe_allow_html=True)
        for t in txns:
            country    = t["destination_country"]
            risk_level = "CRITICAL" if country in HIGH_RISK else "HIGH" if country in MED_RISK else "MEDIUM"
            rc         = "#ef4444" if risk_level == "CRITICAL" else "#f59e0b" if risk_level == "HIGH" else "#3b82f6"
            inds       = t.get("risk_indicators") or []
            inds_pills = " ".join(
                f'<span style="background:rgba(239,68,68,.1);color:#fca5a5;border:1px solid rgba(239,68,68,.25);'
                f'padding:.12rem .45rem;border-radius:5px;font-size:.62rem;font-weight:700;">{html.escape(str(i))}</span>'
                for i in inds
            )
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(
                    f'<div class="alert-card {risk_level.lower()}">'
                    f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;">'
                    f'{pill(risk_level, risk_level)}'
                    f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.82rem;font-weight:700;color:#f0f6ff;">{html.escape(t["transaction_id"])}</span>'
                    f'<span style="color:#4a6080;font-size:.75rem;">{html.escape(t["customer_id"])}</span>'
                    f'</div>'
                    f'<div style="font-size:1.1rem;font-weight:800;color:{rc};margin-bottom:.35rem;">'
                    f'${t["amount"]:,.2f} <span style="font-size:.72rem;color:#4a6080;">{html.escape(t.get("currency","USD"))}</span>'
                    f' → <span style="color:#f0f6ff;">{html.escape(country)}</span>'
                    f' <span style="font-size:.75rem;color:#4a6080;">· {html.escape(t.get("transaction_type","transfer"))}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;">'
                    f'<span style="font-size:.68rem;color:#4a6080;">🚩</span>{inds_pills}'
                    f'<span style="font-size:.68rem;color:#4a6080;margin-left:.25rem;">{html.escape(t.get("timestamp",""))}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("🚨 Flag Alert", key=f"flag_{t['transaction_id']}", use_container_width=True, type="primary"):
                    with st.spinner("Validating payload and calling intake API…"):
                        _create_alert_from_transaction(t)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">Simulate Custom Alert</span>', unsafe_allow_html=True)
        with st.form("custom_alert"):
            col1, col2, col3 = st.columns(3)
            cust_id = col1.selectbox("Customer", [c["customer_id"] for c in st.session_state.customers] or ["CUST001", "CUST002", "CUST003"])
            amount  = col2.number_input("Amount (USD)", value=15000.0, min_value=100.0)
            country = col3.selectbox("Destination Country", ["IR", "KP", "RU", "CN", "US", "NG", "SY", "BY"])
            if st.form_submit_button("Generate Custom Alert", type="primary"):
                import random
                t = {
                    "transaction_id": f"TXN-{uuid.uuid4().hex[:6].upper()}",
                    "customer_id": cust_id, "amount": amount, "currency": "USD",
                    "timestamp": utcnow_iso(), "destination_country": country,
                    "device_id": f"DEV-{uuid.uuid4().hex[:6].upper()}",
                    "ip_address": f"185.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
                    "risk_indicators": ["custom_alert"],
                }
                _create_alert_from_transaction(t)

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _create_alert_from_transaction(t: dict) -> None:
    alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
    inv_id   = f"inv_{uuid.uuid4().hex[:10]}"

    payload = {
        "transaction_id": t["transaction_id"],
        "amount": t["amount"], "currency": t.get("currency", "USD"),
        "timestamp": t.get("timestamp", utcnow_iso()),
        "account_id": t["customer_id"],
        "recipient_country": t["destination_country"],
        "alert_hash": uuid.uuid4().hex,
        "metadata": {
            "device_id": t.get("device_id", ""),
            "ip_address": t.get("ip_address", ""),
            "walkthrough_alert_id": alert_id,
        },
    }
    resp = api_post("/v1/alerts", payload)
    api_ok = bool(resp.get("investigation_id")) or bool(resp.get("status"))
    if resp.get("investigation_id"):
        inv_id = resp["investigation_id"]
    if resp.get("alert_id"):
        alert_id = resp["alert_id"]

    severity = "CRITICAL" if t["destination_country"] in HIGH_RISK else "HIGH" if t["destination_country"] in MED_RISK else "MEDIUM"
    alert = {
        "alert_id": alert_id, "investigation_id": inv_id,
        "transaction_id": t["transaction_id"], "customer_id": t["customer_id"],
        "amount": t["amount"], "currency": t.get("currency", "USD"),
        "destination_country": t["destination_country"],
        "device_id": t.get("device_id", "UNKNOWN"), "ip_address": t.get("ip_address", ""),
        "risk_indicators": t.get("risk_indicators", []),
        "severity": severity, "status": "NEW", "created_at": utcnow_iso(),
        "triage_result": None, "agent_results": None, "risk_result": None,
        "hitl_decision": None, "frozen": False, "approved": False,
        "api_response": resp,
    }
    st.session_state.alerts.append(alert)
    st.session_state.selected_alert_id = alert_id
    st.session_state.metrics["total_alerts"] += 1
    trace(f"ALERT_GENERATED · {alert_id} · API={'OK' if api_ok else 'FALLBACK'} · txn={t['transaction_id']} · ${t['amount']:,.0f}")
    st.toast(f"Alert {alert_id} created", icon="🚨")
    st.session_state.stage = 3
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — ALERTS QUEUE
# ─────────────────────────────────────────────────────────────────────────────
def stage_alerts_queue() -> None:
    stage_hero(
        3,
        "Operations queue with analyst-ready context",
        "Severity, monetary exposure, corridor risk, and freshness are visible at a glance — mirroring how a floor lead triages work before specialists burn cycles.",
        badge_label="Work queue",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        alerts = st.session_state.alerts
        if not alerts:
            st.markdown(
                '<div class="info-panel">No alerts in this session yet. Use <b>Stage 02</b> to raise the first case.</div>',
                unsafe_allow_html=True,
            )
            return

        total  = len(alerts)
        crit   = sum(1 for a in alerts if a["severity"] == "CRITICAL")
        new    = sum(1 for a in alerts if a["status"] == "NEW")
        closed = sum(1 for a in alerts if a["status"] == "CLOSED")

        st.markdown(
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem;margin-bottom:1.5rem;">'
            f'<div class="stat-card"><div class="stat-value" style="color:#f0f6ff;">{total}</div><div class="stat-label">Total</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{crit}</div><div class="stat-label">Critical</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#f59e0b;">{new}</div><div class="stat-label">New</div></div>'
            f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{closed}</div><div class="stat-label">Closed</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            sort_by = st.selectbox("Sort by", ["Amount (High→Low)", "Amount (Low→High)", "Severity", "Created Time"], key="sort_alerts")
        with col2:
            filter_severity = st.selectbox("Filter severity", ["All", "CRITICAL", "HIGH", "MEDIUM"], key="filter_severity")

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        if sort_by == "Amount (High→Low)":
            alerts_sorted = sorted(alerts, key=lambda x: x.get("amount", 0), reverse=True)
        elif sort_by == "Amount (Low→High)":
            alerts_sorted = sorted(alerts, key=lambda x: x.get("amount", 0))
        elif sort_by == "Severity":
            alerts_sorted = sorted(alerts, key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 3))
        else:
            alerts_sorted = sorted(alerts, key=lambda x: x.get("created_at", ""), reverse=True)

        if filter_severity != "All":
            alerts_sorted = [a for a in alerts_sorted if a.get("severity") == filter_severity]

        for a in alerts_sorted:
            is_sel     = st.session_state.selected_alert_id == a["alert_id"]
            severity   = a.get("severity", "MEDIUM")
            card_cls   = f'alert-card {severity.lower()}' + (" selected" if is_sel else "")
            rc         = "#ef4444" if severity == "CRITICAL" else "#f59e0b" if severity == "HIGH" else "#3b82f6"
            inds       = a.get("risk_indicators") or []
            inds_pills = " ".join(
                f'<span style="background:rgba(239,68,68,.1);color:#fca5a5;border:1px solid rgba(239,68,68,.25);'
                f'padding:.1rem .4rem;border-radius:4px;font-size:.6rem;font-weight:700;">{html.escape(str(i))}</span>'
                for i in inds
            ) if inds else ""

            st.markdown(
                f'<div class="{card_cls}">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem;">'
                f'<div style="display:flex;align-items:center;gap:.5rem;">'
                f'{pill(severity, severity)} {pill(a.get("status","NEW"), a.get("status","NEW"))}'
                f'</div>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.78rem;color:#4a6080;">{html.escape(a["alert_id"])}</span>'
                f'</div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.5rem;">'
                f'<div><div style="font-size:.65rem;color:#4a6080;margin-bottom:.15rem;">CUSTOMER</div>'
                f'<div style="font-weight:700;color:#f0f6ff;font-size:.88rem;">{html.escape(a.get("customer_id","?"))}</div></div>'
                f'<div><div style="font-size:.65rem;color:#4a6080;margin-bottom:.15rem;">AMOUNT → DESTINATION</div>'
                f'<div style="font-size:1.05rem;font-weight:800;color:{rc};">${a.get("amount",0):,.2f} → {html.escape(a.get("destination_country","?"))}</div></div>'
                f'</div>'
                f'<div style="display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;">{inds_pills}</div>'
                f'<div style="font-size:.68rem;color:#4a6080;margin-top:.4rem;">{html.escape(a.get("created_at",""))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Investigate →", key=f"inv_{a['alert_id']}", use_container_width=True):
                st.session_state.selected_alert_id = a["alert_id"]
                st.session_state.stage = 4
                trace(f"INVESTIGATION_STARTED · {a['alert_id']}")
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("+ Generate Another Alert", key="more_alerts"):
            st.session_state.stage = 2
            st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — TRIAGE
# ─────────────────────────────────────────────────────────────────────────────
def stage_triage(alert: dict) -> None:
    stage_hero(
        4,
        "Policy-first triage, then model assist",
        "Fast-path rules keep spend predictable; when the case warrants it, ``POST /v1/triage/assess`` runs deterministic triage with an optional fast-model narrative. Falls back to transparent rule scoring if the model is unavailable.",
        badge_label="API · POST /v1/triage/assess",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        st.markdown(
            f'<div class="info-panel">🔍 Alert <b>{html.escape(alert["alert_id"])}</b> &nbsp;·&nbsp; '
            f'Customer <b>{html.escape(alert["customer_id"])}</b> &nbsp;·&nbsp; '
            f'<b>${alert["amount"]:,.2f}</b> → <b>{html.escape(alert["destination_country"])}</b></div>',
            unsafe_allow_html=True,
        )

        customer   = next((c for c in st.session_state.customers if c["customer_id"] == alert["customer_id"]), {})
        kyc_events = [k for k in st.session_state.kyc_events if k["customer_id"] == alert["customer_id"]]
        mem_hits   = [m for m in st.session_state.fraud_memory if m.get("entity_id") == alert["customer_id"]]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<span class="section-label">Customer Profile</span>', unsafe_allow_html=True)
            if customer:
                rp = customer.get("risk_profile", "?")
                rc = "#ef4444" if rp == "high" else "#f59e0b" if rp == "medium" else "#10b981"
                st.markdown(
                    f'<div class="summary-card">'
                    f'<div class="summary-row"><span class="sk">Name</span><span class="sv">{html.escape(customer.get("name","?"))}</span></div>'
                    f'<div class="summary-row"><span class="sk">Account</span><span class="sv">{html.escape(customer.get("account_type","?").upper())}</span></div>'
                    f'<div class="summary-row"><span class="sk">Risk Profile</span><span class="sv" style="color:{rc};">{html.escape(rp.upper())}</span></div>'
                    f'<div class="summary-row"><span class="sk">Total Txns</span><span class="sv">{customer.get("total_transactions",0):,}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with col2:
            st.markdown('<span class="section-label">KYC Anomalies</span>', unsafe_allow_html=True)
            rows = "".join(
                f'<div class="summary-row"><span class="sk">{html.escape(k["anomaly_type"].replace("_"," "))}</span>'
                f'<span class="sv" style="color:#f59e0b;">{k["risk_score"]}</span></div>'
                for k in kyc_events
            ) or '<div class="summary-row"><span class="sk">Status</span><span class="sv" style="color:#10b981;">✅ None</span></div>'
            st.markdown(f'<div class="summary-card">{rows}</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<span class="section-label">Fraud Memory Hits</span>', unsafe_allow_html=True)
            rows = "".join(
                f'<div class="summary-row"><span class="sk">{html.escape(m["pattern_type"].replace("_"," "))}</span>'
                f'<span class="sv" style="color:#ef4444;">{m["confidence"]}</span></div>'
                for m in mem_hits
            ) or '<div class="summary-row"><span class="sk">Status</span><span class="sv" style="color:#10b981;">✅ None</span></div>'
            st.markdown(f'<div class="summary-card">{rows}</div>', unsafe_allow_html=True)

        # Heuristic flags
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">Heuristic Flags</span>', unsafe_allow_html=True)
        flags = []
        if alert["destination_country"] in HIGH_RISK:
            flags.append(("🚩", "HIGH-RISK CORRIDOR", f"Destination {alert['destination_country']} is on the OFAC/EU sanctions watchlist"))
        if alert["amount"] > 10000:
            flags.append(("💰", "LARGE VALUE TRANSFER", f"${alert['amount']:,.2f} exceeds $10,000 reporting threshold"))
        if kyc_events:
            flags.append(("🔍", "KYC ANOMALIES PRESENT", f"{len(kyc_events)} anomalous KYC event(s) on record"))
        if mem_hits:
            flags.append(("🧠", "FRAUD MEMORY MATCH", f"{len(mem_hits)} prior fraud pattern(s) linked to this customer"))
        for icon, label, detail in flags:
            st.markdown(
                f'<div class="flag-row">'
                f'<span style="font-size:1rem;">{icon}</span>'
                f'<div><div class="flag-label">{html.escape(label)}</div>'
                f'<div class="flag-detail">{html.escape(detail)}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Mini gauge
        heuristic_score = min(1.0, 0.3 + (0.4 if alert["destination_country"] in HIGH_RISK else 0.2 if alert["destination_country"] in MED_RISK else 0) + (0.15 if alert["amount"] > 10000 else 0) + (0.1 if kyc_events else 0) + (0.1 if mem_hits else 0))
        pct = int(heuristic_score * 100)
        gc  = risk_gradient(heuristic_score)
        rc  = risk_color(heuristic_score)
        st.markdown(
            f'<div style="margin:.75rem 0;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:.3rem;">'
            f'<span style="font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#4a6080;">Heuristic Risk Score</span>'
            f'<span style="font-size:.9rem;font-weight:800;color:{rc};font-family:\'JetBrains Mono\',monospace;">{pct}/100</span>'
            f'</div>'
            f'<div class="gauge-track"><div class="gauge-fill" style="width:{pct}%;background:{gc};"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<hr>", unsafe_allow_html=True)

        if alert.get("triage_result"):
            tr = alert["triage_result"]
            _show_triage_result(tr)
            st.markdown("<hr>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ AUTO_CLOSE — Dismiss", use_container_width=True, key="triage_close2"):
                    alert["status"] = "CLOSED"
                    st.session_state.metrics["auto_closed"] += 1
                    trace(f"TRIAGE → AUTO_CLOSE · {alert['alert_id']}")
                    st.rerun()
            with c2:
                if st.button("🚀 ESCALATE — Launch Investigation", type="primary", use_container_width=True, key="triage_esc2"):
                    alert["status"] = "INVESTIGATING"
                    st.session_state.stage = 5
                    st.rerun()
            return

        if st.button("▶ Run triage (assess)", type="primary", key="run_triage"):
            with st.spinner("Calling POST /v1/triage/assess; applying rule-based fallback if needed…"):
                params = {"customer_id": alert["customer_id"], "alert_id": alert["alert_id"]}
                body = {"include_initial_suspicion_note": True}
                resp = api_post("/v1/triage/assess", body, params=params, timeout=120)

            if resp.get("success") is False:
                st.markdown(f'<div class="warn-panel">⚠ API call failed: {html.escape(str(resp.get("error","unknown")))}. Using rule-based fallback.</div>', unsafe_allow_html=True)
                score = 0.3
                country = alert["destination_country"]
                if country in HIGH_RISK:
                    score += 0.4
                elif country in MED_RISK:
                    score += 0.2
                if alert["amount"] > 10000:
                    score += 0.2
                if kyc_events:
                    score += 0.1
                if mem_hits:
                    score += 0.15
                score = min(score, 1.0)
                tr = {
                    "decision": "ESCALATE_FOR_INVESTIGATION" if score > 0.5 else "AUTO_CLOSE",
                    "priority": "CRITICAL" if score > 0.8 else "HIGH" if score > 0.6 else "MEDIUM",
                    "risk_score": round(score, 2),
                    "confidence": 0.75,
                    "reasoning": "Rule-based fallback (triage API unavailable).",
                    "key_flags": alert["risk_indicators"],
                }
                alert["triage_result"] = tr
                trace(f"TRIAGE_FALLBACK → decision={tr['decision']} · score={tr['risk_score']}")
                _show_triage_result(tr)
            else:
                assessed = resp.get("assessed_alerts") or []
                tr = _legacy_triage_from_assessed(assessed, alert["alert_id"])
                if tr:
                    alert["triage_result"] = tr
                    trace(
                        f"TRIAGE_API → decision={tr.get('decision')} · score={tr.get('risk_score')} · "
                        f"confidence={tr.get('confidence')}"
                    )
                    st.markdown(
                        f'<div style="margin-bottom:.5rem;">{api_badge("POST /v1/triage/assess")}</div>',
                        unsafe_allow_html=True,
                    )
                    _show_triage_result(tr)
                else:
                    st.markdown(
                        f'<div class="warn-panel">⚠ Triage returned no row for this alert_id. '
                        f"Run <b>POST /v1/alerts/generate</b> or ingest so the alert exists in the merged store, "
                        f"then retry.</div>",
                        unsafe_allow_html=True,
                    )
                    score = 0.35
                    country = alert["destination_country"]
                    if country in HIGH_RISK:
                        score += 0.35
                    elif country in MED_RISK:
                        score += 0.2
                    if alert["amount"] > 10000:
                        score += 0.15
                    score = min(score, 1.0)
                    tr = {
                        "decision": "ESCALATE_FOR_INVESTIGATION" if score > 0.55 else "AUTO_CLOSE",
                        "priority": "HIGH" if score > 0.65 else "MEDIUM",
                        "risk_score": round(score, 2),
                        "confidence": 0.7,
                        "reasoning": "Local fallback — alert not found in triage batch.",
                        "key_flags": alert["risk_indicators"],
                    }
                    alert["triage_result"] = tr
                    trace(f"TRIAGE_FALLBACK_NO_ROW → decision={tr['decision']} · score={tr['risk_score']}")
                    _show_triage_result(tr)
            st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _show_triage_result(tr: dict) -> None:
    score    = tr.get("risk_score", 0)
    pct      = int(score * 100)
    gc       = risk_gradient(score)
    rc       = risk_color(score)
    decision = tr.get("decision", "?")
    priority = tr.get("priority", "?")
    conf_pct = int(tr.get("confidence", 0) * 100)
    dec_color = "#ef4444" if "ESCALATE" in decision else "#10b981"

    st.markdown('<span class="section-label">Triage Result</span>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(
            f'<div class="risk-display" style="padding:1.2rem;">'
            f'<div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#4a6080;margin-bottom:.4rem;">Risk Score</div>'
            f'<div style="font-size:3rem;font-weight:800;color:{rc};font-family:\'JetBrains Mono\',monospace;line-height:1;">{pct}</div>'
            f'<div style="font-size:.68rem;color:{rc};font-weight:700;text-transform:uppercase;margin-top:.2rem;">{html.escape(priority)}</div>'
            f'<div class="gauge-track" style="margin:.6rem 0 .3rem;"><div class="gauge-fill" style="width:{pct}%;background:{gc};"></div></div>'
            f'<div style="font-size:.68rem;color:#4a6080;">Confidence: <b style="color:#10b981;">{conf_pct}%</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="summary-card">'
            f'<div class="summary-row"><span class="sk">Decision</span>'
            f'<span class="sv" style="color:{dec_color};font-size:.88rem;">{html.escape(decision.replace("_"," "))}</span></div>'
            f'<div class="summary-row"><span class="sk">Priority</span>'
            f'<span class="sv" style="color:{rc};">{html.escape(priority)}</span></div>'
            f'<div class="summary-row"><span class="sk">Risk Score</span>'
            f'<span class="sv" style="color:{rc};">{pct}/100</span></div>'
            f'<div class="summary-row"><span class="sk">Confidence</span>'
            f'<span class="sv" style="color:#10b981;">{conf_pct}%</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # AI Reasoning — shown prominently
    if tr.get("reasoning"):
        st.markdown('<span class="section-label" style="margin-top:.75rem;">AI Reasoning</span>', unsafe_allow_html=True)
        with st.chat_message("assistant"):
            st.markdown(
                f"**Triage Decision: {decision.replace('_',' ')}** (score {pct}/100, confidence {conf_pct}%)\n\n"
                f"{tr['reasoning']}"
            )

    if tr.get("key_flags"):
        st.markdown('<span class="section-label" style="margin-top:.5rem;">Key Flags</span>', unsafe_allow_html=True)
        for flag in tr["key_flags"]:
            st.markdown(
                f'<div class="flag-row">'
                f'<span style="font-size:.9rem;">🚩</span>'
                f'<div><div class="flag-label">{html.escape(str(flag).upper().replace("_"," "))}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    if tr.get("key_flags"):
        for flag in tr["key_flags"]:
            st.markdown(
                f'<div class="flag-row">'
                f'<span style="font-size:.9rem;">🚩</span>'
                f'<div><div class="flag-label">{html.escape(str(flag).upper().replace("_"," "))}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — PARALLEL AGENT INVESTIGATION
# ─────────────────────────────────────────────────────────────────────────────
def stage_agents(alert: dict) -> None:
    stage_hero(
        5,
        "Specialist agents gather evidence in parallel",
        "Transaction velocity, device/geo behaviour, and sanctions posture are collected concurrently — each stream stays explainable so risk committees can replay the logic.",
        badge_label="Concurrency · asyncio.gather",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        st.markdown(
            f'<div class="info-panel">🔍 Case <b>{html.escape(alert["investigation_id"])}</b> &nbsp;·&nbsp; '
            f'{html.escape(alert["customer_id"])} &nbsp;·&nbsp; '
            f'<b>${alert["amount"]:,.2f}</b> → <b>{html.escape(alert["destination_country"])}</b></div>',
            unsafe_allow_html=True,
        )

        if alert.get("agent_results"):
            _show_agent_cards(alert["agent_results"])
            st.markdown("<hr>", unsafe_allow_html=True)
            if st.button("→ Proceed to AI Risk Scoring", type="primary", key="to_scoring"):
                st.session_state.stage = 6
                st.rerun()
            return

        if st.button("▶ Launch Parallel Agents", type="primary", key="run_agents"):
            col1, col2, col3 = st.columns(3)
            with col1:
                with st.status("⚡ Transaction Agent", expanded=True) as s1:
                    st.write("Analyzing transaction patterns…")
                    time.sleep(0.2)
                    st.write(f"High-value transfer detected: ${alert.get('amount', 15000):,.2f}")
                    time.sleep(0.2)
                    st.write("Velocity spike pattern identified")
                    time.sleep(0.2)
                    st.write("Comparing to customer baseline…")
                    s1.update(label="⚡ Transaction Agent", state="running")
            with col2:
                with st.status("🔍 KYC / Device Agent", expanded=True) as s2:
                    st.write("Analyzing device logs…")
                    time.sleep(0.2)
                    st.write(f"Device fingerprint: {html.escape(alert.get('device_id','?'))}")
                    time.sleep(0.2)
                    st.write("Geo-location anomaly check…")
                    time.sleep(0.2)
                    st.write("Login pattern deviation flagged")
                    s2.update(label="🔍 KYC Agent", state="running")
            with col3:
                with st.status("🚫 Sanctions Agent", expanded=True) as s3:
                    st.write("High-risk corridor check…")
                    time.sleep(0.2)
                    st.write(f"Checking destination: {html.escape(alert.get('destination_country','?'))}")
                    time.sleep(0.2)
                    st.write("Screening against OFAC/EU/UN lists…")
                    time.sleep(0.2)
                    st.write("Entity match analysis complete")
                    s3.update(label="🚫 Sanctions Agent", state="running")

            max_retries = 3
            resp = {}
            for attempt in range(max_retries):
                try:
                    with st.spinner("Synthesizing all agent findings…"):
                        if attempt > 0:
                            st.info(f"Reconnecting… (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(1)
                        resp = api_post(
                            "/v1/investigation/customer-langgraph-deep",
                            {
                                "customer_id": alert["customer_id"],
                                "alert_id": alert["alert_id"],
                                "include_hitl_recommendation": True,
                                "persist_fraud_memory": False,
                            },
                            timeout=180,
                        )
                        break
                except Exception:
                    if attempt == max_retries - 1:
                        resp = {"success": False, "error": "Service unavailable after retries"}

            if resp.get("success") and resp.get("data"):
                data = resp["data"]
                alert["agent_results"] = data.get("agent_results", {})
                alert["risk_result"] = data.get("risk_result", {})
                alert["ai_synthesis"] = data.get("llm_investigation_synthesis") or data.get("ai_synthesis", {})
                srv_inv = data.get("investigation_id")
                if srv_inv:
                    alert["investigation_id"] = srv_inv
                s1.update(label="✅ Transaction Agent — Complete", state="complete")
                s2.update(label="⚠️ KYC Agent — Anomalies Found", state="complete")
                s3.update(label="🔴 Sanctions Agent — Match Found", state="complete")
                trace(f"AGENTS_COMPLETE · investigation={data.get('investigation_id')} · API=OK")
                trace(f"TRANSACTION_AGENT → risk={data.get('agent_results',{}).get('transaction',{}).get('risk_score','?')}")
                trace(f"KYC_AGENT → anomalies={len(data.get('agent_results',{}).get('kyc',{}).get('anomalies',[]))}")
                trace(f"SANCTIONS_AGENT → risk={data.get('agent_results',{}).get('sanctions',{}).get('risk_score','?')}")
                st.markdown(
                    f'<div style="margin:.5rem 0;">{api_badge("POST /v1/investigation/customer-langgraph-deep")}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<div class="warn-panel">⚠ API call failed: {html.escape(str(resp.get("error","unknown")))}. Using local data fallback.</div>', unsafe_allow_html=True)
                alert["agent_results"] = _build_local_agent_results(alert)
                s1.update(label="✅ Transaction Agent (local)", state="complete")
                s2.update(label="⚠️ KYC Agent (local)", state="complete")
                s3.update(label="🔴 Sanctions Agent (local)", state="complete")
                trace("AGENTS_FALLBACK · local data used")

            st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _build_local_agent_results(alert: dict) -> dict:
    cust_id    = alert["customer_id"]
    country    = alert["destination_country"]
    amount     = alert["amount"]
    kyc_events = [k for k in st.session_state.kyc_events if k["customer_id"] == cust_id]
    mem_hits   = [m for m in st.session_state.fraud_memory if m.get("entity_id") == cust_id]
    san        = st.session_state.sanctions
    country_risks = {c["country_code"]: c for c in (san.get("country_risks", []) if isinstance(san, dict) else [])}
    cr = country_risks.get(country, {})
    return {
        "transaction": {
            "risk_score": min(1.0, amount / 50000),
            "velocity_metrics": {"amount": amount},
            "velocity_anomalies": [{"pattern": ri} for ri in alert["risk_indicators"]],
            "fraud_patterns": [{"pattern_type": m["pattern_type"]} for m in mem_hits],
            "recommendation": "BLOCK_TRANSACTION" if amount > 10000 else "FLAG_FOR_REVIEW",
        },
        "kyc": {
            "risk_score": max((k["risk_score"] for k in kyc_events), default=0.1),
            "anomalies": [{"anomaly_type": k["anomaly_type"], "severity": "high"} for k in kyc_events],
            "recommendation": "REQUIRE_ADDITIONAL_VERIFICATION" if kyc_events else "APPROVE",
        },
        "sanctions": {
            "risk_score": cr.get("risk_score", 0.1),
            "alerts": [{"sanction_type": "COUNTRY_SANCTION", "risk_score": cr.get("risk_score", 0.1)}] if country in HIGH_RISK else [],
            "recommendation": "BLOCK_TRANSACTION" if country in HIGH_RISK else "MONITOR",
        },
    }


def _show_agent_cards(results: dict) -> None:
    tx  = results.get("transaction") or {}
    kyc = results.get("kyc") or {}
    san = results.get("sanctions") or {}

    def _fv(v: Any) -> str:
        if isinstance(v, bool):
            return f'<span class="fv fv-{"t" if v else "f"}">{"TRUE" if v else "false"}</span>'
        if isinstance(v, float):
            cls = "fv-h" if v > 0.7 else "fv-m" if v > 0.4 else "fv-t"
            return f'<span class="fv {cls}">{v:.2f}</span>'
        return f'<span class="fv" style="color:#8ba3c7;">{html.escape(str(v))}</span>'

    def _card(title: str, color: str, state: str, rows: list) -> str:
        rows_html = "".join(
            f'<div class="agent-finding"><span class="fk">{html.escape(str(k))}</span>{_fv(v)}</div>'
            for k, v in rows
        )
        return (
            f'<div class="agent-card {state} fadeInUp">'
            f'<div class="agent-name" style="color:{color};">{html.escape(title)}</div>'
            f'{rows_html}</div>'
        )

    tx_score  = tx.get("risk_score", 0)
    kyc_score = kyc.get("risk_score", 0)
    san_score = san.get("risk_score", 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            _card(
                "⚡ Transaction Agent",
                "#10b981" if tx_score < 0.5 else "#f59e0b" if tx_score < 0.7 else "#ef4444",
                "success" if tx_score < 0.5 else "warning" if tx_score < 0.7 else "danger",
                [
                    ("risk_score", tx_score),
                    ("velocity_anomalies", len(tx.get("velocity_anomalies", []))),
                    ("fraud_patterns", len(tx.get("fraud_patterns", []))),
                    ("recommendation", tx.get("recommendation", "?")),
                ],
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _card(
                "🔍 KYC / Device Agent",
                "#10b981" if kyc_score < 0.4 else "#f59e0b" if kyc_score < 0.7 else "#ef4444",
                "success" if kyc_score < 0.4 else "warning" if kyc_score < 0.7 else "danger",
                [
                    ("risk_score", kyc_score),
                    ("anomalies_found", len(kyc.get("anomalies", []))),
                    ("recommendation", kyc.get("recommendation", "?")),
                ],
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _card(
                "🚫 Sanctions Agent",
                "#10b981" if san_score < 0.4 else "#f59e0b" if san_score < 0.7 else "#ef4444",
                "success" if san_score < 0.4 else "warning" if san_score < 0.7 else "danger",
                [
                    ("risk_score", san_score),
                    ("sanctions_alerts", len(san.get("alerts", []))),
                    ("recommendation", san.get("recommendation", "?")),
                ],
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — AI REASONING & RISK SCORING
# ─────────────────────────────────────────────────────────────────────────────
def stage_risk_scoring(alert: dict) -> None:
    def _unit_interval(x: Any, default: float) -> float:
        v = x if x is not None else default
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = float(default)
        if f > 1.0:
            f = f / 100.0
        return max(0.0, min(1.0, f))

    stage_hero(
        6,
        "Hybrid scoring with an auditable narrative",
        "POST /v1/investigation/customer-langgraph-deep runs LangGraph agents plus synthesis so you can show both structured scores and narrative.",
        badge_label="Gemini synthesis",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        rr = alert.get("risk_result") or {}

        raw_final   = rr.get("final_risk_score") or rr.get("risk_score") or 0.5
        final_score = _unit_interval(raw_final, 0.5)
        risk_tier   = rr.get("risk_tier") or rr.get("risk_level") or "MEDIUM"
        confidence  = _unit_interval(rr.get("confidence"), 0.7)
        rule_raw = rr.get("rule_based_score")
        if rule_raw is None:
            rule_raw = rr.get("rule_score")
        if rule_raw is not None:
            rule_score = _unit_interval(rule_raw, 0.5)
            rule_pct = int(rule_score * 100)
            rule_sv = f"{rule_pct}/100"
            rule_c = risk_color(rule_score)
        else:
            rule_score = None
            rule_sv = "—"
            rule_c = "#64748b"
        summary     = rr.get("executive_summary", rr.get("explanation"))
        if not summary:
            try:
                from app.services.ai_reasoning_service import InvestigationReasoningService
                ai_service = InvestigationReasoningService()
                ai_result  = ai_service.generate_executive_summary(alert)
                summary    = ai_result.get("summary", "AI analysis in progress…")
            except Exception as e:
                summary = f"AI analysis unavailable: {e}"
        evidence  = rr.get("evidence_chain", [])
        reasoning = rr.get("reasoning_steps", [])

        pct    = int(final_score * 100)
        rc     = risk_color(final_score)
        gc     = risk_gradient(final_score)
        conf_p = int(confidence * 100)

        col_gauge, col_scores = st.columns([1, 2])
        with col_gauge:
            st.markdown(
                f'<div class="risk-display">'
                f'<div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#4a6080;margin-bottom:.5rem;">Final Risk Score</div>'
                f'<div class="risk-number" style="color:{rc};">{pct}</div>'
                f'<div style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{rc};margin-top:.3rem;">{html.escape(risk_tier)}</div>'
                f'<div class="gauge-track"><div class="gauge-fill" style="width:{pct}%;background:{gc};"></div></div>'
                f'<div style="font-size:.7rem;color:#4a6080;margin-top:.3rem;">Confidence: <b style="color:#10b981;">{conf_p}%</b></div>'
                f'<div class="gauge-track" style="margin-top:4px;"><div style="height:100%;width:{conf_p}%;background:linear-gradient(90deg,#10b981,#059669);border-radius:4px;"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_scores:
            st.markdown('<span class="section-label">Score Breakdown</span>', unsafe_allow_html=True)
            human_req = pct >= 70
            st.markdown(
                f'<div class="summary-card">'
                f'<div class="summary-row"><span class="sk">Pipeline risk (LangGraph)</span>'
                f'<span class="sv" style="color:{rule_c};">{html.escape(rule_sv)}</span></div>'
                f'<div class="summary-row"><span class="sk">Final risk (LLM synthesis)</span>'
                f'<span class="sv" style="color:{rc};">{pct}/100</span></div>'
                f'<div class="summary-note">Final is the holistic fraud risk from synthesis (narrative + evidence). '
                f"It is not a separate RAG or &quot;context coverage&quot; index.</div>"
                f'<div class="summary-row"><span class="sk">Confidence</span><span class="sv" style="color:#10b981;">{conf_p}%</span></div>'
                f'<div class="summary-row"><span class="sk">Risk Tier</span><span class="sv" style="color:{rc};">{html.escape(risk_tier)}</span></div>'
                f'<div class="summary-row"><span class="sk">Requires Human Review</span>'
                f'<span class="sv" style="color:{"#ef4444" if human_req else "#10b981"};">{"YES" if human_req else "NO"}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if evidence:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">Evidence Chain</span>', unsafe_allow_html=True)
            for e in evidence:
                st.markdown(
                    f'<div class="evidence-card">'
                    f'<div class="evidence-reason">{html.escape(str(e.get("signal","?")))}</div>'
                    f'<div class="evidence-meta">source: {html.escape(str(e.get("source","?")))} &nbsp;·&nbsp; weight: {html.escape(str(e.get("weight","?")))} &nbsp;·&nbsp; {html.escape(str(e.get("detail","")))}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if reasoning:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">AI Reasoning Steps</span>', unsafe_allow_html=True)
            for i, step in enumerate(reasoning, 1):
                st.markdown(
                    f'<div style="padding:.5rem .8rem;margin-bottom:.35rem;border-radius:8px;background:#0d1b2e;border-left:3px solid #3b82f6;">'
                    f'<span style="font-size:.68rem;color:#3b82f6;font-weight:700;font-family:\'JetBrains Mono\',monospace;">STEP {i}</span> '
                    f'<span style="font-size:.82rem;color:#8ba3c7;">{html.escape(str(step))}</span></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">AI Executive Summary</span>', unsafe_allow_html=True)
        with st.chat_message("assistant"):
            st.markdown(f"**Risk Score: {pct}/100 — {risk_tier}** (confidence {conf_p}%)\n\n{summary}")

        trace(f"RISK_SCORING_DISPLAYED · score={pct} · tier={risk_tier} · confidence={conf_p}%")

        st.markdown("<hr>", unsafe_allow_html=True)
        if pct >= 70:
            st.markdown(
                f'<div class="hitl-alert pulse-amber">'
                f'<div class="hitl-title">⚠ Risk Threshold Exceeded — Routing to Human Analyst</div>'
                f'<div class="hitl-body">Score <b>{pct}/100</b> exceeds the auto-approve threshold of 70. '
                f'No remediation executes until an analyst confirms.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("→ Proceed to Human Review (HITL)", type="primary", key="to_hitl"):
                st.session_state.stage = 7
                trace(f"DECISION_ENGINE → HITL · score={pct}")
                st.rerun()
        else:
            st.markdown(
                '<div class="success-panel">✅ Risk score below threshold. Auto-approving — no human review required.</div>',
                unsafe_allow_html=True,
            )
            if st.button("→ Auto-Approve & Proceed to Resolution", type="primary", key="to_res_auto"):
                alert["approved"] = True
                alert["status"]   = "CLOSED"
                st.session_state.stage = 8
                trace(f"DECISION_ENGINE → AUTO_APPROVE · score={pct}")
                st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — HITL REVIEW
# ─────────────────────────────────────────────────────────────────────────────
def stage_hitl(alert: dict) -> None:
    stage_hero(
        7,
        "Human-in-the-loop control point",
        "Material actions wait for an analyst. Gemini prepares a structured briefing; the disposition recorded here is what downstream settlement systems should trust.",
        badge_label="Awaiting analyst",
        badge_ok=False,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        rr    = alert.get("risk_result") or {}
        score = int(float(rr.get("final_risk_score", rr.get("risk_score", 0.9))) * 100)
        conf  = int(float(rr.get("confidence", 0.9)) * 100)

        st.markdown(
            f'<div class="hitl-alert pulse-amber">'
            f'<div class="hitl-title">⚠ Human Intervention Required</div>'
            f'<div class="hitl-body">Risk score <b>{score}/100</b> · Confidence <b>{conf}%</b>. '
            f'No remediation executes until analyst confirms.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not alert.get("hitl_ai_recommendation"):
            if st.button("🤖 Get Gemini Recommendation", key="get_hitl_rec", type="primary"):
                with st.spinner("Generating structured briefing via POST /v1/investigation/hitl-recommendation…"):
                    payload = {
                        "investigation_id": alert["investigation_id"],
                        "customer_id":      alert["customer_id"],
                        "amount":           alert["amount"],
                        "destination_country": alert["destination_country"],
                        "agent_results":    alert.get("agent_results", {}),
                        "risk_result":      alert.get("risk_result", {}),
                    }
                    resp = api_post("/v1/investigation/hitl-recommendation", payload)
                if resp.get("success") and resp.get("data"):
                    alert["hitl_ai_recommendation"] = resp["data"]
                    trace(f"HITL_AI_REC → recommended={resp['data'].get('recommended_action')}")
                    st.markdown(
                        f'<div style="margin:.5rem 0;">{api_badge("POST /v1/investigation/hitl-recommendation")}</div>',
                        unsafe_allow_html=True,
                    )
                st.rerun()

        if alert.get("hitl_ai_recommendation"):
            rec        = alert["hitl_ai_recommendation"]
            rec_action = rec.get("recommended_action", "?")
            rec_conf   = int(float(rec.get("confidence", 0.8)) * 100)
            rec_color  = "#ef4444" if rec_action == "CONFIRM_FRAUD" else "#10b981" if rec_action == "FALSE_POSITIVE" else "#f59e0b"
            rec_label  = "CONFIRM FRAUD" if rec_action == "CONFIRM_FRAUD" else "FALSE POSITIVE" if rec_action == "FALSE_POSITIVE" else rec_action.replace("_", " ")

            # Structured recommendation card — not raw JSON
            st.markdown(
                f'<div style="background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.3);'
                f'border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:1rem;">'
                f'<div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
                f'color:#c4b5fd;margin-bottom:.75rem;">Gemini Analyst Recommendation</div>'
                # Recommendation + confidence
                f'<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem;">'
                f'<span style="font-size:1rem;font-weight:800;color:{rec_color};">{html.escape(rec_label)}</span>'
                f'<span style="font-size:.72rem;background:rgba(139,92,246,.15);color:#c4b5fd;'
                f'border:1px solid rgba(139,92,246,.3);border-radius:6px;padding:.15rem .5rem;font-weight:700;">'
                f'Confidence {rec_conf}%</span>'
                f'</div>'
                # Analyst briefing
                f'<div style="font-size:.83rem;color:#8ba3c7;line-height:1.6;margin-bottom:.75rem;'
                f'padding:.75rem;background:rgba(0,0,0,.2);border-radius:8px;">'
                f'{html.escape(str(rec.get("analyst_briefing", "")))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Supporting evidence as clean cards
            evidence_list = rec.get("supporting_evidence") or []
            if evidence_list:
                st.markdown('<span class="section-label">Supporting Evidence</span>', unsafe_allow_html=True)
                for i, ev in enumerate(evidence_list, 1):
                    st.markdown(
                        f'<div class="evidence-card">'
                        f'<div class="evidence-reason">'
                        f'<span style="color:#8b5cf6;font-family:\'JetBrains Mono\',monospace;font-size:.7rem;margin-right:.5rem;">{i:02d}</span>'
                        f'{html.escape(str(ev))}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Risk if wrong
            risk_if_wrong = rec.get("risk_if_wrong", "")
            if risk_if_wrong:
                st.markdown(
                    f'<div style="background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.2);'
                    f'border-radius:8px;padding:.65rem .9rem;margin-top:.5rem;">'
                    f'<span style="font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;'
                    f'color:#f59e0b;">Risk if incorrect</span><br>'
                    f'<span style="font-size:.78rem;color:#8ba3c7;">{html.escape(str(risk_if_wrong))}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<span class="section-label">Investigation Summary</span>', unsafe_allow_html=True)
            rc = risk_color(float(rr.get("final_risk_score", rr.get("risk_score", 0.9))))
            st.markdown(
                f'<div class="summary-card">'
                f'<div class="summary-row"><span class="sk">Alert ID</span><span class="sv">{html.escape(alert["alert_id"])}</span></div>'
                f'<div class="summary-row"><span class="sk">Customer</span><span class="sv">{html.escape(alert["customer_id"])}</span></div>'
                f'<div class="summary-row"><span class="sk">Amount</span><span class="sv">${alert["amount"]:,.2f} {html.escape(alert["currency"])}</span></div>'
                f'<div class="summary-row"><span class="sk">Destination</span><span class="sv">{html.escape(alert["destination_country"])}</span></div>'
                f'<div class="summary-row"><span class="sk">Risk Score</span><span class="sv" style="color:{rc};">{score}/100</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown('<span class="section-label">Agent Findings Summary</span>', unsafe_allow_html=True)
            ar = alert.get("agent_results") or {}
            if ar:
                tx_r  = (ar.get("transaction") or {}).get("risk_score", "?")
                kyc_r = (ar.get("kyc") or {}).get("risk_score", "?")
                san_r = (ar.get("sanctions") or {}).get("risk_score", "?")
                st.markdown(
                    f'<div class="summary-card">'
                    f'<div class="summary-row"><span class="sk">Transaction Risk</span><span class="sv">{tx_r}</span></div>'
                    f'<div class="summary-row"><span class="sk">KYC Risk</span><span class="sv">{kyc_r}</span></div>'
                    f'<div class="summary-row"><span class="sk">Sanctions Risk</span><span class="sv">{san_r}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<hr>", unsafe_allow_html=True)
        notes = st.text_area(
            "Analyst decision rationale (required for audit trail)",
            value="High-value transfer to sanctioned corridor with device and geo anomalies. Recommend account freeze.",
            height=90,
            key="hitl_notes",
        )

        # Two clear action buttons only
        st.markdown('<span class="section-label">Analyst Decision</span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Close as False Positive", use_container_width=True, key="hitl_approve"):
                alert["approved"] = True
                alert["status"]   = "CLOSED"
                alert["hitl_decision"] = {"decision": "FALSE_POSITIVE", "notes": notes}
                st.session_state.metrics["auto_closed"] += 1
                trace(f"HITL → FALSE_POSITIVE · notes={notes[:50]}")
                st.session_state.stage = 8
                st.rerun()
        with c2:
            if st.button("🔒 Confirm Fraud — Freeze Account", type="primary", use_container_width=True, key="hitl_freeze"):
                alert["frozen"] = True
                alert["status"] = "CLOSED"
                alert["hitl_decision"] = {"decision": "CONFIRM_FRAUD", "notes": notes}
                st.session_state.metrics["confirmed_fraud"] += 1
                st.session_state.metrics["blocked"] += 1
                trace(f"HITL → CONFIRM_FRAUD · account={alert['customer_id']}")
                st.session_state.stage = 8
                st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────
def stage_resolution(alert: dict) -> None:
    stage_hero(
        8,
        "Controlled remediation and memory updates",
        "Actions are emitted through the resolution service so each step is idempotent, logged, and reversible. Fraud memory captures confirmed indicators for the next detection cycle.",
        badge_label="Action engine",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        frozen   = alert.get("frozen", False) if alert else False
        approved = alert.get("approved", False) if alert else False

        if frozen:
            st.markdown(
                f'<div class="success-panel" style="font-size:.95rem;font-weight:700;">'
                f'✅ Fraud Confirmed — Account {html.escape(alert["customer_id"])} Frozen</div>',
                unsafe_allow_html=True,
            )

            actions = [
                ("freeze_account",      f"Account {alert['customer_id']} frozen — outgoing transfers blocked"),
                ("reverse_transaction", f"Transaction {alert['transaction_id']} reversal initiated"),
                ("block_login",         f"Login access disabled for {alert['customer_id']}"),
                ("send_sms",            f"Customer notified via SMS — suspicious activity alert sent"),
            ]
            st.markdown('<span class="section-label">Actions Executed</span>', unsafe_allow_html=True)
            for action, detail in actions:
                st.markdown(
                    f'<div class="action-row">'
                    f'<span class="action-name">{html.escape(action)}</span>'
                    f'<span style="font-size:.68rem;color:#10b981;font-weight:700;">✅ SUCCESS</span>'
                    f'<span style="margin-left:auto;font-size:.73rem;color:#6ee7b7;">{html.escape(detail)}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                trace(f"ACTION_ENGINE → {action} · SUCCESS")

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">Fraud Memory Update</span>', unsafe_allow_html=True)
            new_indicators = [
                {"type": "device",  "value": alert["device_id"],           "source": alert["investigation_id"]},
                {"type": "account", "value": alert["customer_id"],         "source": alert["investigation_id"]},
                {"type": "country", "value": alert["destination_country"], "source": alert["investigation_id"]},
                {"type": "ip",      "value": alert["ip_address"],          "source": alert["investigation_id"]},
            ]
            existing = {m["value"] for m in st.session_state.fraud_memory_updates}
            for ind in new_indicators:
                if ind["value"] not in existing:
                    ind["confirmed_at"] = utcnow_iso()
                    st.session_state.fraud_memory_updates.append(ind)
                    trace(f"FRAUD_MEMORY → WRITE · type={ind['type']} · value={ind['value']}")
            for ind in new_indicators:
                st.markdown(
                    f'<div class="memory-row">'
                    f'<span class="memory-type">{html.escape(ind["type"])}</span>'
                    f'<span class="memory-val">{html.escape(str(ind["value"]))}</span>'
                    f'<span style="margin-left:auto;font-size:.68rem;color:#4a6080;">pinned from {html.escape(ind["source"])}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if st.session_state.fraud_memory_updates:
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown('<span class="section-label">Full Fraud Memory Ledger (Session)</span>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(st.session_state.fraud_memory_updates), hide_index=True, use_container_width=True)

        elif approved:
            st.markdown(
                f'<div class="info-panel">✅ Transaction <b>{html.escape(alert["transaction_id"])}</b> approved. '
                f'Case closed as FALSE_POSITIVE. No remediation taken.</div>',
                unsafe_allow_html=True,
            )
            trace(f"RESOLUTION → FALSE_POSITIVE · {alert['alert_id']}")
        else:
            st.markdown(
                '<div class="warn-panel">⚠ No resolution action recorded yet. Complete HITL review first.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("→ View Audit Trail", type="primary", key="to_audit"):
                st.session_state.stage = 9
                st.rerun()
        with col2:
            if st.button("→ Live Dashboard", key="to_dashboard"):
                st.session_state.stage = 10
                st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 9 — AUDIT TRAIL
# ─────────────────────────────────────────────────────────────────────────────
def stage_audit(alert: dict | None) -> None:
    stage_hero(
        9,
        "Immutable lineage for supervisors and auditors",
        "Every API hop, model assist, analyst decision, and remediation hook lands in the trace. Export or pipe this feed into your SIEM for long-term retention.",
        badge_label="Non-repudiation",
        badge_ok=True,
    )

    tab_demo, tab_raw = st.tabs(["🔍 Investigation Demo", "📋 Raw Trace"])

    with tab_demo:
        trail = st.session_state.audit_trail

        if alert:
            rr = alert.get("risk_result") or {}
            score_val = f"{int(float(rr.get('final_risk_score', rr.get('risk_score', 0))) * 100)}/100" if rr else "—"
            decision_val = (
                (alert.get("hitl_decision") or {}).get("decision", "AUTO")
                if alert.get("hitl_decision")
                else ("FROZEN" if alert.get("frozen") else "APPROVED" if alert.get("approved") else "—")
            )
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Alert Created", (alert.get("created_at") or "—")[:19])
            col2.metric("Status", alert.get("status", "—"))
            col3.metric("Risk Score", score_val)
            col4.metric("Decision", decision_val)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">Full Audit Log</span>', unsafe_allow_html=True)
        for entry in reversed(trail[-80:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if alert and alert.get("agent_results"):
            with st.expander("Agent evidence archive (JSON)"):
                st.json(alert["agent_results"])
        if alert and alert.get("ai_synthesis"):
            with st.expander("Model synthesis payload (JSON)"):
                st.json(alert["ai_synthesis"])

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("→ Live Dashboard", type="primary", key="to_live"):
            st.session_state.stage = 10
            st.rerun()

    with tab_raw:
        st.markdown('<span class="section-label">Raw Trace Export</span>', unsafe_allow_html=True)
        st.code(
            "\n".join(f'[{e["timestamp"]}] {e["event"]}' for e in st.session_state.audit_trail[-100:]),
            language="text",
        )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 10 — LIVE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def stage_live_dashboard() -> None:
    stage_hero(
        10,
        "Executive telemetry without losing operational truth",
        "Roll-ups show how the program is trending while preserving drill-down paths to individual alerts — exactly the posture modern fraud COEs adopt.",
        badge_label="Session rollup",
        badge_ok=True,
    )

    m      = st.session_state.metrics
    alerts = st.session_state.alerts
    fraud_stopped = m["confirmed_fraud"] + m["blocked"]

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.6rem;margin-bottom:1.5rem;">'
        f'<div class="stat-card"><div class="stat-value" style="color:#f0f6ff;">{m["total_alerts"]}</div><div class="stat-label">Total Alerts</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{m["confirmed_fraud"]}</div><div class="stat-label">Fraud Confirmed</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{m["auto_closed"]}</div><div class="stat-label">Auto-Closed</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#f59e0b;">{m["hitl_pending"]}</div><div class="stat-label">HITL Pending</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{m["blocked"]}</div><div class="stat-label">Accts Blocked</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<span class="section-label">Active Investigations</span>', unsafe_allow_html=True)
        active = [a for a in alerts if a["status"] not in ("CLOSED",)]
        if active:
            rows = []
            for a in active:
                rr = a.get("risk_result") or {}
                fs = float(rr.get("final_risk_score", rr.get("risk_score", 0)))
                rows.append({
                    "Alert ID":   a["alert_id"],
                    "Customer":   a["customer_id"],
                    "Amount":     f"${a['amount']:,.0f}",
                    "Country":    a["destination_country"],
                    "Severity":   a["severity"],
                    "Status":     a["status"],
                    "Risk Score": f"{int(fs * 100)}/100" if rr else "—",
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.markdown('<div class="info-panel">No active investigations.</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<span class="section-label">Risk Distribution</span>', unsafe_allow_html=True)
        if alerts:
            risk_data = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for a in alerts:
                sev = a.get("severity", "MEDIUM")
                risk_data[sev] = risk_data.get(sev, 0) + 1
            bars_html = ""
            colors = {"CRITICAL": "#ef4444", "HIGH": "#f59e0b", "MEDIUM": "#3b82f6", "LOW": "#10b981"}
            total_a = max(sum(risk_data.values()), 1)
            for sev, count in risk_data.items():
                pct = int(count / total_a * 100)
                bars_html += (
                    f'<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem;">'
                    f'<span style="font-size:.68rem;font-weight:700;color:{colors[sev]};width:60px;text-align:right;">{sev}</span>'
                    f'<div style="flex:1;height:20px;background:#1c3050;border-radius:4px;overflow:hidden;">'
                    f'<div style="height:100%;width:{pct}%;background:{colors[sev]};border-radius:4px;transition:width .4s;"></div></div>'
                    f'<span style="font-size:.78rem;font-weight:700;color:#f0f6ff;width:20px;">{count}</span>'
                    f'</div>'
                )
            st.markdown(bars_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-panel">No alerts to display.</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<span class="section-label">Fraud Memory Store</span>', unsafe_allow_html=True)
        all_mem = st.session_state.fraud_memory + st.session_state.fraud_memory_updates
        if all_mem:
            df_m = pd.DataFrame(all_mem)
            cols = [c for c in ["pattern_type", "entity_id", "confidence", "risk_score", "status", "description"] if c in df_m.columns]
            st.dataframe(df_m[cols or list(df_m.columns)[:5]], hide_index=True, use_container_width=True)
        else:
            st.markdown(
                '<div class="info-panel">No patterns in session or API store. '
                "Open Stage 1 → Fraud Memory → <b>Refresh from API</b> (or demo JSON).</div>",
                unsafe_allow_html=True,
            )

    with col4:
        st.markdown('<span class="section-label">Transaction Volume by Country</span>', unsafe_allow_html=True)
        txns = st.session_state.transactions
        if txns:
            df_tx = pd.DataFrame(txns)
            cv = df_tx.groupby("destination_country")["amount"].sum().reset_index()
            cv.columns = ["Country", "Total Amount"]
            cv = cv.sort_values("Total Amount", ascending=False)
            bars_html = ""
            max_amt = cv["Total Amount"].max() if len(cv) > 0 else 1
            for _, row in cv.iterrows():
                pct = int(row["Total Amount"] / max_amt * 100)
                is_high = row["Country"] in HIGH_RISK
                color   = "#ef4444" if is_high else "#f59e0b" if row["Country"] in MED_RISK else "#3b82f6"
                bars_html += (
                    f'<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.45rem;">'
                    f'<span style="font-size:.72rem;font-weight:700;color:{color};width:30px;">{html.escape(str(row["Country"]))}</span>'
                    f'<div style="flex:1;height:18px;background:#1c3050;border-radius:4px;overflow:hidden;">'
                    f'<div style="height:100%;width:{pct}%;background:{color};border-radius:4px;"></div></div>'
                    f'<span style="font-size:.72rem;color:#8ba3c7;width:70px;text-align:right;">${row["Total Amount"]:,.0f}</span>'
                    f'</div>'
                )
            st.markdown(bars_html, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">All Alerts Summary</span>', unsafe_allow_html=True)
    if alerts:
        rows = []
        for a in alerts:
            rr = a.get("risk_result") or {}
            fs = float(rr.get("final_risk_score", rr.get("risk_score", 0))) if rr else 0.0
            rows.append({
                "Alert ID":  a["alert_id"],
                "Customer":  a["customer_id"],
                "Amount":    f"${a['amount']:,.0f}",
                "Country":   a["destination_country"],
                "Severity":  a["severity"],
                "Status":    a["status"],
                "Risk Score": f"{int(fs * 100)}/100" if rr else "—",
                "Decision":  (
                    (a.get("hitl_decision") or {}).get("decision", "—")
                    if a.get("hitl_decision")
                    else ("FROZEN" if a.get("frozen") else "APPROVED" if a.get("approved") else "—")
                ),
                "Created":   a["created_at"][:19],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("↩ Start New Investigation", type="primary", key="restart"):
        st.session_state.stage = 1
        st.session_state.selected_alert_id = None
        trace("SESSION_RESET → Stage 01")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION STAGE (kept for gate logic compatibility)
# ─────────────────────────────────────────────────────────────────────────────
def stage_evaluation(alert: dict) -> None:
    stage_hero(
        6,
        "Agent Results vs. Benchmark Comparison",
        "Evaluates agent performance against historical benchmarks and industry standards to ensure accuracy and reliability.",
        badge_label="Benchmark engine",
        badge_ok=True,
    )

    tab_demo, tab_audit = st.tabs(["🔍 Investigation Demo", "📋 Audit Trace"])

    with tab_demo:
        eval_result = alert.get("evaluation_result") or {}

        if eval_result:
            st.markdown('<span class="section-label">Evaluation Summary</span>', unsafe_allow_html=True)
            eval_status = eval_result.get("status", "MEETS_BENCHMARK")
            eval_score  = eval_result.get("evaluation_score", 0.0)
            status_color = {
                "EXCEEDS_BENCHMARK": "#10b981", "MEETS_BENCHMARK": "#059669",
                "BELOW_BENCHMARK": "#f59e0b",   "CRITICAL_DEVIATION": "#ef4444",
            }.get(eval_status, "#4a6080")
            st.markdown(
                f'<div class="summary-card">'
                f'<div class="summary-row"><span class="sk">Evaluation Status</span>'
                f'<span class="sv" style="color:{status_color};">{html.escape(eval_status.replace("_"," "))}</span></div>'
                f'<div class="summary-row"><span class="sk">Evaluation Score</span>'
                f'<span class="sv">{eval_score:.2f}/1.00</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            metrics = eval_result.get("metrics") or {}
            if metrics:
                st.markdown('<span class="section-label">Agent Performance Metrics</span>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f'<div class="summary-card">'
                        f'<div class="summary-row"><span class="sk">Risk Score</span><span class="sv">{metrics.get("risk_score","N/A")}</span></div>'
                        f'<div class="summary-row"><span class="sk">Confidence</span><span class="sv">{metrics.get("confidence","N/A")}</span></div>'
                        f'<div class="summary-row"><span class="sk">Processing Time</span><span class="sv">{metrics.get("processing_time","N/A")}s</span></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        f'<div class="summary-card">'
                        f'<div class="summary-row"><span class="sk">Risk Within Range</span><span class="sv">{"✓" if metrics.get("risk_within_range") else "✗"}</span></div>'
                        f'<div class="summary-row"><span class="sk">Meets Confidence</span><span class="sv">{"✓" if metrics.get("meets_confidence_threshold") else "✗"}</span></div>'
                        f'<div class="summary-row"><span class="sk">Processing Acceptable</span><span class="sv">{"✓" if metrics.get("processing_acceptable") else "✗"}</span></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            benchmark_data = eval_result.get("benchmark_data") or {}
            if benchmark_data:
                st.markdown('<span class="section-label">Benchmark Comparison</span>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="summary-card">'
                    f'<div class="summary-row"><span class="sk">Historical Accuracy</span><span class="sv">{benchmark_data.get("historical_accuracy","N/A"):.1%}</span></div>'
                    f'<div class="summary-row"><span class="sk">False Positive Rate</span><span class="sv">{benchmark_data.get("false_positive_rate","N/A"):.1%}</span></div>'
                    f'<div class="summary-row"><span class="sk">Detection Rate</span><span class="sv">{benchmark_data.get("detection_rate","N/A"):.1%}</span></div>'
                    f'<div class="summary-row"><span class="sk">Typical Risk Range</span><span class="sv">{html.escape(str(benchmark_data.get("typical_risk_range","N/A")))}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            recommendations = eval_result.get("recommendations") or []
            if recommendations:
                st.markdown('<span class="section-label">Recommendations</span>', unsafe_allow_html=True)
                for rec in recommendations:
                    st.markdown(
                        f'<div class="evidence-card"><div class="evidence-reason">{html.escape(str(rec))}</div></div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown('<div class="info-panel">No evaluation results available. Run agent evaluation first.</div>', unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">Evaluation Controls</span>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Re-evaluate Agent", use_container_width=True):
                try:
                    response = httpx.post(
                        f"{API_BASE}/v1/evaluation/agent-result",
                        headers=_api_headers(),
                        json={
                            "investigation_id": alert.get("investigation_id", ""),
                            "agent_type": "transaction",
                            "agent_result": (alert.get("agent_results") or {}).get("transaction", {}),
                            "fraud_type": "transaction_anomaly",
                        },
                    )
                    if response.status_code == 200:
                        alert["evaluation_result"] = response.json()
                        st.success("Agent re-evaluated successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Evaluation failed: {e}")
        with col2:
            if st.button("📊 View Benchmarks", use_container_width=True):
                try:
                    response = httpx.get(f"{API_BASE}/v1/evaluation/benchmarks", headers=_api_headers())
                    if response.status_code == 200:
                        benchmarks = response.json().get("data") or {}
                        if benchmarks:
                            st.markdown('<span class="section-label">Available Benchmarks</span>', unsafe_allow_html=True)
                            for fraud_type, benchmark in (benchmarks.get("fraud_type_benchmarks") or {}).items():
                                st.markdown(f"**{fraud_type}**: Accuracy `{benchmark['historical_accuracy']:.1%}`, Risk Range `{benchmark['typical_risk_range']}`")
                except Exception as e:
                    st.error(f"Failed to fetch benchmarks: {e}")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.code(
            "\n".join(f'[{e["timestamp"]}] {e["event"]}' for e in st.session_state.audit_trail[-100:]),
            language="text",
        )
        if alert and alert.get("agent_results"):
            with st.expander("Agent evidence archive (JSON)"):
                st.json(alert["agent_results"])
        if alert and alert.get("ai_synthesis"):
            with st.expander("Model synthesis payload (JSON)"):
                st.json(alert["ai_synthesis"])
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("→ Live Dashboard", type="primary", key="to_live"):
            st.session_state.stage = 10
            st.rerun()

    with tab_audit:
        st.markdown('<span class="section-label">Audit Trace</span>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.audit_trail[-30:]):
            st.markdown(
                f'<div class="timeline-row">'
                f'<span class="timeline-ts">{html.escape(entry["timestamp"])}</span>'
                f'<span class="timeline-evt">{html.escape(entry["event"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# NARRATIVE / OUTLINE HELPERS (preserved for render_post_segment_chrome)
# ─────────────────────────────────────────────────────────────────────────────
STAGE_LABELS_LEGACY = [
    "Ingestion", "Triage", "Investigation", "Evaluation", "Resolution",
]

DEMO_KICKER = "Reference walkthrough"
DEMO_TITLE  = "Ten stages — one coherent fraud story"
DEMO_BODY   = (
    "Open this map when you need the full arc. For presenting, stay in the main column: "
    "each stage is one chapter; advance with the primary action at the bottom or jump from the sidebar."
)


def render_narrative_banner() -> None:
    items = "".join(
        f'<li><b>{html.escape(num)}</b> <strong>{html.escape(title)}</strong> — {html.escape(desc)}</li>'
        for num, title, desc in NARRATIVE_BEATS
    )
    st.markdown(
        f'<div style="background:linear-gradient(135deg,rgba(13,27,46,.92),rgba(6,13,26,.98));border:1px solid #1c3050;border-radius:14px;padding:1rem 1.25rem;margin-bottom:1.25rem;">'
        f'<div style="font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#4a6080;margin-bottom:.35rem;">{html.escape(DEMO_KICKER)}</div>'
        f'<div style="font-size:1.05rem;font-weight:700;color:#f0f6ff;letter-spacing:-.02em;margin-bottom:.4rem;">{html.escape(DEMO_TITLE)}</div>'
        f'<p style="font-size:.84rem;color:#8ba3c7;line-height:1.55;margin:0 0 .75rem;">{html.escape(DEMO_BODY)}</p>'
        f'<ul style="margin:0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.45rem .75rem;">{items}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_session_strip(m: dict, fraud_stopped: int) -> None:
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:.65rem 1.25rem;align-items:center;padding:.55rem .85rem;'
        f'margin-bottom:1rem;border-radius:10px;border:1px solid #1c3050;background:rgba(13,27,46,.55);'
        f'font-size:.78rem;color:#8ba3c7;">'
        f'<span><b style="color:#f0f6ff;">{m["total_alerts"]}</b> alerts</span>'
        f'<span><b style="color:#f0f6ff;">{fraud_stopped}</b> confirmed + blocked</span>'
        f'<span><b style="color:#f0f6ff;">{m["auto_closed"]}</b> auto-closed</span>'
        f'<span><b style="color:#f0f6ff;">{m["hitl_pending"]}</b> HITL queue</span>'
        f'<span><b style="color:#f0f6ff;">{m["blocked"]}</b> accounts blocked</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_post_segment_chrome(stage: int, m: dict, fraud_stopped: int) -> None:
    with st.expander("Outline, counters & activity (optional)", expanded=False):
        render_narrative_banner()
        if stage <= 2:
            st.caption("Session counters appear once alerts exist (stage 3 onward).")
        elif stage < 10:
            render_session_strip(m, fraud_stopped)
        else:
            st.caption("Primary roll-ups are in the stage body above; reset from the sidebar to rehearse.")
        if stage >= 4:
            st.markdown('<span class="section-label">Recent activity</span>', unsafe_allow_html=True)
            recent_activity = st.session_state.audit_trail[-10:]
            for event in reversed(recent_activity):
                st.markdown(
                    f'<div class="timeline-row">'
                    f'<span class="timeline-ts">{html.escape(str(event["timestamp"]))}</span>'
                    f'<span class="timeline-evt">{html.escape(str(event["event"]))}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Agentic AI Fraud Investigator",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    sync_fraud_memory_from_api()
    st.markdown(CSS, unsafe_allow_html=True)
    render_sidebar()

    render_platform_header()
    render_system_status_strip()
    render_pipeline_stepper(st.session_state.stage)

    primary = st.radio(
        "Primary view",
        ["Live investigator", "Walkthrough (10 stages)", "Event log"],
        horizontal=True,
        label_visibility="collapsed",
        key="primary_view",
    )

    stage = st.session_state.stage
    m     = st.session_state.metrics
    fraud_stopped = m["confirmed_fraud"] + m["blocked"]
    alert = next(
        (a for a in st.session_state.alerts if a["alert_id"] == st.session_state.selected_alert_id),
        None,
    )

    def _gate(msg: str) -> None:
        st.markdown(
            f'<div style="border-left:3px solid #f59e0b;background:rgba(245,158,11,.07);padding:.85rem 1rem;'
            f'border-radius:0 10px 10px 0;margin:.5rem 0 1rem;">'
            f'<div style="font-weight:700;color:#fcd34d;font-size:.82rem;margin-bottom:.25rem;">Complete the prior stage</div>'
            f'<div style="color:#8ba3c7;font-size:.82rem;line-height:1.45;">{msg}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if primary == "Live investigator":
        render_investigator_console(embedded=True)

    elif primary == "Walkthrough (10 stages)":
        st.caption(f"**Stage {stage}/10** · {STAGE_LABELS[stage - 1]}")

        if stage == 1:
            stage_data_sources()
        elif stage == 2:
            stage_generate_alert()
        elif stage == 3:
            stage_alerts_queue()
        elif stage == 4:
            if not alert:
                _gate("Generate and select an alert in <b>Stage 02–03</b> first.")
            else:
                stage_triage(alert)
        elif stage == 5:
            if not alert or not alert.get("triage_result"):
                _gate("Run triage in <b>Stage 04</b> so agents receive a routed case.")
            else:
                stage_agents(alert)
        elif stage == 6:
            if not alert or not alert.get("agent_results"):
                _gate("Execute the parallel agents in <b>Stage 05</b> to populate evidence.")
            else:
                # Use risk scoring stage (evaluation gate check preserved for compatibility)
                if not alert.get("evaluation_result") and alert.get("risk_result"):
                    stage_risk_scoring(alert)
                elif alert.get("evaluation_result"):
                    stage_evaluation(alert)
                else:
                    stage_risk_scoring(alert)
        elif stage == 7:
            if not alert:
                _gate("Record an analyst disposition in <b>Stage 07</b> before remediation.")
            else:
                stage_hitl(alert)
        elif stage == 8:
            stage_resolution(alert)
        elif stage == 9:
            stage_audit(alert)
        elif stage == 10:
            stage_live_dashboard()

        render_post_segment_chrome(stage, m, fraud_stopped)

    else:
        st.markdown('<span class="section-label">Append-only trace (export friendly)</span>', unsafe_allow_html=True)
        st.code(
            "\n".join(f'[{e["timestamp"]}] {e["event"]}' for e in st.session_state.audit_trail[-150:]),
            language="text",
        )

    st.markdown(
        '<div style="margin-top:2rem;padding-top:1rem;border-top:1px solid #1c3050;text-align:center;">'
        '<div style="font-size:.72rem;font-weight:700;color:#8ba3c7;margin-bottom:.25rem;">Reference implementation · not production advice</div>'
        '<div style="font-size:.68rem;color:#4a6080;">Configure <code>FRAUD_API_BASE</code> for your FastAPI instance. '
        'Set <code>API_KEY</code> only if the API requires <code>X-API-Key</code>.</div>'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
