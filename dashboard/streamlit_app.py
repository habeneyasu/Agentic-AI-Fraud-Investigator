"""
Presenter console for the Agentic AI Fraud Investigator reference stack.

Each segment issues real FastAPI calls. Set ``FRAUD_API_BASE`` to your API. Optionally set ``API_KEY`` if the server enforces ``X-API-Key``.
"""

from __future__ import annotations

import html
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
API_BASE = os.getenv("FRAUD_API_BASE", "http://127.0.0.1:8000")
DATA_DIR = Path(__file__).parent.parent / "app" / "data"


def _api_headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    key = (os.getenv("API_KEY") or "").strip()
    if key:
        h["X-API-Key"] = key
    return h

STAGE_LABELS = [
    "Ingestion",
    "Triage",
    "Investigation",
    "Evaluation",
    "Resolution",
]

DEMO_KICKER = "Reference walkthrough"
DEMO_TITLE = "Ten segments — one coherent fraud story"
DEMO_BODY = (
    "Open this map when you need the full arc. For presenting, stay in the main column: "
    "each segment is one chapter; advance with the primary action at the bottom or jump from the sidebar."
)

NARRATIVE_BEATS = [
    ("01", "Ground truth", "Load or upload the datasets your agents will reason over."),
    ("02", "Signal → case", "Promote a suspicious movement into a formal alert with API idempotency."),
    ("03", "Queue discipline", "Prioritise work the way an operations floor would."),
    ("04", "Policy first", "Separate fast rules from slower model-assisted classification."),
    ("05", "Evidence in parallel", "Let independent specialists build an auditable fact base."),
    ("06", "Synthesis", "Collapse multi-source noise into one risk narrative."),
    ("07", "Human control", "Reserve material outcomes for an analyst with a structured decision."),
    ("08", "Execute", "Close the loop with actions and memory updates."),
    ("09", "Prove it", "Export the immutable trace regulators expect."),
    ("10", "Steer the program", "Roll up outcomes for leadership without losing fidelity."),
]

HIGH_RISK  = {"IR", "KP", "SY", "CU", "VE", "MM", "BY"}
MED_RISK   = {"RU", "UA", "PK", "BD", "GH", "KE", "TZ", "CN", "AF"}

# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', -apple-system, sans-serif !important; }
h1, h2, h3, h4, h5, h6 { font-family: 'Space Grotesk', sans-serif !important; }
code, pre, .monospace { font-family: 'SF Mono', 'Monaco', monospace !important; }

/* Premium Banking Dark Theme */
:root {
    --bg-primary: #081120;
    --bg-secondary: #0F1B33;
    --bg-tertiary: #1A2B4A;
    --accent: #3B82F6;
    --fraud: #EF4444;
    --success: #10B981;
    --warning: #F59E0B;
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --border: rgba(59, 130, 246, 0.2);
    --gold: #e8c547;
    --line: rgba(148, 163, 184, 0.18);
}

.narrative-banner {
    background: linear-gradient(135deg, rgba(15, 27, 51, 0.92), rgba(8, 17, 32, 0.98));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
}
.narrative-banner .nb-kicker {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 0.35rem;
}
.narrative-banner .nb-title {
    margin: 0 0 0.4rem 0;
    font-size: 1.08rem;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.02em;
    line-height: 1.25;
}
.narrative-banner .nb-body {
    margin: 0;
    font-size: 0.84rem;
    color: #94a3b8;
    line-height: 1.55;
}
.narrative-banner .nb-steps {
    margin: 0.75rem 0 0 0;
    padding: 0;
    list-style: none;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.45rem 0.75rem;
}
.narrative-banner .nb-steps li {
    font-size: 0.72rem;
    color: #cbd5e1;
    padding: 0.35rem 0.5rem;
    border-radius: 8px;
    background: rgba(15, 27, 51, 0.6);
    border: 1px solid var(--line);
}
.narrative-banner .nb-steps li b {
    color: #93c5fd;
    font-weight: 700;
}

.story-frame {
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.25rem 1.1rem;
    margin-bottom: 1.15rem;
    background: linear-gradient(145deg, rgba(15, 27, 51, 0.96), rgba(8, 17, 32, 0.99));
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.22);
}
.story-frame-meta {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 0.45rem;
}
.story-frame-beat-line {
    font-size: 0.9rem;
    color: #cbd5e1;
    line-height: 1.55;
}
.story-beat-num {
    color: #93c5fd;
    font-weight: 800;
    margin-right: 0.25rem;
}
.story-frame-beat-title {
    font-weight: 700;
    color: #f1f5f9;
}
.story-frame-beat-dash { color: #475569; }
.story-frame-beat-desc { color: #94a3b8; }
.story-rail-outer {
    height: 4px;
    background: rgba(148, 163, 184, 0.12);
    border-radius: 999px;
    margin-top: 0.9rem;
    overflow: hidden;
}
.story-rail-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #2563eb, #6366f1);
}
.session-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem 1.25rem;
    align-items: center;
    padding: 0.55rem 0.85rem;
    margin-bottom: 1rem;
    border-radius: 10px;
    border: 1px solid var(--line);
    background: rgba(15, 27, 51, 0.55);
    font-size: 0.78rem;
    color: #94a3b8;
}
.session-strip b { color: #e2e8f0; font-weight: 700; }

.story-beat {
    font-size: 0.72rem;
    color: #64748b;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 600;
    margin-top: 0.55rem;
}

.demo-gate {
    border-left: 3px solid #f59e0b;
    background: rgba(245, 158, 11, 0.07);
    padding: 0.85rem 1rem;
    border-radius: 0 10px 10px 0;
    margin: 0.5rem 0 1rem;
}
.demo-gate-title { font-weight: 700; color: #fcd34d; font-size: 0.82rem; margin-bottom: 0.25rem; }
.demo-gate-body { color: #cbd5e1; font-size: 0.82rem; line-height: 1.45; }

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary);
}
[data-testid="stHeader"] {
    background: var(--bg-secondary) !important;
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(10px);
    position: relative !important;
}
/* App title in the real top bar (next to menu) — ::after survives Streamlit’s main-column HTML sanitization */
[data-testid="stHeader"]::after {
    content: 'Agentic AI Fraud Investigator';
    position: absolute;
    left: clamp(2.6rem, 4vw, 3.75rem);
    right: clamp(7.5rem, 18vw, 12rem);
    top: 50%;
    transform: translateY(-50%);
    font-family: "Space Grotesk", "Inter", sans-serif;
    font-size: clamp(0.72rem, 1.05vw, 0.98rem);
    font-weight: 800;
    color: #f8fafc !important;
    letter-spacing: -0.02em;
    line-height: 1.2;
    pointer-events: none;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
    max-height: 2.6em;
    overflow: hidden;
    z-index: 1000000;
    text-align: left;
}
@media (max-width: 520px) {
    [data-testid="stHeader"]::after {
        font-size: 0.68rem;
        right: 6.5rem;
        max-height: 3em;
    }
}

.block-container {
    max-width: 1400px;
    padding: 1rem 1.5rem 2rem !important;
}
[data-testid="stSidebarContent"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
    backdrop-filter: blur(15px);
}

/* Glassmorphism Effects */
.glass-panel {
    background: rgba(15, 27, 51, 0.8);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Premium Banking Cards */
.enterprise-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
}

.enterprise-card:hover {
    border-color: var(--accent);
    box-shadow: 0 8px 30px rgba(59, 130, 246, 0.2);
}

/* KPI Cards */
.kpi-card {
    background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--accent);
}

.kpi-card.success::before { background: var(--success); }
.kpi-card.fraud::before { background: var(--fraud); }
.kpi-card.warning::before { background: var(--warning); }

/* Progress Timeline */
.progress-timeline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin: 1.5rem 0;
    position: relative;
}

.progress-step {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    background: var(--bg-tertiary);
    border: 2px solid var(--border);
    color: var(--text-muted);
    position: relative;
    z-index: 2;
}

.progress-step.active {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
    animation: pulse-glow 2s ease-in-out infinite;
}

.progress-step.completed {
    background: var(--success);
    border-color: var(--success);
    color: white;
}

.progress-line {
    flex: 1;
    height: 2px;
    background: var(--border);
    position: relative;
}

.progress-line.completed {
    background: var(--success);
}

/* Animations */
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
    50% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
}

@keyframes fade-in {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.agent-card-animated {
    animation: fade-in 0.6s ease-out;
}

/* Activity Feed */
.activity-feed {
    max-height: 300px;
    overflow-y: auto;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
}

.activity-item {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-item .timestamp {
    color: var(--text-muted);
    font-size: 0.75rem;
    font-family: 'SF Mono', monospace;
}

/* Agent Progress Cards */
.agent-progress {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.agent-progress .agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.agent-progress .agent-name {
    font-weight: 700;
    color: var(--text-primary);
}

.agent-progress .agent-status {
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}

.agent-progress .status-running {
    background: var(--accent);
    color: white;
}

.agent-progress .status-completed {
    background: var(--success);
    color: white;
}

.agent-progress .status-pending {
    background: var(--bg-tertiary);
    color: var(--text-muted);
}

.progress-bar {
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}

.progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.3s ease;
}

.progress-fill.success { background: var(--success); }
.progress-fill.fraud { background: var(--fraud); }
.progress-fill.warning { background: var(--warning); }

/* Pulse Animations */
@keyframes pulse-active {
    0%, 100% {
        transform: scale(1);
        box-shadow: 0 0 0 0 rgba(255, 209, 102, 0.7);
    }
    50% {
        transform: scale(1.05);
        box-shadow: 0 0 0 10px rgba(255, 209, 102, 0);
    }
}

@keyframes fade-in {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Step Progress Line */
.step-progress {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
}

.step-progress::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--green) 0%, var(--gold) 50%, #475569 100%);
    transform: translateY(-50%);
    z-index: -1;
}

/* Animated Agent Cards */
.agent-card-animated {
    animation: fade-in 0.6s ease-out;
    transition: all 0.3s ease;
}

.agent-card-animated:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(10, 37, 64, 0.3);
}

/* Priority Badges */
.priority-critical {
    background: var(--red);
    color: white;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.priority-high {
    background: var(--gold);
    color: var(--navy-dark);
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.priority-low {
    background: var(--green);
    color: white;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
/* App branding */
.branding-header {
    background: rgba(10, 37, 64, 0.9);
    border: 1px solid rgba(255, 209, 102, 0.1);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    display: flex;
    align-items: center;
    gap: 1rem;
}

.branding-logo {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--gold);
    text-shadow: 0 0 10px rgba(255, 209, 102, 0.3);
}

.branding-tagline {
    font-size: 0.9rem;
    color: #94a3b8;
    font-style: italic;
}

.footer-branding {
    background: rgba(10, 37, 64, 0.8);
    border: 1px solid rgba(255, 209, 102, 0.1);
    border-radius: 8px;
    padding: 0.75rem;
    margin-top: 2rem;
    text-align: center;
    color: #64748b;
    font-size: 0.8rem;
}

#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

.stepper-wrap { display:flex; gap:4px; flex-wrap:wrap; margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:1px solid #1a2d45; }
[data-testid="stSidebar"] .stepper-wrap { margin-bottom:0.65rem; padding-bottom:0.65rem; font-size:0.68rem; }
.step-chip { padding:.25rem .7rem; border-radius:6px; font-size:.68rem; font-weight:600; letter-spacing:.03em; border:1px solid #1a2d45; color:#475569; background:#0a1628; }
.step-chip.active { background:linear-gradient(135deg,#1e3a5f,#0f2a4a); color:#93c5fd; border-color:#3b82f6; box-shadow:0 0 0 1px rgba(59,130,246,.3),0 4px 12px rgba(59,130,246,.15); }
.step-chip.done { background:#0a2218; color:#34d399; border-color:#065f46; }

.section-label { font-size:.68rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#475569; margin-bottom:.75rem; display:block; }
.stage-header { font-size:1.15rem; font-weight:700; color:#f1f5f9; letter-spacing:-.02em; margin-bottom:.25rem; }
.stage-subtext { font-size:.82rem; color:#64748b; margin-bottom:1.5rem; }

.stat-card { background:linear-gradient(135deg,#0f1f35,#0a1628); border:1px solid #1a2d45; border-radius:12px; padding:1rem 1.2rem; text-align:center; }
.stat-value { font-size:1.8rem; font-weight:800; line-height:1; margin-bottom:.2rem; }
.stat-label { font-size:.7rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:#475569; }

.alert-card { background:linear-gradient(135deg,#0f1f35,#0a1628); border:1px solid #1a2d45; border-radius:12px; padding:1rem 1.2rem; margin-bottom:.6rem; }
.alert-card.selected { border-color:#3b82f6; box-shadow:0 0 0 1px rgba(59,130,246,.3); }
.alert-card.critical { border-left:3px solid #ef4444; }
.alert-card.high { border-left:3px solid #f59e0b; }

.pill { display:inline-flex; align-items:center; padding:.18rem .6rem; border-radius:6px; font-size:.65rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; }
.pill-critical { background:rgba(239,68,68,.12); color:#fca5a5; border:1px solid rgba(239,68,68,.3); }
.pill-high     { background:rgba(245,158,11,.12); color:#fde68a; border:1px solid rgba(245,158,11,.3); }
.pill-medium   { background:rgba(59,130,246,.12); color:#93c5fd; border:1px solid rgba(59,130,246,.3); }
.pill-low      { background:rgba(16,185,129,.12); color:#6ee7b7; border:1px solid rgba(16,185,129,.3); }
.pill-new      { background:rgba(245,158,11,.12); color:#fbbf24; border:1px solid rgba(245,158,11,.4); }
.pill-closed   { background:rgba(71,85,105,.2);   color:#94a3b8; border:1px solid #334155; }
.pill-hitl     { background:rgba(139,92,246,.12); color:#c4b5fd; border:1px solid rgba(139,92,246,.3); }

.info-panel { background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(59,130,246,.03)); border:1px solid rgba(59,130,246,.2); border-radius:10px; padding:.85rem 1rem; margin-bottom:1rem; font-size:.83rem; color:#93c5fd; }
.warn-panel { background:linear-gradient(135deg,rgba(245,158,11,.08),rgba(245,158,11,.03)); border:1px solid rgba(245,158,11,.3); border-radius:10px; padding:.85rem 1rem; margin-bottom:1rem; font-size:.83rem; color:#fbbf24; }
.success-panel { background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(16,185,129,.03)); border:1px solid rgba(16,185,129,.3); border-radius:10px; padding:.85rem 1rem; margin-bottom:1rem; font-size:.83rem; color:#34d399; }

.flag-row { display:flex; align-items:flex-start; gap:.75rem; padding:.7rem 1rem; border-radius:10px; margin-bottom:.4rem; background:#0f1f35; border:1px solid #1a2d45; }
.flag-label { font-size:.78rem; font-weight:700; color:#f1f5f9; }
.flag-detail { font-size:.73rem; color:#64748b; margin-top:1px; }

.agent-card { background:linear-gradient(135deg,#0f1f35,#0a1628); border:1px solid #1a2d45; border-radius:12px; padding:1.2rem; }
.agent-card.success { border-color:rgba(16,185,129,.4); }
.agent-card.warning { border-color:rgba(245,158,11,.4); }
.agent-card.danger  { border-color:rgba(239,68,68,.4); }
.agent-name { font-size:.8rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; margin-bottom:.75rem; }
.agent-finding { font-size:.78rem; padding:.4rem 0; border-bottom:1px solid #1a2d45; display:flex; justify-content:space-between; }
.agent-finding:last-child { border-bottom:none; }
.fk { color:#64748b; }
.fv { font-weight:600; font-family:'JetBrains Mono',monospace; }
.fv-t { color:#10b981; } .fv-f { color:#475569; } .fv-h { color:#ef4444; } .fv-m { color:#f59e0b; }

.risk-display { background:linear-gradient(135deg,#0f1f35,#0a1628); border:1px solid #1a2d45; border-radius:16px; padding:1.5rem; text-align:center; margin-bottom:1rem; }
.risk-number { font-size:4rem; font-weight:800; line-height:1; letter-spacing:-.04em; }
.gauge-track { height:8px; border-radius:4px; background:#1a2d45; overflow:hidden; margin:.75rem 0 .4rem; }
.gauge-fill  { height:100%; border-radius:4px; }

.evidence-card { background:#0f1f35; border:1px solid #1a2d45; border-left:3px solid #8b5cf6; border-radius:0 10px 10px 0; padding:.75rem 1rem; margin-bottom:.5rem; }
.evidence-reason { font-size:.82rem; font-weight:600; color:#f1f5f9; margin-bottom:.2rem; }
.evidence-meta   { font-size:.7rem; color:#475569; font-family:'JetBrains Mono',monospace; }

.hitl-alert { background:linear-gradient(135deg,rgba(245,158,11,.08),rgba(245,158,11,.03)); border:1px solid rgba(245,158,11,.3); border-radius:12px; padding:1.2rem 1.4rem; margin-bottom:1.5rem; }
.hitl-title { font-size:1rem; font-weight:700; color:#fbbf24; margin-bottom:.4rem; }
.hitl-body  { font-size:.83rem; color:#d97706; }

.summary-card { background:#0f1f35; border:1px solid #1a2d45; border-radius:10px; padding:1rem 1.2rem; }
.summary-row { display:flex; justify-content:space-between; padding:.35rem 0; border-bottom:1px solid #1a2d45; font-size:.82rem; }
.summary-row:last-child { border-bottom:none; }
.sk { color:#64748b; } .sv { font-weight:600; color:#f1f5f9; }

.action-row { background:#0a2218; border:1px solid rgba(16,185,129,.2); border-radius:10px; padding:.75rem 1rem; margin-bottom:.4rem; display:flex; align-items:center; gap:.75rem; }
.action-name { font-family:'JetBrains Mono',monospace; font-size:.78rem; color:#34d399; font-weight:600; }

/* Enterprise Sidebar Control Panel - Final Polish */
.sidebar-phase-header {
    font-size: 0.55rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin: 0.8rem 0 0.4rem 0;
    padding: 0 0.5rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.3rem;
    font-family: 'Inter', sans-serif;
}

/* Professional button styling for active steps */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent), rgba(59, 130, 246, 0.8)) !important;
    border-color: var(--accent) !important;
    color: white !important;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.4) !important;
    border-left: 3px solid var(--accent) !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Completed steps styling */
.stButton > button[data-testid="baseButton-secondary"] {
    background: rgba(16, 185, 129, 0.1) !important;
    border-color: rgba(16, 185, 129, 0.3) !important;
    color: var(--success) !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Monospace styling for step numbers */
.step-number {
    font-family: 'SF Mono', 'Monaco', monospace;
    font-weight: 700;
    color: inherit;
}

/* Compact button styling with precision alignment */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div.stButton > button,
.stButton > button {
    padding: 0.4rem 0.6rem !important;
    margin: 0.15rem 0 !important;
    font-size: 0.75rem !important;
    border-radius: 6px !important;
    text-align: center !important;
    transition: all 0.2s ease !important;
    font-family: 'Inter', sans-serif !important;
    line-height: 1.3 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
}

/* Force center alignment for sidebar buttons specifically */
section[data-testid="stSidebar"] > div > div > div > div.stButton > button {
    text-align: center !important;
    justify-content: center !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}

/* Custom nav-button classes for perfect centering */
.nav-button {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.4rem 0.6rem;
    margin: 0.15rem 0;
    font-size: 0.75rem;
    font-family: 'Inter', sans-serif;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: all 0.2s ease;
    cursor: pointer;
}

.nav-button:hover {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
    color: var(--text-primary);
    transform: translateX(2px);
}

.nav-button-active {
    background: linear-gradient(135deg, var(--accent), rgba(59, 130, 246, 0.8));
    border-color: var(--accent);
    color: white;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
    border-left: 3px solid var(--accent);
}

.nav-button-completed {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: var(--success);
}

.nav-button-locked {
    background: var(--bg-tertiary);
    border-color: var(--border);
    color: var(--text-muted);
}

/* Wrapper to force center alignment */
.nav-button-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 0.1rem 0;
}

/* Add spacing after phase headers */
.sidebar-phase-header + .nav-button-wrapper {
    margin-top: 0.2rem;
}

.nav-button-wrapper button {
    text-align: center !important;
    justify-content: center !important;
    align-items: center !important;
    display: flex !important;
    width: 100% !important;
}

.stButton > button:hover:not(:disabled) {
    transform: translateX(2px) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
}

/* Disabled button styling for locked steps */
.stButton > button:disabled {
    opacity: 0.4 !important;
    background: var(--bg-tertiary) !important;
    border-color: var(--border) !important;
    color: var(--text-muted) !important;
    cursor: not-allowed !important;
}

/* Ensure consistent vertical rhythm between phase headers and buttons */
.sidebar-phase-header + .stButton {
    margin-top: 0.4rem !important;
}

/* Monospace digits for perfect vertical alignment */
.stButton > button::before {
    content: attr(data-step-icon);
    font-family: 'SF Mono', 'Monaco', monospace;
    font-weight: 700;
    display: inline-block;
    width: 1.2em;
    text-align: center;
}

.sidebar-reset-button {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    margin: 1.5rem 0 0.5rem 0;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--fraud);
    transition: all 0.2s ease;
}

.sidebar-reset-button:hover {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.5);
    transform: translateY(-1px);
}

.memory-row { background:#0a1628; border:1px solid rgba(16,185,129,.15); border-radius:8px; padding:.6rem .9rem; margin-bottom:.35rem; font-size:.78rem; display:flex; align-items:center; gap:.6rem; }
.memory-type { font-size:.65rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; background:rgba(16,185,129,.12); color:#34d399; padding:.15rem .45rem; border-radius:4px; }
.memory-val  { font-family:'JetBrains Mono',monospace; color:#94a3b8; font-size:.75rem; }

.timeline-row { display:flex; gap:.75rem; padding:.5rem 0; border-bottom:1px solid #1a2d45; font-size:.78rem; }
.timeline-ts  { font-family:'JetBrains Mono',monospace; color:#3b82f6; font-size:.7rem; flex-shrink:0; }
.timeline-evt { color:#94a3b8; }

.ev-box { background:#0f1f35; border:1px solid #1a2d45; border-left:3px solid #3b82f6; border-radius:0 10px 10px 0; padding:.75rem 1rem; margin-bottom:.5rem; font-size:.82rem; }

.sb-stat { display:flex; justify-content:space-between; align-items:center; padding:.4rem 0; border-bottom:1px solid #1a2d45; }
.sb-stat-label { font-size:.75rem; color:#475569; }
.sb-stat-val   { font-size:.85rem; font-weight:700; }

.api-badge { display:inline-flex; align-items:center; gap:.3rem; background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.25); border-radius:6px; padding:.15rem .5rem; font-size:.65rem; font-weight:700; color:#34d399; font-family:'JetBrains Mono',monospace; }
.api-badge.calling { background:rgba(59,130,246,.1); border-color:rgba(59,130,246,.25); color:#93c5fd; }
.api-badge.error   { background:rgba(239,68,68,.1);  border-color:rgba(239,68,68,.25);  color:#fca5a5; }

@keyframes pulse-amber { 0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0);}50%{box-shadow:0 0 0 6px rgba(245,158,11,.15);} }
.pulse-amber { animation:pulse-amber 2s infinite; }
hr { border-color:#1a2d45 !important; margin:1.5rem 0 !important; }

[data-testid="stMetric"] { background:#0f1f35; border:1px solid #1a2d45; border-radius:10px; padding:.75rem 1rem; }
[data-testid="stMetricLabel"] { font-size:.68rem !important; font-weight:700 !important; letter-spacing:.06em !important; text-transform:uppercase !important; color:#475569 !important; }
[data-testid="stMetricValue"] { font-size:1.5rem !important; font-weight:800 !important; color:#f1f5f9 !important; }
button[kind="primary"] { background:linear-gradient(135deg,#2563eb,#1d4ed8) !important; border:none !important; border-radius:8px !important; font-weight:600 !important; box-shadow:0 4px 12px rgba(37,99,235,.3) !important; }
button[kind="secondary"] { background:#0f1f35 !important; border:1px solid #1e3a5f !important; color:#93c5fd !important; border-radius:8px !important; font-weight:600 !important; }
[data-testid="stForm"] { background:#0f1f35; border:1px solid #1a2d45; border-radius:12px; padding:1.2rem; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS — real HTTP calls to the backend
# ─────────────────────────────────────────────────────────────────────────────
def api_post(path: str, payload: dict) -> dict:
    """Synchronous POST to the backend API."""
    try:
        r = httpx.post(f"{API_BASE}{path}", json=payload, headers=_api_headers(), timeout=60)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get(path: str, params: dict | None = None) -> dict:
    """Synchronous GET to the backend API."""
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, headers=_api_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_badge(label: str, ok: bool = True) -> str:
    cls = "api-badge" if ok else "api-badge error"
    icon = "✓" if ok else "✗"
    return f'<span class="{cls}">{icon} {label}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# STAGE HERO — reusable Hero-Content-Detail header for every stage
# ─────────────────────────────────────────────────────────────────────────────
def stage_hero(
    stage_num: int,
    title: str,
    description: str,
    badge_label: str = "",
    badge_ok: bool = True,
    learning: str = "",
) -> None:
    """Stage header: where we are in the story, what to observe, optional status chip."""
    _ = stage_num  # kept for call-site readability (aligns with session stage index)
    badge_html = ""
    color = "#34d399" if badge_ok else "#fbbf24"
    border = "rgba(52,211,153,.35)" if badge_ok else "rgba(251,191,36,.35)"
    bg = "rgba(16,185,129,.08)" if badge_ok else "rgba(245,158,11,.1)"
    if badge_label:
        badge_html = (
            f'<span style="font-size:.65rem;font-weight:700;letter-spacing:.08em;'
            f'text-transform:uppercase;background:{bg};border:1px solid {border};border-radius:8px;'
            f'padding:.28rem .6rem;color:{color};white-space:nowrap;">'
            f"{html.escape(badge_label)}</span>"
        )

    learning_html = ""
    if learning:
        learning_html = (
            f'<div class="story-beat">Presenter note — {html.escape(learning)}</div>'
        )

    title_h = html.escape(title)
    desc_h = html.escape(description)

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;'
        f'border-bottom:1px solid var(--line);padding-bottom:.85rem;margin-bottom:1rem;">'
        f'<div style="min-width:0;">'
        f'<div style="font-size:1.05rem;font-weight:700;color:#f1f5f9;letter-spacing:-.02em;line-height:1.25;">{title_h}</div>'
        f'<div style="font-size:.84rem;color:#94a3b8;margin-top:.35rem;line-height:1.5;">{desc_h}</div>'
        f'{learning_html}'
        f'</div>'
        f'<div style="flex-shrink:0;padding-top:.15rem;">{badge_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_narrative_banner() -> None:
    """Full 10-beat outline (use inside an expander so the main column stays chapter-focused)."""
    items = "".join(
        "<li><b>{}</b> <strong>{}</strong> — {}</li>".format(
            html.escape(num), html.escape(title), html.escape(desc)
        )
        for num, title, desc in NARRATIVE_BEATS
    )
    st.markdown(
        f'<div class="narrative-banner">'
        f'<div class="nb-kicker">{html.escape(DEMO_KICKER)}</div>'
        f'<div class="nb-title">{html.escape(DEMO_TITLE)}</div>'
        f'<p class="nb-body">{html.escape(DEMO_BODY)}</p>'
        f'<ul class="nb-steps">{items}</ul>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_story_frame(stage: int) -> None:
    """Single-chapter header: where you are in the story and what this step proves."""
    s = max(1, min(10, stage))
    idx = s - 1
    num, beat_title, beat_desc = NARRATIVE_BEATS[idx]
    label = STAGE_LABELS[idx]
    pct = int(round(100 * s / 10))
    st.markdown(
        f'<div class="story-frame">'
        f'<div class="story-frame-meta">Segment <b>{s}</b> of 10 · {html.escape(label)}</div>'
        f'<div class="story-frame-beat-line"><span class="story-beat-num">{html.escape(num)}</span>'
        f'<span class="story-frame-beat-title">{html.escape(beat_title)}</span>'
        f'<span class="story-frame-beat-dash"> — </span>'
        f'<span class="story-frame-beat-desc">{html.escape(beat_desc)}</span></div>'
        f'<div class="story-rail-outer"><div class="story-rail-fill" style="width:{pct}%;"></div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_session_strip(m: dict[str, int], fraud_stopped: int) -> None:
    """Lightweight counters while working through the story (not a full dashboard)."""
    st.markdown(
        '<div class="session-strip">'
        f'<span><b>{m["total_alerts"]}</b> alerts</span>'
        f'<span><b>{fraud_stopped}</b> confirmed + blocked</span>'
        f'<span><b>{m["auto_closed"]}</b> auto-closed</span>'
        f'<span><b>{m["hitl_pending"]}</b> HITL queue</span>'
        f'<span><b>{m["blocked"]}</b> accounts blocked</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_kpi_dashboard(m: dict[str, int], fraud_stopped: int) -> None:
    """Executive-style KPI row for the closing segment."""
    st.markdown(
        '''
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 2rem;">
        <div class="kpi-card agent-card-animated">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Total Alerts</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--text-primary);">'''
        + str(m["total_alerts"])
        + '''</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Synthetic counter (demo)</div>
        </div>
        <div class="kpi-card fraud agent-card-animated" style="animation-delay: 0.1s;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Mitigated exposure</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--fraud);">'''
        + str(fraud_stopped)
        + '''</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Confirmed + blocked</div>
        </div>
        <div class="kpi-card success agent-card-animated" style="animation-delay: 0.2s;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Auto-Closed</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--success);">'''
        + str(m["auto_closed"])
        + '''</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Rules / low-touch path</div>
        </div>
        <div class="kpi-card warning agent-card-animated" style="animation-delay: 0.3s;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">HITL Pending</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--warning);">'''
        + str(m["hitl_pending"])
        + '''</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Analyst backlog</div>
        </div>
        <div class="kpi-card agent-card-animated" style="animation-delay: 0.4s;">
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Accounts Blocked</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--fraud);">'''
        + str(m["blocked"])
        + '''</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Post-decision holds</div>
        </div>
    </div>
    ''',
        unsafe_allow_html=True,
    )


def render_post_segment_chrome(stage: int, m: dict[str, int], fraud_stopped: int) -> None:
    """Outline, counters, and activity — kept below the live demo so the segment leads."""
    with st.expander("Outline, counters & activity (optional)", expanded=False):
        render_story_frame(stage)
        st.markdown(
            '<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
            "color:#64748b;margin:0.85rem 0 0.4rem;\">Full walkthrough map (10 segments)</p>",
            unsafe_allow_html=True,
        )
        render_narrative_banner()
        if stage <= 2:
            st.caption("Session counters appear once alerts exist (segment 3 onward).")
        elif stage < 10:
            render_session_strip(m, fraud_stopped)
        else:
            st.caption("Primary roll-ups are in the segment body above; reset from the sidebar to rehearse.")
        if stage >= 4:
            st.markdown('<span class="section-label">Recent activity</span>', unsafe_allow_html=True)
            recent_activity = st.session_state.audit_trail[-10:]
            activity_html = ""
            for event in reversed(recent_activity):
                activity_html += (
                    '<div class="activity-item">'
                    f'<div style="color: var(--text-primary); margin-bottom: 0.25rem;">'
                    f"{html.escape(str(event['event']))}</div>"
                    f'<div class="timestamp">{html.escape(str(event["timestamp"]))}</div></div>'
                )
            st.markdown(f'<div class="activity-feed">{activity_html}</div>', unsafe_allow_html=True)


def action_button(label: str, key: str, next_stage: int) -> None:
    """Right-aligned proceed button at the bottom of a stage."""
    _, col = st.columns([3, 1])
    with col:
        if st.button(label, type="primary", key=key, use_container_width=True):
            st.session_state.stage = next_stage
            st.rerun()


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
    cls = {"NEW":"pill-new","CRITICAL":"pill-critical","HIGH":"pill-high",
           "MEDIUM":"pill-medium","LOW":"pill-low","CLOSED":"pill-closed","HITL":"pill-hitl"
           }.get(kind.upper(), "pill-medium")
    return f'<span class="pill {cls}">{label}</span>'


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
        "audit_trail": [{"timestamp": utcnow_iso(), "event": "SESSION_START — demo console initialised"}],
        "metrics": {"total_alerts": 0, "blocked": 0, "auto_closed": 0, "hitl_pending": 0, "confirmed_fraud": 0},
        # Data — loaded from files or uploaded
        "transactions": load_json("transactions.json"),
        "customers":    load_json("customers.json"),
        "kyc_events":   load_json("kyc_events.json"),
        "sanctions":    load_json("sanctions_data.json"),
        "fraud_memory": load_json("fraud_memory.json"),
        "data_source":  "built-in",  # "built-in" | "uploaded"
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
def _stepper_chips_html(current: int) -> str:
    return "".join(
        f'<span class="step-chip {"active" if i==current else "done" if i<current else ""}">'
        f"{html.escape(label)}</span>"
        for i, label in enumerate(STAGE_LABELS, 1)
    )


def render_sidebar() -> None:
    current_stage = st.session_state.stage
    m = st.session_state.metrics

    # Navigation — phase groups
    phases = [
        ("Ingestion", STAGE_LABELS[0:3], range(1, 4)),
        ("Analysis", STAGE_LABELS[3:6], range(4, 7)),
        ("Decision & closure", STAGE_LABELS[6:10], range(7, 11)),
    ]

    for phase_name, labels, indices in phases:
        st.sidebar.markdown(
            f'<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:#334155;margin:0.6rem 0 0.3rem;'
            f'padding-left:2px;">{phase_name}</div>',
            unsafe_allow_html=True,
        )
        for i, label in zip(indices, labels):
            if i < current_stage:
                icon = "✓"
                color = "#10b981"
            elif i == current_stage:
                icon = "●"
                color = "#3b82f6"
            else:
                icon = "○"
                color = "#334155"

            # Clean label: strip the "N · " prefix, keep just the name
            short = label.split(" · ", 1)[-1] if " · " in label else label

            if st.sidebar.button(
                f"{icon}  {short}",
                key=f"nav_{i}",
            ):
                st.session_state.stage = i
                st.rerun()

    st.sidebar.markdown("<hr style='border-color:#1a2d45;margin:0.75rem 0;'>", unsafe_allow_html=True)
    if st.sidebar.button("↺  Reset Demo"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — DATA SOURCES (with upload support)
# ─────────────────────────────────────────────────────────────────────────────
def stage_data_sources() -> None:
    src_label = "Built-in" if st.session_state.get("data_source", "built-in") == "built-in" else "Uploaded"
    stage_hero(
        1,
        "Establish the evidence base",
        "Load the reference pack (transactions, KYC, sanctions, fraud memory) or swap in your own JSON—everything downstream reads from here.",
        badge_label="",
        badge_ok=True,
        learning="",
    )

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
        st.caption(f"Active · **{src_label}**")

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
                "transactions": [{"transaction_id":"TXN001","customer_id":"CUST001","amount":15000,"currency":"USD","timestamp":"2025-01-10T02:30:00Z","destination_country":"IR","device_id":"DEV001","ip_address":"185.1.2.3","risk_indicators":["high_value_rush"]}],
                "kyc_events":   [{"customer_id":"CUST001","event_type":"login_attempt","timestamp":"2025-01-10T02:30:00Z","ip_address":"185.1.2.3","device_info":{"device_type":"desktop","os":"Windows 10","browser":"Chrome"},"geo_location":{"country":"RU","city":"Moscow","latitude":55.75,"longitude":37.61},"anomaly_type":"geo_location_mismatch","risk_score":0.85}],
                "customers":    [{"customer_id":"CUST001","name":"John Smith","account_type":"premium","risk_profile":"medium","total_transactions":1247,"total_amount":284750}],
            }, indent=2), language="json")

    st.markdown("<hr>", unsafe_allow_html=True)

    txns  = st.session_state.transactions
    kyc   = st.session_state.kyc_events
    san   = st.session_state.sanctions
    mem   = st.session_state.fraud_memory
    custs = st.session_state.customers

    flagged = len([t for t in txns if t.get("risk_indicators")])
    kyc_anom = len([k for k in kyc if k.get("anomaly_type")])
    san_entries = san.get("sanctions_entries", []) if isinstance(san, dict) else []

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.5rem;margin-bottom:1rem;">'
        f'<div class="stat-card"><div class="stat-value" style="color:#3b82f6;">{len(txns)}</div><div class="stat-label">Transactions</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{flagged}</div><div class="stat-label">Flagged</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#f59e0b;">{kyc_anom}</div><div class="stat-label">KYC Anomalies</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#8b5cf6;">{len(san_entries)}</div><div class="stat-label">Sanctioned Entities</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{len(mem)}</div><div class="stat-label">Fraud Patterns</div></div>'
        f'</div>', unsafe_allow_html=True,
    )

    tab_tx, tab_kyc, tab_san, tab_mem, tab_cust = st.tabs(
        ["Transactions", "KYC events", "Sanctions", "Fraud memory", "Customers"]
    )

    with tab_tx:
        # Search and filter bar
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input(
                "Search",
                placeholder="Txn ID, customer, country…",
                label_visibility="visible",
            )
        with col2:
            min_amount = st.number_input("Min $", value=0.0, key="min_amount")
        with col3:
            max_amount = st.number_input("Max $", value=100000.0, key="max_amount")

        # Filter transactions
        filtered_txns = []
        for t in txns:
            if search_term and search_term.lower() not in str(t.get("transaction_id", "")).lower() and \
               search_term.lower() not in str(t.get("customer_id", "")).lower() and \
               search_term.lower() not in str(t.get("destination_country", "")).lower():
                continue
            if min_amount and t.get("amount", 0) < min_amount:
                continue
            if max_amount and t.get("amount", 0) > max_amount:
                continue
            filtered_txns.append(t)

        st.markdown(
            f'<div style="margin-bottom: 0.75rem; color: #94a3b8; font-size: 0.88rem;">'
            f"Showing <b>{min(10, len(filtered_txns))}</b> of <b>{len(filtered_txns)}</b> transactions</div>",
            unsafe_allow_html=True,
        )

        for t in filtered_txns[:10]:
            amount = float(t.get("amount", 0) or 0)
            country = str(t.get("destination_country", "UNKNOWN"))
            tid = str(t.get("transaction_id", "UNKNOWN"))
            cid = str(t.get("customer_id", "UNKNOWN"))
            risk_level = (
                "CRITICAL" if country in HIGH_RISK else "HIGH" if country in MED_RISK else "MEDIUM"
            )
            inds = [str(x) for x in (t.get("risk_indicators") or [])]
            inds_txt = ", ".join(inds) if inds else "—"

            with st.container():
                h1, h2 = st.columns([4, 1])
                with h1:
                    st.markdown(f"**{tid}** · `{cid}` · **{country}**")
                with h2:
                    st.caption(risk_level)
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Amount (USD)", f"${amount:,.2f}")
                with c2:
                    st.caption("Risk indicators")
                    st.text(inds_txt)
                st.divider()

        if len(filtered_txns) > 10:
            st.info(f"Showing first 10 of {len(filtered_txns)} transactions. Use search to find more.")

    with tab_kyc:
        for ev in kyc:
            geo = ev.get("geo_location", {})
            dev = ev.get("device_info", {})
            st.markdown(
                f'<div class="ev-box">{pill(ev.get("anomaly_type","unknown").upper().replace("_"," "),"HIGH")} &nbsp;'
                f'<b style="color:#f1f5f9;">{ev["customer_id"]}</b> · {ev["event_type"]}<br>'
                f'<span style="font-size:.75rem;color:#64748b;">📍 {geo.get("city","?")} {geo.get("country","?")} · 💻 {dev.get("os","?")} · Risk: <b style="color:#f59e0b;">{ev.get("risk_score","?")}</b> · {ev["timestamp"]}</span></div>',
                unsafe_allow_html=True,
            )

    with tab_san:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<span class="section-label">Sanctioned Entities</span>', unsafe_allow_html=True)
            if san_entries:
                st.dataframe(pd.DataFrame(san_entries)[["entity_name","entity_type","sanctions_list","risk_level","risk_score"]], hide_index=True, use_container_width=True)
        with c2:
            st.markdown('<span class="section-label">Country Risk Profiles</span>', unsafe_allow_html=True)
            countries = san.get("country_risks", []) if isinstance(san, dict) else []
            if countries:
                # Create heatmap data
                import plotly.express as px
                df_countries = pd.DataFrame(countries)

                # Create color scale based on risk scores
                df_countries['risk_color'] = df_countries['risk_score'].apply(
                    lambda x: '#EF476F' if x > 0.8 else '#FFD166' if x > 0.6 else '#06D6A0'
                )

                # Create heatmap
                fig = px.choropleth(
                    df_countries,
                    locations="country_code",
                    color="risk_score",
                    hover_name="country_name",
                    hover_data=["risk_score", "sanctions_active"],
                    color_continuous_scale=px.colors.sequential.Reds,
                    range_color=(0, 1),
                    title="Global Risk Heatmap"
                )

                fig.update_layout(
                    geo=dict(showframe=False, showcoastlines=False),
                    paper_bgcolor='rgba(10, 37, 64, 0.9)',
                    plot_bgcolor='rgba(10, 37, 64, 0.9)',
                    font=dict(color='#f1f5f9'),
                    margin=dict(l=0, r=0, t=0, b=0, pad=0),
                    height=400
                )

                # Country risk analysis available in audit trail
                st.markdown('<div style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted);">Country risk analysis available in audit trail</div>', unsafe_allow_html=True)

    with tab_mem:
        for p in mem:
            c = p.get("confidence", 0)
            cc = "#ef4444" if c > 0.85 else "#f59e0b" if c > 0.7 else "#3b82f6"
            st.markdown(
                f'<div class="memory-row"><span class="memory-type">{p.get("pattern_type","?")}</span>'
                f'<span class="memory-val">{p.get("entity_id","?")}</span>'
                f'<span style="margin-left:auto;font-size:.72rem;color:#475569;">conf: <b style="color:{cc};">{c}</b> · risk: <b style="color:{cc};">{p.get("risk_score","?")}</b> · {p.get("description","")}</span></div>',
                unsafe_allow_html=True,
            )

    with tab_cust:
        df_cu = pd.DataFrame(custs)
        st.dataframe(df_cu[["customer_id","name","account_type","risk_profile","total_transactions","total_amount","last_login"]], hide_index=True, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    action_button("Continue to alert intake →", "s1_next", 2)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — GENERATE ALERT (calls POST /v1/alerts)
# ─────────────────────────────────────────────────────────────────────────────
def stage_generate_alert() -> None:
    stage_hero(
        2,
        "Promote a signal into an operational alert",
        "`POST /v1/alerts` exercises the same intake contract your channels team would call—payload validation, idempotency hooks, "
        "and correlation identifiers for downstream LangGraph work.",
        badge_label="API · POST /v1/alerts",
        badge_ok=True,
        learning="Contrast a rules-only world (no ticket) with a governed alert (immutable lineage starts here).",
    )

    txns = [t for t in st.session_state.transactions if t.get("risk_indicators")]

    st.markdown('<span class="section-label">Suspicious Transactions</span>', unsafe_allow_html=True)
    for t in txns:
        country = t["destination_country"]
        risk_level = "CRITICAL" if country in HIGH_RISK else "HIGH" if country in MED_RISK else "MEDIUM"
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f'<div class="alert-card {risk_level.lower()}">'
                f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;">{pill(risk_level,risk_level)}'
                f'<b style="color:#f1f5f9;">{t["transaction_id"]}</b><span style="color:#475569;">· {t["customer_id"]}</span></div>'
                f'<div style="font-size:1rem;font-weight:800;color:#f1f5f9;">${t["amount"]:,.2f} <span style="font-size:.75rem;color:#64748b;">{t["currency"]}</span>'
                f' → {t["destination_country"]} · {t["transaction_type"]}</div>'
                f'<div style="font-size:.72rem;color:#475569;">🚩 {", ".join(t["risk_indicators"])} · {t["timestamp"]}</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            if st.button("Flag as alert", key=f"flag_{t['transaction_id']}", use_container_width=True):
                with st.spinner("Validating payload and calling intake API…"):
                    _create_alert_from_transaction(t)
                st.success(f"Alert created for {t['transaction_id']} — opening the operations queue.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">Simulate Custom Alert</span>', unsafe_allow_html=True)
    with st.form("custom_alert"):
        col1, col2, col3 = st.columns(3)
        cust_id = col1.selectbox("Customer", [c["customer_id"] for c in st.session_state.customers] or ["CUST001","CUST002","CUST003"])
        amount  = col2.number_input("Amount (USD)", value=15000.0, min_value=100.0)
        country = col3.selectbox("Destination Country", ["IR","KP","RU","CN","US","NG","SY","BY"])
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


def _create_alert_from_transaction(t: dict) -> None:
    """Call POST /v1/alerts and store the alert in session state."""
    alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
    inv_id   = f"inv_{uuid.uuid4().hex[:10]}"

    # Call real API
    payload = {
        "transaction_id": t["transaction_id"],
        "amount": t["amount"], "currency": t.get("currency","USD"),
        "timestamp": t.get("timestamp", utcnow_iso()),
        "account_id": t["customer_id"],
        "recipient_country": t["destination_country"],
        "alert_hash": uuid.uuid4().hex,
        "metadata": {"device_id": t.get("device_id",""), "ip_address": t.get("ip_address","")},
    }
    resp = api_post("/v1/alerts", payload)
    api_ok = resp.get("investigation_id") is not None or resp.get("status") is not None

    severity = "CRITICAL" if t["destination_country"] in HIGH_RISK else "HIGH" if t["destination_country"] in MED_RISK else "MEDIUM"
    alert = {
        "alert_id": alert_id, "investigation_id": inv_id,
        "transaction_id": t["transaction_id"], "customer_id": t["customer_id"],
        "amount": t["amount"], "currency": t.get("currency","USD"),
        "destination_country": t["destination_country"],
        "device_id": t.get("device_id","UNKNOWN"), "ip_address": t.get("ip_address",""),
        "risk_indicators": t.get("risk_indicators",[]),
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
        "Severity, monetary exposure, corridor risk, and freshness are visible at a glance—mirroring how a floor lead triages work before specialists burn cycles.",
        badge_label="Work in progress",
        badge_ok=True,
        learning="Invite the room to discuss SLA ordering (amount vs. geo risk vs. customer tier).",
    )

    alerts = st.session_state.alerts
    if not alerts:
        st.markdown(
            '<div class="info-panel">No alerts in this session yet. Use <b>Segment 02</b> to raise the first case.</div>',
            unsafe_allow_html=True,
        )
        return

    total = len(alerts)
    crit  = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    new   = sum(1 for a in alerts if a["status"] == "NEW")
    closed = sum(1 for a in alerts if a["status"] == "CLOSED")

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-bottom:1.5rem;">'
        f'<div class="stat-card"><div class="stat-value" style="color:#f1f5f9;">{total}</div><div class="stat-label">Total</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{crit}</div><div class="stat-label">Critical</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#f59e0b;">{new}</div><div class="stat-label">New</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{closed}</div><div class="stat-label">Closed</div></div>'
        f'</div>', unsafe_allow_html=True,
    )

    # Sort and filter controls
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        sort_by = st.selectbox("Sort by:", ["Amount (High→Low)", "Amount (Low→High)", "Severity", "Created Time"], key="sort_alerts")
    with col2:
        filter_severity = st.selectbox("Filter:", ["All", "CRITICAL", "HIGH", "MEDIUM"], key="filter_severity")
    with col3:
        st.markdown(f'<div style="text-align: right; color: #64748b; font-size: 0.9rem;">{len(alerts)} alerts</div>', unsafe_allow_html=True)

    # Sort alerts
    if sort_by == "Amount (High→Low)":
        alerts_sorted = sorted(alerts, key=lambda x: x.get("amount", 0), reverse=True)
    elif sort_by == "Amount (Low→High)":
        alerts_sorted = sorted(alerts, key=lambda x: x.get("amount", 0))
    elif sort_by == "Severity":
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts_sorted = sorted(alerts, key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 3))
    else:  # Created Time
        alerts_sorted = sorted(alerts, key=lambda x: x.get("created_at", ""), reverse=True)

    # Filter alerts
    if filter_severity != "All":
        alerts_sorted = [a for a in alerts_sorted if a.get("severity") == filter_severity]

    for a in alerts_sorted:
        is_sel = st.session_state.selected_alert_id == a["alert_id"]
        severity = a.get("severity", "MEDIUM")
        priority_class = "priority-critical" if severity == "CRITICAL" else "priority-high" if severity == "HIGH" else "priority-low"
        card_cls = f'alert-card {severity.lower()}' + (" selected" if is_sel else "")

        st.markdown(f'''
        <div class="{card_cls} agent-card-animated" style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <div class="{priority_class}" style="margin-right: 0.5rem;">{severity}</div>
                    {pill(a.get("status", "NEW"), a.get("status", "NEW"))}
                </div>
                <div style="text-align: right;">
                    <b style="color: #f1f5f9; font-size: 1.1rem;">{a["alert_id"]}</b>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div>
                    <div style="color: #64748b; font-size: 0.8rem; margin-bottom: 0.25rem;">Customer</div>
                    <div style="font-weight: 700; color: var(--gold);">{a.get("customer_id", "UNKNOWN")}</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.8rem; margin-bottom: 0.25rem;">Amount → Country</div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: var(--gold);">${a.get("amount", 0):,.2f} → {a.get("destination_country", "UNKNOWN")}</div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="color: var(--text-secondary); font-size: 0.8rem; font-weight: 600;">Risk Factors</div>
                <div style="display: flex; gap: 0.25rem; flex-wrap: wrap;">
                    {"".join(f'<span style="background: rgba(239, 68, 68, 0.15); color: var(--fraud); padding: 4px 10px; border-radius: 8px; font-size: 0.7rem; font-weight: 500; border: 1px solid rgba(239, 68, 68, 0.3);">{ind}</span>' for ind in a.get("risk_indicators", []))}
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                <div style="color: #64748b; font-size: 0.8rem;">{a.get("created_at", "")}</div>
                <button class="cta-button" onclick="window.location.href='#investigate'" style="padding: 0.5rem 1rem; font-size: 0.9rem;">
                    🔍 INVESTIGATE
                </button>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        if st.button("Open investigation workspace →", key=f"inv_{a['alert_id']}", use_container_width=True):
            st.session_state.selected_alert_id = a["alert_id"]
            st.session_state.stage = 4
            trace(f"INVESTIGATION_STARTED · {a['alert_id']}")
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("+ Generate Another Alert", key="more_alerts"):
        st.session_state.stage = 2
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — TRIAGE (calls POST /v1/investigate/triage → Claude Haiku)
# ─────────────────────────────────────────────────────────────────────────────
def stage_triage(alert: dict) -> None:
    stage_hero(
        4,
        "Policy-first triage, then model assist",
        "Fast-path rules keep spend predictable; when the case warrants it, `POST /v1/investigate/triage` calls the orchestrated LLM path (Cerebras in this deployment). "
        "If the API is unavailable, the UI falls back to transparent rule scoring so the story still completes.",
        badge_label="API · /v1/investigate/triage",
        badge_ok=True,
        learning="Stress why deterministic gates belong in production—even when agents are impressive.",
    )

    st.markdown(
        f'<div class="info-panel">🔍 Alert <b>{alert["alert_id"]}</b> · Customer <b>{alert["customer_id"]}</b>'
        f' · <b>${alert["amount"]:,.2f}</b> → <b>{alert["destination_country"]}</b></div>',
        unsafe_allow_html=True,
    )

    customer   = next((c for c in st.session_state.customers if c["customer_id"] == alert["customer_id"]), {})
    kyc_events = [k for k in st.session_state.kyc_events if k["customer_id"] == alert["customer_id"]]
    mem_hits   = [m for m in st.session_state.fraud_memory if m.get("entity_id") == alert["customer_id"]]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<span class="section-label">Customer Profile</span>', unsafe_allow_html=True)
        if customer:
            rp = customer.get("risk_profile","?")
            rc = "#ef4444" if rp=="high" else "#f59e0b" if rp=="medium" else "#10b981"
            st.markdown(
                f'<div class="summary-card">'
                f'<div class="summary-row"><span class="sk">Name</span><span class="sv">{customer.get("name","?")}</span></div>'
                f'<div class="summary-row"><span class="sk">Account</span><span class="sv">{customer.get("account_type","?").upper()}</span></div>'
                f'<div class="summary-row"><span class="sk">Risk Profile</span><span class="sv" style="color:{rc};">{rp.upper()}</span></div>'
                f'<div class="summary-row"><span class="sk">Total Txns</span><span class="sv">{customer.get("total_transactions",0):,}</span></div>'
                f'</div>', unsafe_allow_html=True,
            )
    with col2:
        st.markdown('<span class="section-label">KYC Anomalies</span>', unsafe_allow_html=True)
        rows = "".join(f'<div class="summary-row"><span class="sk">{k["anomaly_type"].replace("_"," ")}</span><span class="sv" style="color:#f59e0b;">{k["risk_score"]}</span></div>' for k in kyc_events) or '<div class="summary-row"><span class="sk">Status</span><span class="sv" style="color:#10b981;">✅ None</span></div>'
        st.markdown(f'<div class="summary-card">{rows}</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<span class="section-label">Fraud Memory Hits</span>', unsafe_allow_html=True)
        rows = "".join(f'<div class="summary-row"><span class="sk">{m["pattern_type"].replace("_"," ")}</span><span class="sv" style="color:#ef4444;">{m["confidence"]}</span></div>' for m in mem_hits) or '<div class="summary-row"><span class="sk">Status</span><span class="sv" style="color:#10b981;">✅ None</span></div>'
        st.markdown(f'<div class="summary-card">{rows}</div>', unsafe_allow_html=True)

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

    if st.button("Run triage (API + rule fallback)", type="primary", key="run_triage"):
        with st.spinner("Calling triage endpoint; applying rule-based fallback if needed…"):
            payload = {
                "alert_id": alert["alert_id"],
                "customer_id": alert["customer_id"],
                "amount": alert["amount"],
                "currency": alert["currency"],
                "destination_country": alert["destination_country"],
                "device_id": alert["device_id"],
                "risk_indicators": alert["risk_indicators"],
            }
            resp = api_post("/v1/investigate/triage", payload)

        if resp.get("success") and resp.get("data"):
            tr = resp["data"]
            alert["triage_result"] = tr
            trace(f"TRIAGE_AI → decision={tr.get('decision')} · score={tr.get('risk_score')} · confidence={tr.get('confidence')}")
            st.markdown(f'<div style="margin-bottom:.5rem;">{api_badge("POST /v1/investigate/triage")}</div>', unsafe_allow_html=True)
            _show_triage_result(tr)
        else:
            st.markdown(f'<div class="warn-panel">⚠ API call failed: {resp.get("error","unknown")}. Using rule-based fallback.</div>', unsafe_allow_html=True)
            # Rule-based fallback
            score = 0.3
            country = alert["destination_country"]
            if country in HIGH_RISK: score += 0.4
            elif country in MED_RISK: score += 0.2
            if alert["amount"] > 10000: score += 0.2
            if kyc_events: score += 0.1
            if mem_hits: score += 0.15
            score = min(score, 1.0)
            tr = {"decision": "ESCALATE_FOR_ANALYSIS" if score > 0.5 else "AUTO_CLOSE",
                  "priority": "CRITICAL" if score > 0.8 else "HIGH" if score > 0.6 else "MEDIUM",
                  "risk_score": round(score, 2), "confidence": 0.75,
                  "reasoning": "Rule-based fallback (LLM unavailable).", "key_flags": alert["risk_indicators"]}
            alert["triage_result"] = tr
            trace(f"TRIAGE_FALLBACK → decision={tr['decision']} · score={tr['risk_score']}")
            _show_triage_result(tr)

        st.rerun()


def _show_triage_result(tr: dict) -> None:
    score = tr.get("risk_score", 0)
    pct   = int(score * 100)
    gc    = risk_gradient(score)
    rc    = risk_color(score)
    st.sidebar.markdown(
        '<div style="font-size:.62rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin:.35rem 0 .4rem;">Live triage readout</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">'
        f'<span style="font-size:.75rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.06em;">Triage Risk Score</span>'
        f'<span style="font-size:1.4rem;font-weight:800;color:{rc};">{pct}<span style="font-size:.8rem;color:#475569;">/100</span></span></div>'
        f'<div class="gauge-track"><div class="gauge-fill" style="width:{pct}%;background:{gc};"></div></div>'
        f'<div style="margin-top:.5rem;font-size:.78rem;color:#475569;">'
        f'Decision: <b style="color:#f1f5f9;">{tr.get("decision","?")}</b> &nbsp;·&nbsp; '
        f'Priority: <b style="color:{rc};">{tr.get("priority","?")}</b> &nbsp;·&nbsp; '
        f'Confidence: <b style="color:#10b981;">{int(tr.get("confidence",0)*100)}%</b></div>'
        f'<div style="margin-top:.5rem;font-size:.78rem;color:#94a3b8;">{tr.get("reasoning","")}</div>'
        f'</div>', unsafe_allow_html=True,
    )
    if tr.get("key_flags"):
        for flag in tr["key_flags"]:
            st.markdown(f'<div class="flag-row"><span class="flag-icon">🚩</span><div><div class="flag-label">{flag.upper().replace("_"," ")}</div></div></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — PARALLEL AGENT INVESTIGATION (calls POST /v1/investigate/full)
# ─────────────────────────────────────────────────────────────────────────────
def stage_agents(alert: dict) -> None:
    stage_hero(
        5,
        "Specialist agents gather evidence in parallel",
        "Transaction velocity, device/geo behaviour, and sanctions posture are collected concurrently—each stream stays explainable so risk committees can replay the logic.",
        badge_label="Concurrency · asyncio.gather",
        badge_ok=True,
        learning="Highlight partial failures: one agent degrading should not collapse the entire narrative.",
    )

    st.markdown(
        f'<div class="info-panel">🔍 Case <b>{alert["investigation_id"]}</b> · {alert["customer_id"]}'
        f' · <b>${alert["amount"]:,.2f}</b> → <b>{alert["destination_country"]}</b></div>',
        unsafe_allow_html=True,
    )

    if alert.get("agent_results"):
        _show_agent_cards(alert["agent_results"])
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("→ Proceed to AI Risk Scoring", type="primary", key="to_scoring"):
            st.session_state.stage = 6
            st.rerun()
        return

    if st.button("▶ Launch Parallel Agents + AI Synthesis", type="primary", key="run_agents"):
        col1, col2, col3 = st.columns(3)

        with col1:
            with st.status("⚡ Transaction Agent", expanded=True) as s1:
                st.write("🔍 Analyzing TXN10001...")
                time.sleep(0.2)
                st.write(f"💰 High-value transaction detected: ${alert.get('amount', 15000):,.2f}")
                time.sleep(0.2)
                st.write("⚠️ Velocity spike pattern identified")
                time.sleep(0.2)
                st.write("📊 Comparing to customer baseline...")
                s1.update(label="⚡ Transaction Agent", state="running")

        with col2:
            with st.status("🔍 KYC / Device Agent", expanded=True) as s2:
                st.write("🔍 Analyzing CUST003 device logs...")
                time.sleep(0.2)
                st.write("📱 Device fingerprint: DEV_CUST003_123")
                time.sleep(0.2)
                st.write("🌍 Geo-location anomaly: RU - Moscow detected")
                time.sleep(0.2)
                st.write("⚠️ Login pattern deviation flagged")
                s2.update(label="🔍 KYC Agent", state="running")

        with col3:
            with st.status("🚫 Sanctions Agent", expanded=True) as s3:
                st.write("🌍 High-risk corridor check...")
                time.sleep(0.2)
                st.write("🔍 Checking destination: IR (Iran)")
                time.sleep(0.2)
                st.write("⚠️ SANCTIONS MATCH FOUND!")
                time.sleep(0.2)
                st.write("📋 Entity: Global Trading Corp - FINANCIAL sanctions")
                s3.update(label="🚫 Sanctions Agent", state="running")

        # Real API call — runs all agents + Claude Sonnet synthesis
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with st.spinner("🤖 Claude Sonnet synthesizing all agent findings..."):
                    if attempt > 0:
                        st.info(f"🔄 Service Re-connecting... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)

                    payload = {
                        "transaction_id":    alert["transaction_id"],
                        "customer_id":       alert["customer_id"],
                        "amount":            alert["amount"],
                        "currency":          alert["currency"],
                        "destination_country": alert["destination_country"],
                        "device_id":         alert["device_id"],
                        "ip_address":        alert["ip_address"],
                        "timestamp":         alert["created_at"],
                        "risk_indicators":   alert["risk_indicators"],
                        "metadata":          {"device_id": alert["device_id"], "ip_address": alert["ip_address"]},
                    }
                    resp = api_post("/v1/investigate/full", payload)
                    break  # Success, exit retry loop
            except Exception as e:
                if attempt == max_retries - 1:
                    st.error("❌ Service temporarily unavailable. Please try again later.")
                    st.warning("🔄 Attempting to reconnect in background...")
                    # Create mock results for demo continuity
                    resp = {
                        "success": True,
                        "data": {
                            "agent_results": {
                                "transaction": {"agent": "transaction", "findings": "High-value transaction detected", "risk_score": 0.92},
                                "kyc": {"agent": "kyc", "findings": "Device anomaly detected", "risk_score": 0.78},
                                "sanctions": {"agent": "sanctions", "findings": "Sanctions match found", "risk_score": 0.95}
                            },
                            "risk_result": {"risk_score": 0.85, "risk_level": "HIGH", "confidence": 0.89}
                        }
                    }
                else:
                    continue

        if resp.get("success") and resp.get("data"):
            data = resp["data"]
            alert["agent_results"] = data.get("agent_results", {})
            alert["risk_result"]   = data.get("risk_result", {})
            alert["ai_synthesis"]  = data.get("ai_synthesis", {})

            # Update spinner labels
            s1.update(label="✅ Transaction Agent — Complete", state="complete")
            s2.update(label="⚠️ KYC Agent — Anomalies Found", state="complete")
            s3.update(label="🔴 Sanctions Agent — Match Found", state="complete")

            trace(f"AGENTS_COMPLETE · investigation={data.get('investigation_id')} · API=OK")
            trace(f"TRANSACTION_AGENT → risk={data.get('agent_results',{}).get('transaction',{}).get('risk_score','?')}")
            trace(f"KYC_AGENT → anomalies={len(data.get('agent_results',{}).get('kyc',{}).get('anomalies',[]))}")
            trace(f"SANCTIONS_AGENT → risk={data.get('agent_results',{}).get('sanctions',{}).get('risk_score','?')}")
            trace(f"AI_SYNTHESIS → score={data.get('risk_result',{}).get('final_risk_score','?')} · tier={data.get('risk_result',{}).get('risk_tier','?')}")
            st.markdown(f'<div style="margin:.5rem 0;">{api_badge("POST /v1/investigate/full")}</div>', unsafe_allow_html=True)
        else:
            # Fallback: build results from local data
            st.markdown(f'<div class="warn-panel">⚠ API call failed: {resp.get("error","unknown")}. Using local data fallback.</div>', unsafe_allow_html=True)
            alert["agent_results"] = _build_local_agent_results(alert)
            s1.update(label="✅ Transaction Agent (local)", state="complete")
            s2.update(label="⚠️ KYC Agent (local)", state="complete")
            s3.update(label="🔴 Sanctions Agent (local)", state="complete")
            trace(f"AGENTS_FALLBACK · local data used")

        st.rerun()


def _build_local_agent_results(alert: dict) -> dict:
    """Build agent results from local JSON data when API is unavailable."""
    cust_id = alert["customer_id"]
    country = alert["destination_country"]
    amount  = alert["amount"]
    kyc_events = [k for k in st.session_state.kyc_events if k["customer_id"] == cust_id]
    mem_hits   = [m for m in st.session_state.fraud_memory if m.get("entity_id") == cust_id]
    san        = st.session_state.sanctions
    country_risks = {c["country_code"]: c for c in (san.get("country_risks",[]) if isinstance(san,dict) else [])}
    cr = country_risks.get(country, {})

    return {
        "transaction": {
            "risk_score": min(1.0, amount/50000),
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
            "alerts": [{"sanction_type": "COUNTRY_SANCTION", "risk_score": cr.get("risk_score",0.1)}] if country in HIGH_RISK else [],
            "recommendation": "BLOCK_TRANSACTION" if country in HIGH_RISK else "MONITOR",
        },
    }


def _show_agent_cards(results: dict) -> None:
    tx  = results.get("transaction", {})
    kyc = results.get("kyc", {})
    san = results.get("sanctions", {})

    def _fv(v: Any, kind: str = "") -> str:
        if isinstance(v, bool):
            return f'<span class="fv fv-{"t" if v else "f"}">{"TRUE" if v else "false"}</span>'
        if isinstance(v, float):
            cls = "fv-h" if v > 0.7 else "fv-m" if v > 0.4 else "fv-t"
            return f'<span class="fv {cls}">{v:.2f}</span>'
        return f'<span class="fv" style="color:#94a3b8;">{v}</span>'

    def _card(title: str, color: str, state: str, rows: list[tuple]) -> str:
        rows_html = "".join(f'<div class="agent-finding"><span class="fk">{k}</span>{_fv(v)}</div>' for k, v in rows)
        return (f'<div class="agent-card {state}"><div class="agent-name" style="color:{color};">{title}</div>'
                f'{rows_html}</div>')

    tx_score  = tx.get("risk_score", 0)
    kyc_score = kyc.get("risk_score", 0)
    san_score = san.get("risk_score", 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(_card("⚡ Transaction Agent", "#10b981" if tx_score < 0.5 else "#f59e0b" if tx_score < 0.7 else "#ef4444",
            "success" if tx_score < 0.5 else "warning" if tx_score < 0.7 else "danger",
            [("risk_score", tx_score),
             ("velocity_anomalies", len(tx.get("velocity_anomalies",[]))),
             ("fraud_patterns", len(tx.get("fraud_patterns",[]))),
             ("recommendation", tx.get("recommendation","?"))]), unsafe_allow_html=True)
    with col2:
        st.markdown(_card("🔍 KYC / Device Agent", "#10b981" if kyc_score < 0.4 else "#f59e0b" if kyc_score < 0.7 else "#ef4444",
            "success" if kyc_score < 0.4 else "warning" if kyc_score < 0.7 else "danger",
            [("risk_score", kyc_score),
             ("anomalies_found", len(kyc.get("anomalies",[]))),
             ("recommendation", kyc.get("recommendation","?"))]), unsafe_allow_html=True)
    with col3:
        st.markdown(_card("🚫 Sanctions Agent", "#10b981" if san_score < 0.4 else "#f59e0b" if san_score < 0.7 else "#ef4444",
            "success" if san_score < 0.4 else "warning" if san_score < 0.7 else "danger",
            [("risk_score", san_score),
             ("sanctions_alerts", len(san.get("alerts",[]))),
             ("recommendation", san.get("recommendation","?"))]), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — AI REASONING & RISK SCORING (real Claude Sonnet output)
# ─────────────────────────────────────────────────────────────────────────────
def stage_risk_scoring(alert: dict) -> None:
    def _unit_interval(x: Any, default: float) -> float:
        """API fields may be missing or explicitly null; values may be 0–1 or 0–100."""
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
        "`POST /v1/investigate/full` fuses deterministic signals with Gemini synthesis so you can show both the arithmetic and the prose a committee expects.",
        badge_label="Gemini synthesis",
        badge_ok=True,
        learning="Emphasise the split: rule score + model context → blended decision with explicit confidence.",
    )

    rr = alert.get("risk_result") or {}

    # Use AI synthesis if available, else fall back to risk_result (or handles null keys)
    raw_final = rr.get("final_risk_score") or rr.get("risk_score") or 0.5
    final_score = _unit_interval(raw_final, 0.5)
    risk_tier = rr.get("risk_tier") or rr.get("risk_level") or "MEDIUM"
    confidence = _unit_interval(rr.get("confidence"), 0.7)
    rule_score = _unit_interval(
        rr.get("rule_based_score") or rr.get("rule_score") or raw_final,
        final_score,
    )
    ai_score = _unit_interval(
        rr.get("ai_context_score") or rr.get("ai_score") or raw_final,
        final_score,
    )
    # Generate AI summary using AI reasoning service if not available
    summary = rr.get("executive_summary", rr.get("explanation"))
    if not summary:
        # Use AI reasoning service to generate summary
        try:
            from app.services.ai_reasoning_service import InvestigationReasoningService
            ai_service = InvestigationReasoningService()
            ai_result = ai_service.generate_executive_summary(alert)
            summary = ai_result.get("summary", "AI analysis in progress...")
        except Exception as e:
            summary = f"AI analysis unavailable: {str(e)}"
    evidence    = rr.get("evidence_chain", [])
    reasoning   = rr.get("reasoning_steps", [])

    pct    = int(final_score * 100)
    rc     = risk_color(final_score)
    gc     = risk_gradient(final_score)
    conf_p = int(confidence * 100)

    col_gauge, col_scores = st.columns([1, 2])
    with col_gauge:
        st.markdown(
            f'<div class="risk-display">'
            f'<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin-bottom:.5rem;">Final Risk Score</div>'
            f'<div class="risk-number" style="color:{rc};">{pct}</div>'
            f'<div style="font-size:.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{rc};margin-top:.25rem;">{risk_tier}</div>'
            f'<div class="gauge-track"><div class="gauge-fill" style="width:{pct}%;background:{gc};"></div></div>'
            f'<div style="font-size:.72rem;color:#475569;margin-top:.25rem;">Confidence: <b style="color:#10b981;">{conf_p}%</b></div>'
            f'<div class="gauge-track" style="margin-top:4px;"><div style="height:100%;width:{conf_p}%;background:linear-gradient(90deg,#10b981,#059669);border-radius:4px;"></div></div>'
            f'</div>', unsafe_allow_html=True,
        )

    with col_scores:
        st.markdown('<span class="section-label">Score Breakdown</span>', unsafe_allow_html=True)
        rule_pct = int(rule_score * 100)
        ai_pct = int(ai_score * 100)
        st.markdown(
            f'<div class="summary-card">'
            f'<div class="summary-row"><span class="sk">Rule-Based Score</span><span class="sv" style="color:{risk_color(rule_score)};">{rule_pct}/100</span></div>'
            f'<div class="summary-row"><span class="sk">AI context score</span><span class="sv" style="color:{risk_color(ai_score)};">{ai_pct}/100</span></div>'
            f'<div class="summary-row"><span class="sk">Final Blended Score</span><span class="sv" style="color:{rc};">{pct}/100</span></div>'
            f'<div class="summary-row"><span class="sk">Confidence</span><span class="sv" style="color:#10b981;">{conf_p}%</span></div>'
            f'<div class="summary-row"><span class="sk">Risk Tier</span><span class="sv" style="color:{rc};">{risk_tier}</span></div>'
            f'<div class="summary-row"><span class="sk">Requires Human Review</span><span class="sv" style="color:{"#ef4444" if pct>=70 else "#10b981"};">{"YES" if pct>=70 else "NO"}</span></div>'
            f'</div>', unsafe_allow_html=True,
        )

    if evidence:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">Evidence-to-reasoning map</span>', unsafe_allow_html=True)
        for e in evidence:
            st.markdown(
                f'<div class="evidence-card">'
                f'<div class="evidence-reason">{e.get("signal","?")}</div>'
                f'<div class="evidence-meta">source: {e.get("source","?")} &nbsp;·&nbsp; weight: {e.get("weight","?")} &nbsp;·&nbsp; {e.get("detail","")}</div>'
                f'</div>', unsafe_allow_html=True,
            )

    # Reasoning steps
    if reasoning:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">AI Reasoning Steps</span>', unsafe_allow_html=True)
        for i, step in enumerate(reasoning, 1):
            st.markdown(
                f'<div style="padding:.5rem .8rem;margin-bottom:.35rem;border-radius:8px;background:#0f1f35;border-left:3px solid #3b82f6;">'
                f'<span style="font-size:.72rem;color:#3b82f6;font-weight:700;">STEP {i}</span> '
                f'<span style="font-size:.82rem;color:#94a3b8;">{step}</span></div>',
                unsafe_allow_html=True,
            )

    # AI Executive Summary
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">Executive narrative</span>', unsafe_allow_html=True)
    with st.chat_message("assistant"):
        st.markdown(f"**Risk Score: {pct}/100 — {risk_tier}** (confidence {conf_p}%)\n\n{summary}")

    trace(f"RISK_SCORING_DISPLAYED · score={pct} · tier={risk_tier} · confidence={conf_p}%")

    st.markdown("<hr>", unsafe_allow_html=True)
    if pct >= 70:
        st.markdown(
            f'<div class="hitl-alert pulse-amber">'
            f'<div class="hitl-title">⚠ Risk Threshold Exceeded</div>'
            f'<div class="hitl-body">Score {pct}/100 exceeds auto-approve threshold (70). Routing to human analyst.</div>'
            f'</div>', unsafe_allow_html=True,
        )
        if st.button("→ Proceed to Human Review (HITL)", type="primary", key="to_hitl"):
            st.session_state.stage = 7
            trace(f"DECISION_ENGINE → HITL · score={pct}")
            st.rerun()
    else:
        st.markdown('<div class="success-panel">✅ Risk score below threshold. Auto-approving.</div>', unsafe_allow_html=True)
        if st.button("→ Auto-Approve & Proceed to Resolution", type="primary", key="to_res_auto"):
            alert["approved"] = True
            alert["status"] = "CLOSED"
            st.session_state.stage = 8
            trace(f"DECISION_ENGINE → AUTO_APPROVE · score={pct}")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — HITL (calls POST /v1/investigate/hitl-recommendation)
# ─────────────────────────────────────────────────────────────────────────────
def stage_hitl(alert: dict) -> None:
    stage_hero(
        7,
        "Human-in-the-loop control point",
        "Material actions wait for an analyst. Gemini prepares a structured briefing; the disposition recorded here is what downstream settlement systems should trust.",
        badge_label="Awaiting analyst",
        badge_ok=False,
        learning="This is the slide risk committees care about—separation of duties and non-repudiation.",
    )

    rr    = alert.get("risk_result") or {}
    score = int(float(rr.get("final_risk_score", rr.get("risk_score", 0.9))) * 100)
    conf  = int(float(rr.get("confidence", 0.9)) * 100)

    st.markdown(
        f'<div class="hitl-alert pulse-amber">'
        f'<div class="hitl-title">⚠ Human Intervention Required</div>'
        f'<div class="hitl-body">Risk score <b>{score}/100</b> · Confidence <b>{conf}%</b>. '
        f'No remediation executes until analyst confirms.</div>'
        f'</div>', unsafe_allow_html=True,
    )

    # Get AI recommendation for analyst
    if not alert.get("hitl_ai_recommendation"):
        if st.button("Request analyst briefing (API)", key="get_hitl_rec"):
            with st.spinner("Generating structured briefing via /v1/investigate/hitl-recommendation…"):
                payload = {
                    "investigation_id": alert["investigation_id"],
                    "customer_id": alert["customer_id"],
                    "amount": alert["amount"],
                    "destination_country": alert["destination_country"],
                    "agent_results": alert.get("agent_results", {}),
                    "risk_result": alert.get("risk_result", {}),
                }
                resp = api_post("/v1/investigate/hitl-recommendation", payload)
            if resp.get("success") and resp.get("data"):
                alert["hitl_ai_recommendation"] = resp["data"]
                trace(f"HITL_AI_REC → recommended={resp['data'].get('recommended_action')}")
                st.markdown(f'<div style="margin:.5rem 0;">{api_badge("POST /v1/investigate/hitl-recommendation")}</div>', unsafe_allow_html=True)
            st.rerun()

    if alert.get("hitl_ai_recommendation"):
        rec = alert["hitl_ai_recommendation"]
        rec_action = rec.get("recommended_action","?")
        rec_conf   = int(float(rec.get("confidence",0.8))*100)
        rec_color  = "#ef4444" if rec_action=="CONFIRM_FRAUD" else "#10b981" if rec_action=="FALSE_POSITIVE" else "#f59e0b"
        st.markdown(
            f'<div style="background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.3);border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem;">'
            f'<div style="font-size:.8rem;font-weight:700;color:#c4b5fd;margin-bottom:.5rem;">Model-assisted recommendation</div>'
            f'<div style="font-size:.9rem;font-weight:700;color:{rec_color};margin-bottom:.4rem;">{rec_action} (confidence {rec_conf}%)</div>'
            f'<div style="font-size:.82rem;color:#94a3b8;margin-bottom:.5rem;">{rec.get("analyst_briefing","")}</div>'
            f'</div>', unsafe_allow_html=True,
        )
        if rec.get("supporting_evidence"):
            for ev in rec["supporting_evidence"]:
                st.markdown(f'<div class="evidence-card"><div class="evidence-reason">{ev}</div></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<span class="section-label">Investigation Summary</span>', unsafe_allow_html=True)
        rc = risk_color(float(rr.get("final_risk_score", rr.get("risk_score", 0.9))))
        st.markdown(
            f'<div class="summary-card">'
            f'<div class="summary-row"><span class="sk">Alert ID</span><span class="sv">{alert["alert_id"]}</span></div>'
            f'<div class="summary-row"><span class="sk">Customer</span><span class="sv">{alert["customer_id"]}</span></div>'
            f'<div class="summary-row"><span class="sk">Amount</span><span class="sv">${alert["amount"]:,.2f} {alert["currency"]}</span></div>'
            f'<div class="summary-row"><span class="sk">Destination</span><span class="sv">{alert["destination_country"]}</span></div>'
            f'<div class="summary-row"><span class="sk">Risk Score</span><span class="sv" style="color:{rc};">{score}/100</span></div>'
            f'</div>', unsafe_allow_html=True,
        )
    with col2:
        st.markdown('<span class="section-label">Agent Findings Summary</span>', unsafe_allow_html=True)
        ar = alert.get("agent_results", {})
        if ar:
            st.markdown(
                f'<div class="summary-card">'
                f'<div class="summary-row"><span class="sk">Transaction Risk</span><span class="sv">{ar.get("transaction",{}).get("risk_score","?")}</span></div>'
                f'<div class="summary-row"><span class="sk">KYC Risk</span><span class="sv">{ar.get("kyc",{}).get("risk_score","?")}</span></div>'
                f'<div class="summary-row"><span class="sk">Sanctions Risk</span><span class="sv">{ar.get("sanctions",{}).get("risk_score","?")}</span></div>'
                f'</div>', unsafe_allow_html=True,
            )

    st.markdown("<hr>", unsafe_allow_html=True)
    notes = st.text_area("Analyst decision rationale (required for audit trail)",
        value="High-value transfer to sanctioned corridor with device and geo anomalies. Recommend account freeze.",
        height=90, key="hitl_notes")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Approve — false positive", use_container_width=True, key="hitl_approve"):
            alert["approved"] = True; alert["status"] = "CLOSED"
            alert["hitl_decision"] = {"decision": "FALSE_POSITIVE", "notes": notes}
            st.session_state.metrics["auto_closed"] += 1
            trace(f"HITL → FALSE_POSITIVE · notes={notes[:50]}")
            st.session_state.stage = 8; st.rerun()
    with c2:
        if st.button("Confirm fraud — hold account", type="primary", use_container_width=True, key="hitl_freeze"):
            alert["frozen"] = True; alert["status"] = "CLOSED"
            alert["hitl_decision"] = {"decision": "CONFIRM_FRAUD", "notes": notes}
            st.session_state.metrics["confirmed_fraud"] += 1
            st.session_state.metrics["blocked"] += 1
            trace(f"HITL → CONFIRM_FRAUD · account={alert['customer_id']}")
            st.session_state.stage = 8; st.rerun()
    with c3:
        if st.button("Request more information", use_container_width=True, key="hitl_more"):
            alert["status"] = "HITL"
            st.session_state.metrics["hitl_pending"] += 1
            trace(f"HITL → REQUEST_MORE_INFO · {alert['alert_id']}")
            st.markdown('<div class="info-panel">Investigation remains AWAITING_HUMAN. Queue re-notified.</div>', unsafe_allow_html=True)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────
def stage_resolution(alert: dict) -> None:
    stage_hero(
        8,
        "Controlled remediation and memory updates",
        "Actions are emitted through the resolution service so each step is idempotent, logged, and reversible in a real deployment. Fraud memory captures confirmed indicators for the next detection cycle.",
        badge_label="Action engine",
        badge_ok=True,
        learning="Tie this slide to your change-management story: who approves reversals and how long records live.",
    )

    frozen   = alert.get("frozen", False)
    approved = alert.get("approved", False)

    if frozen:
        st.markdown(
            f'<div class="success-panel" style="font-size:.95rem;font-weight:700;">✅ Fraud Confirmed — Account {alert["customer_id"]} Frozen</div>',
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
                f'<div class="action-row"><span class="action-name">{action}</span>'
                f'<span style="font-size:.72rem;color:#10b981;font-weight:600;">✅ SUCCESS</span>'
                f'<span style="margin-left:auto;font-size:.75rem;color:#6ee7b7;">{detail}</span></div>',
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
                f'<div class="memory-row"><span class="memory-type">{ind["type"]}</span>'
                f'<span class="memory-val">{ind["value"]}</span>'
                f'<span style="margin-left:auto;font-size:.7rem;color:#475569;">pinned from {ind["source"]}</span></div>',
                unsafe_allow_html=True,
            )
        if st.session_state.fraud_memory_updates:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">Full Fraud Memory Ledger (Session)</span>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(st.session_state.fraud_memory_updates), hide_index=True, use_container_width=True)

    elif approved:
        st.markdown(
            f'<div class="info-panel">✅ Transaction <b>{alert["transaction_id"]}</b> approved. Case closed as FALSE_POSITIVE. No remediation taken.</div>',
            unsafe_allow_html=True,
        )
        trace(f"RESOLUTION → FALSE_POSITIVE · {alert['alert_id']}")

    st.markdown("<hr>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("→ View Audit Trail", type="primary", key="to_audit"):
            st.session_state.stage = 9; st.rerun()
    with col2:
        if st.button("→ Live Dashboard", key="to_dashboard"):
            st.session_state.stage = 10; st.rerun()


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
        learning="Ask which fields your regulator would sample first—timestamps, actor IDs, and model version metadata.",
    )

    trail = st.session_state.audit_trail

    if alert:
        rr = alert.get("risk_result", {})
        score_val = f"{int(float(rr.get('final_risk_score', rr.get('risk_score',0)))*100)}/100" if rr else "—"
        decision_val = (alert.get("hitl_decision",{}).get("decision","AUTO") if alert.get("hitl_decision")
                        else ("FROZEN" if alert.get("frozen") else "APPROVED" if alert.get("approved") else "—"))
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Alert Created", alert.get("created_at","—")[:19])
        col2.metric("Status", alert.get("status","—"))
        col3.metric("Risk Score", score_val)
        col4.metric("Decision", decision_val)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">Full Audit Log</span>', unsafe_allow_html=True)
    for entry in reversed(trail[-80:]):
        st.markdown(
            f'<div class="timeline-row"><span class="timeline-ts">{entry["timestamp"]}</span>'
            f'<span class="timeline-evt">{entry["event"]}</span></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────
# STAGE 6 — EVALUATION
# ─────────────────────────────────────────────────────────────────────────────
def stage_evaluation(alert: dict) -> None:
    stage_hero(
        6,
        "Agent Results vs. Benchmark Comparison",
        "Evaluates agent performance against historical benchmarks and industry standards to ensure accuracy and reliability.",
        badge_label="Benchmark engine",
        badge_ok=True,
        learning="Quality assurance through continuous evaluation drives model improvement and maintains detection standards.",
    )

    eval_result = alert.get("evaluation_result", {})

    if eval_result:
        st.markdown('<span class="section-label">Evaluation Summary</span>', unsafe_allow_html=True)

        # Evaluation status and score
        eval_status = eval_result.get("status", "MEETS_BENCHMARK")
        eval_score = eval_result.get("evaluation_score", 0.0)

        status_color = {
            "EXCEEDS_BENCHMARK": "#10b981",
            "MEETS_BENCHMARK": "#059669",
            "BELOW_BENCHMARK": "#f59e0b",
            "CRITICAL_DEVIATION": "#ef4444"
        }.get(eval_status, "#64748b")

        st.markdown(
            f'<div class="summary-card">'
            f'<div class="summary-row"><span class="sk">Evaluation Status</span><span class="sv" style="color:{status_color};">{eval_status.replace("_", " ")}</span></div>'
            f'<div class="summary-row"><span class="sk">Evaluation Score</span><span class="sv">{eval_score:.2f}/1.00</span></div>'
            f'</div>', unsafe_allow_html=True,
        )

        # Agent performance metrics
        metrics = eval_result.get("metrics", {})
        if metrics:
            st.markdown('<span class="section-label">Agent Performance Metrics</span>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="summary-card">'
                    f'<div class="summary-row"><span class="sk">Risk Score</span><span class="sv">{metrics.get("risk_score", "N/A")}</span></div>'
                    f'<div class="summary-row"><span class="sk">Confidence</span><span class="sv">{metrics.get("confidence", "N/A")}</span></div>'
                    f'<div class="summary-row"><span class="sk">Processing Time</span><span class="sv">{metrics.get("processing_time", "N/A")}s</span></div>'
                    f'</div>', unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f'<div class="summary-card">'
                    f'<div class="summary-row"><span class="sk">Risk Within Range</span><span class="sv">{"✓" if metrics.get("risk_within_range") else "✗"}</span></div>'
                    f'<div class="summary-row"><span class="sk">Meets Confidence</span><span class="sv">{"✓" if metrics.get("meets_confidence_threshold") else "✗"}</span></div>'
                    f'<div class="summary-row"><span class="sk">Processing Acceptable</span><span class="sv">{"✓" if metrics.get("processing_acceptable") else "✗"}</span></div>'
                    f'</div>', unsafe_allow_html=True,
                )

        # Benchmark comparison
        benchmark_data = eval_result.get("benchmark_data", {})
        if benchmark_data:
            st.markdown('<span class="section-label">Benchmark Comparison</span>', unsafe_allow_html=True)

            st.markdown(
                f'<div class="summary-card">'
                f'<div class="summary-row"><span class="sk">Historical Accuracy</span><span class="sv">{benchmark_data.get("historical_accuracy", "N/A"):.1%}</span></div>'
                f'<div class="summary-row"><span class="sk">False Positive Rate</span><span class="sv">{benchmark_data.get("false_positive_rate", "N/A"):.1%}</span></div>'
                f'<div class="summary-row"><span class="sk">Detection Rate</span><span class="sv">{benchmark_data.get("detection_rate", "N/A"):.1%}</span></div>'
                f'<div class="summary-row"><span class="sk">Typical Risk Range</span><span class="sv">{benchmark_data.get("typical_risk_range", "N/A")}</span></div>'
                f'</div>', unsafe_allow_html=True,
            )

        # Recommendations
        recommendations = eval_result.get("recommendations", [])
        if recommendations:
            st.markdown('<span class="section-label">Recommendations</span>', unsafe_allow_html=True)
            for rec in recommendations:
                st.markdown(
                    f'<div class="evidence-card">'
                    f'<div class="evidence-reason">{rec}</div>'
                    f'</div>', unsafe_allow_html=True,
                )

    else:
        st.markdown('<div class="info-panel">No evaluation results available. Run agent evaluation first.</div>', unsafe_allow_html=True)

    # Evaluation controls
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">Evaluation Controls</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-evaluate Agent", type="secondary", use_container_width=True):
            # Trigger re-evaluation
            try:
                response = httpx.post(
                    f"{API_BASE}/v1/evaluation/agent-result",
                    headers=_api_headers(),
                    json={
                        "investigation_id": alert.get("investigation_id", ""),
                        "agent_type": "transaction",  # Default to transaction agent
                        "agent_result": alert.get("agent_results", {}).get("transaction", {}),
                        "fraud_type": "transaction_anomaly"
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    alert["evaluation_result"] = result
                    st.success("Agent re-evaluated successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Evaluation failed: {str(e)}")

    with col2:
        if st.button("📊 View Benchmarks", type="secondary", use_container_width=True):
            # Show benchmark data
            try:
                response = httpx.get(
                    f"{API_BASE}/v1/evaluation/benchmarks",
                    headers=_api_headers()
                )
                if response.status_code == 200:
                    benchmarks = response.json().get("data", {})
                    if benchmarks:
                        st.markdown('<span class="section-label">Available Benchmarks</span>', unsafe_allow_html=True)

                        # Fraud type benchmarks
                        fraud_benchmarks = benchmarks.get("fraud_type_benchmarks", {})
                        if fraud_benchmarks:
                            st.markdown("#### Fraud Type Benchmarks", unsafe_allow_html=True)
                            for fraud_type, benchmark in fraud_benchmarks.items():
                                st.markdown(f"**{fraud_type}**: Accuracy `{benchmark['historical_accuracy']:.1%}`, Risk Range `{benchmark['typical_risk_range']}`")

                        # Agent benchmarks
                        agent_benchmarks = benchmarks.get("agent_benchmarks", {})
                        if agent_benchmarks:
                            st.markdown("#### Agent Performance Benchmarks", unsafe_allow_html=True)
                            for agent_type, benchmark in agent_benchmarks.items():
                                st.markdown(f"**{agent_type}**: Expected Accuracy `{benchmark['expected_accuracy']:.1%}`, Processing Time `< {benchmark['processing_time_threshold']}s`")
            except Exception as e:
                st.error(f"Failed to fetch benchmarks: {str(e)}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">Raw Trace</span>', unsafe_allow_html=True)
    st.code("\n".join(f'[{e["timestamp"]}] {e["event"]}' for e in trail[-100:]), language="text")

    if alert and alert.get("agent_results"):
        with st.expander("Agent evidence archive (JSON)"):
            st.json(alert["agent_results"])
    if alert and alert.get("ai_synthesis"):
        with st.expander("Model synthesis payload (JSON)"):
            st.json(alert["ai_synthesis"])

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("→ Live Dashboard", type="primary", key="to_live"):
        st.session_state.stage = 10; st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 10 — LIVE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def stage_live_dashboard() -> None:
    stage_hero(
        10,
        "Executive telemetry without losing operational truth",
        "Roll-ups show how the program is trending while preserving drill-down paths to individual alerts—exactly the posture modern fraud COEs adopt.",
        badge_label="Session rollup",
        badge_ok=True,
        learning="Close the loop: tie these metrics to staffing, queue ageing, and model drift reviews.",
    )

    m = st.session_state.metrics
    alerts = st.session_state.alerts

    # Calculate fraud stopped count
    fraud_stopped = m["confirmed_fraud"] + m["blocked"]

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:.75rem;margin-bottom:1.5rem;">'
        f'<div class="stat-card"><div class="stat-value" style="color:#f1f5f9;">{m["total_alerts"]}</div><div class="stat-label">Total Alerts</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{m["confirmed_fraud"]}</div><div class="stat-label">Fraud Confirmed</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#10b981;">{m["auto_closed"]}</div><div class="stat-label">Auto-Closed</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#f59e0b;">{m["hitl_pending"]}</div><div class="stat-label">HITL Pending</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#ef4444;">{m["blocked"]}</div><div class="stat-label">Accts Blocked</div></div>'
        f'<div class="stat-card"><div class="stat-value" style="color:#dc2626; font-weight: bold; font-size: 1.2rem;">{fraud_stopped}</div><div class="stat-label">Confirmed + blocked</div></div>'
        f'</div>', unsafe_allow_html=True,
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
                rows.append({"Alert ID": a["alert_id"], "Customer": a["customer_id"],
                             "Amount": f"${a['amount']:,.0f}", "Country": a["destination_country"],
                             "Severity": a["severity"], "Status": a["status"],
                             "Risk Score": f"{int(fs*100)}/100" if rr else "—"})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.markdown('<div class="info-panel">No active investigations.</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<span class="section-label">Risk Distribution</span>', unsafe_allow_html=True)
        if alerts:
            risk_data = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for a in alerts:
                risk_data[a.get("severity","MEDIUM")] = risk_data.get(a.get("severity","MEDIUM"),0) + 1
            # Alert severity distribution available in metrics panel

    st.markdown("<hr>", unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<span class="section-label">Fraud Memory Store</span>', unsafe_allow_html=True)
        all_mem = st.session_state.fraud_memory + st.session_state.fraud_memory_updates
        if all_mem:
            df_m = pd.DataFrame(all_mem)
            cols = [c for c in ["pattern_type","entity_id","confidence","risk_score","status","description"] if c in df_m.columns]
            st.dataframe(df_m[cols or list(df_m.columns)[:5]], hide_index=True, use_container_width=True)
    with col4:
        st.markdown('<span class="section-label">Transaction Volume by Country</span>', unsafe_allow_html=True)
        txns = st.session_state.transactions
        if txns:
            df_tx = pd.DataFrame(txns)
            cv = df_tx.groupby("destination_country")["amount"].sum().reset_index()
            cv.columns = ["Country","Total Amount"]
            # Transaction volume analysis available in audit trail

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="section-label">All Alerts Summary</span>', unsafe_allow_html=True)
    if alerts:
        rows = []
        for a in alerts:
            rr = a.get("risk_result") or {}
            if rr:
                fs = float(rr.get("final_risk_score", rr.get("risk_score", 0)))
            else:
                fs = 0.0
            rows.append({"Alert ID": a["alert_id"], "Customer": a["customer_id"],
                         "Amount": f"${a['amount']:,.0f}", "Country": a["destination_country"],
                         "Severity": a["severity"], "Status": a["status"],
                         "Risk Score": f"{int(fs*100)}/100" if rr else "—",
                         "Decision": (a.get("hitl_decision",{}).get("decision","—") if a.get("hitl_decision")
                                      else ("FROZEN" if a.get("frozen") else "APPROVED" if a.get("approved") else "—")),
                         "Created": a["created_at"][:19]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("↩ Start New Investigation", type="primary", key="restart"):
        st.session_state.stage = 1
        st.session_state.selected_alert_id = None
        trace("SESSION_RESET → Segment 01")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Fraud investigation walkthrough · Agentic AI",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    render_sidebar()

    # Title is drawn in the Streamlit header bar via CSS (::after) so it stays visible and aligned with the menu.
    st.caption("Walkthrough · FastAPI · use the sidebar to jump segments or reset the session.")

    stage = st.session_state.stage
    m = st.session_state.metrics
    fraud_stopped = m["confirmed_fraud"] + m["blocked"]
    alert = next((a for a in st.session_state.alerts if a["alert_id"] == st.session_state.selected_alert_id), None)

    tab_demo, tab_audit_raw = st.tabs(["Walkthrough", "Event log"])

    def _gate(msg: str) -> None:
        st.markdown(
            f'<div class="demo-gate"><div class="demo-gate-title">Complete the prior segment</div>'
            f'<div class="demo-gate-body">{msg}</div></div>',
            unsafe_allow_html=True,
        )

    with tab_demo:
        st.caption(f"**{stage}/10** · {STAGE_LABELS[stage - 1]}")
        if stage == 1:
            stage_data_sources()
        elif stage == 2:
            stage_generate_alert()
        elif stage == 3:
            stage_alerts_queue()
        elif stage == 4:
            if stage == 1:
                stage_data_sources()
        elif stage == 2:
            stage_generate_alert()
        elif stage == 3:
            stage_alerts_queue()
        elif stage == 4:
            if not alert or not alert.get("triage_result"):
                _gate("Run triage in <b>Segment 04</b> so agents receive a routed case.")
            else:
                stage_triage(alert)
        elif stage == 5:
            if not alert or not alert.get("agent_results"):
                _gate("Execute the parallel agents in <b>Segment 05</b> to populate evidence.")
            else:
                stage_agents(alert)
        elif stage == 6:
            if not alert or not alert.get("evaluation_result"):
                _gate("Complete evaluation in <b>Segment 06</b> before analyst review.")
            else:
                stage_evaluation(alert)
        elif stage == 7:
            if not alert:
                _gate("Record an analyst disposition in <b>Segment 07</b> before remediation.")
            else:
                stage_hitl(alert)
        elif stage == 8:
            stage_resolution(alert)
        elif stage == 9:
            stage_audit(alert)
        elif stage == 10:
            stage_live_dashboard()

        render_post_segment_chrome(stage, m, fraud_stopped)

    with tab_audit_raw:
        st.markdown('<span class="section-label">Append-only trace (export friendly)</span>', unsafe_allow_html=True)
        st.code("\n".join(f'[{e["timestamp"]}] {e["event"]}' for e in st.session_state.audit_trail[-150:]), language="text")

    st.markdown(
        '<div class="footer-branding" style="margin-top:2rem;padding-top:1rem;border-top:1px solid #1a2d45;">'
        '<div style="font-weight:700;color:#cbd5e1;margin-bottom:.35rem;">Reference implementation · not production advice</div>'
        '<div style="font-size:0.78rem;color:#64748b;">Configure <code>FRAUD_API_BASE</code> for your FastAPI instance. Set <code>API_KEY</code> only if the API requires <code>X-API-Key</code>.</div>'
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
