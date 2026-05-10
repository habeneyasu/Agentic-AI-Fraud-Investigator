"""🛡️ AI FRAUD COMMAND CENTER - Enterprise-Grade War Room"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
import random
from typing import Dict, Any

# Enterprise-grade configuration
st.set_page_config(
    page_title="🛡️ AI FRAUD COMMAND CENTER",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional enterprise styling
st.markdown("""
<style>
    /* Base Enterprise Theme */
    body { 
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%); 
        color: #ffffff; 
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.4;
    }
    .stApp { 
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%); 
    }
    
    /* Enterprise SOC Header */
    .soc-header {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
        border: 2px solid #00ff88;
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 255, 136, 0.15);
    }
    
    .soc-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.1), transparent);
        animation: scan 4s infinite;
    }
    
    @keyframes scan {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .header-title {
        flex: 1;
    }
    
    .header-title h1 {
        margin: 0 0 0.5rem 0;
        font-size: 1.75rem;
        font-weight: 800;
        color: #00ff88;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .header-subtitle {
        margin: 0;
        font-size: 0.875rem;
        color: #999999;
        font-weight: 500;
    }
    
    .header-status {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        min-width: 250px;
    }
    
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    
    .status-dot {
        width: 12px;
        height: 12px;
        background: #00ff88;
        border-radius: 50%;
        animation: pulse 2s infinite;
        box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
    }
    
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.1); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    .live-ticker {
        background: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.75rem;
        color: #00ff88;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Enterprise KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 2rem 0;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        border-color: #444444;
    }
    
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00ff88, #00cc6a, #00ff88);
        animation: shimmer 3s infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    .kpi-icon {
        font-size: 2rem;
        margin-bottom: 0.75rem;
        display: block;
    }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: #00ff88;
        margin: 0.5rem 0;
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
    }
    
    .kpi-change {
        font-size: 0.875rem;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        background: rgba(0, 255, 136, 0.1);
        color: #00ff88;
    }
    
    .kpi-change.negative {
        background: rgba(255, 68, 68, 0.1);
        color: #ff4444;
    }
    
    .kpi-label {
        font-size: 0.75rem;
        color: #999999;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.5rem;
    }
    
    /* Cinematic Timeline */
    .timeline-container {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 2rem 0;
    }
    
    .timeline-header {
        font-size: 1.125rem;
        font-weight: 700;
        color: #00ff88;
        margin-bottom: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .timeline-steps {
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: relative;
        margin: 2rem 0;
    }
    
    .timeline-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        position: relative;
        z-index: 2;
    }
    
    .timeline-node {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .timeline-node.active {
        background: #00ff88;
        color: #000000;
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        animation: glow 2s infinite;
    }
    
    @keyframes glow {
        0% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.5); }
        50% { box-shadow: 0 0 30px rgba(0, 255, 136, 0.8); }
        100% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.5); }
    }
    
    .timeline-node.completed {
        background: #00ff88;
        color: #000000;
    }
    
    .timeline-node.pending {
        background: #333333;
        color: #666666;
    }
    
    .timeline-label {
        font-size: 0.75rem;
        color: #999999;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        text-align: center;
        max-width: 100px;
    }
    
    .timeline-line {
        position: absolute;
        top: 20px;
        left: 40px;
        right: 40px;
        height: 2px;
        background: linear-gradient(90deg, #00ff88 0%, #333333 100%);
        z-index: 1;
    }
    
    /* Dangerous Alert Cards */
    .alert-dangerous {
        background: linear-gradient(135deg, #2a0a0a 0%, #4a1a1a 100%);
        border: 1px solid #ff0000;
        border-left: 6px solid #ff0000;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        position: relative;
        transition: all 0.3s ease;
        box-shadow: 0 8px 24px rgba(255, 0, 0, 0.3);
    }
    
    .alert-dangerous:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(255, 0, 0, 0.4);
    }
    
    .alert-dangerous::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #ff0000, #ff4444, #ff0000);
        animation: alert-pulse 1s infinite;
    }
    
    @keyframes alert-pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    
    .alert-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .alert-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #ff4444;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .alert-badge {
        background: #ff0000;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        animation: alert-pulse 1s infinite;
    }
    
    .alert-details {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .alert-detail {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 1rem;
    }
    
    .alert-detail-label {
        font-size: 0.75rem;
        color: #999999;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }
    
    .alert-detail-value {
        font-size: 1.125rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    .alert-signals {
        background: rgba(255, 68, 68, 0.05);
        border: 1px solid rgba(255, 68, 68, 0.2);
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .signal-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0.5rem 0;
        padding: 0.75rem;
        background: rgba(255, 68, 68, 0.1);
        border-radius: 6px;
        border-left: 3px solid #ff4444;
    }
    
    .signal-icon {
        color: #ff4444;
        font-size: 1.25rem;
    }
    
    .signal-text {
        color: #ffffff;
        font-weight: 600;
        font-size: 0.875rem;
    }
    
    /* Live AI Agents */
    .agent-container {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        position: relative;
    }
    
    .agent-terminal {
        background: #000000;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.875rem;
        color: #00ff88;
        min-height: 200px;
        overflow-y: auto;
        position: relative;
    }
    
    .agent-log {
        margin: 0.5rem 0;
        line-height: 1.4;
    }
    
    .agent-log.timestamp {
        color: #666666;
        font-size: 0.75rem;
    }
    
    .agent-log.message {
        color: #00ff88;
        margin-left: 0.5rem;
    }
    
    .agent-status {
        position: absolute;
        top: 1rem;
        right: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: #00ff88;
    }
    
    /* Executive AI Briefing */
    .executive-briefing {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
        position: relative;
    }
    
    .briefing-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #333333;
    }
    
    .briefing-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #00ff88;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .briefing-confidence {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        color: #00ff88;
    }
    
    .briefing-content {
        color: #ffffff;
        line-height: 1.6;
        font-size: 0.875rem;
    }
    
    .briefing-section {
        margin: 1.5rem 0;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 8px;
        border-left: 3px solid #00ff88;
    }
    
    .briefing-section-title {
        font-weight: 700;
        color: #00ff88;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.875rem;
    }
    
    /* High-Stakes Human Review */
    .human-review-overlay {
        background: linear-gradient(135deg, rgba(255, 170, 0, 0.1) 0%, rgba(255, 136, 0, 0.1) 100%);
        border: 2px solid #ffaa00;
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
        position: relative;
        box-shadow: 0 8px 32px rgba(255, 170, 0, 0.3);
    }
    
    .review-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ffaa00;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .review-subtitle {
        font-size: 1.125rem;
        color: #ffffff;
        margin-bottom: 2rem;
    }
    
    .massive-button {
        background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%);
        color: white;
        border: none;
        padding: 1.5rem 3rem;
        border-radius: 12px;
        font-weight: 800;
        font-size: 1.125rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 8px 24px rgba(255, 0, 0, 0.4);
        margin: 1rem;
    }
    
    .massive-button:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(255, 0, 0, 0.6);
    }
    
    .massive-button.safe {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
        color: #000000;
        box-shadow: 0 8px 24px rgba(0, 255, 136, 0.4);
    }
    
    .massive-button.safe:hover {
        box-shadow: 0 12px 32px rgba(0, 255, 136, 0.6);
    }
    
    /* Audit Timeline */
    .audit-timeline {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .audit-item {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        margin: 0.75rem 0;
        padding: 0.75rem;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 8px;
        border-left: 3px solid #00ff88;
    }
    
    .audit-time {
        color: #666666;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.75rem;
        min-width: 80px;
    }
    
    .audit-message {
        color: #ffffff;
        font-size: 0.875rem;
        flex: 1;
    }
    
    /* Streamlit Overrides */
    .stButton > button {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%) !important;
        color: #000000 !important;
        border: none !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 0.875rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 16px rgba(0, 255, 136, 0.3) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #00cc6a 0%, #00ff88 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0, 255, 136, 0.4) !important;
    }
    
    .stMetric {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%) !important;
        border: 1px solid #333333 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
    }
    
    .stStatus > div {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%) !important;
        border: 1px solid #333333 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    
    .stTabs [data-baseweb="tabList"] {
        background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #999999;
        border: none;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: rgba(0, 255, 136, 0.1);
        color: #00ff88;
        border: 1px solid #00ff88;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'selected_alert' not in st.session_state:
    st.session_state.selected_alert = None
if 'investigation_log' not in st.session_state:
    st.session_state.investigation_log = []
if 'agent_logs' not in st.session_state:
    st.session_state.agent_logs = []

def generate_fraud_alert():
    """Generate realistic fraud alert."""
    return {
        "id": f"ALERT_{datetime.now().strftime('%H%M%S')}",
        "type": "ACCOUNT_TAKEOVER",
        "title": "HIGH-RISK CROSS-BORDER TRANSFER",
        "description": "Impossible travel + new device + OFAC partial match",
        "amount": 15000,
        "risk_score": 0.92,
        "status": "new",
        "customer_id": f"CUST_{random.randint(1000, 9999)}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "flags": ["New Device", "Impossible Travel", "OFAC Partial Match"],
        "country": "IR",
        "device_id": f"DEV_UNKNOWN_{random.randint(100, 999)}",
        "previous_transactions": [12, 18, 22, 17, 15, 21, 19, 16, 20, 15000]
    }

def render_soc_header():
    """Render REAL SOC header with live status."""
    st.markdown('<div class="soc-header">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="header-content">
        <div class="header-title">
            <h1>🛡️ AI FRAUD COMMAND CENTER</h1>
            <p class="header-subtitle">Real-Time Autonomous Investigation Platform</p>
        </div>
        <div class="header-status">
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span style="color: #00ff88; font-weight: 700;">SYSTEM ONLINE</span>
            </div>
            <div style="color: #ffffff; font-size: 0.875rem; margin: 0.5rem 0;">
                <div>Latency: <span style="color: #00ff88;">182ms</span></div>
                <div>Agents Active: <span style="color: #00ff88;">3</span></div>
                <div>Threat Level: <span style="color: #ffaa00;">ELEVATED</span></div>
            </div>
            <div class="live-ticker">
                <span style="color: #00ff88; font-weight: 700;">[ LIVE ]</span>
                <span>Monitoring 12,441 transactions/min</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_executive_kpis():
    """Render executive KPI cards with trends."""
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    
    # KPI data
    kpis = [
        {
            "icon": "🚨",
            "label": "Alerts Today",
            "value": "124",
            "change": "+18%",
            "positive": True
        },
        {
            "icon": "🔒",
            "label": "Fraud Prevented",
            "value": "$1.8M",
            "change": "+24%",
            "positive": True
        },
        {
            "icon": "⚡",
            "label": "Avg Response Time",
            "value": "1.2s",
            "change": "-0.3s",
            "positive": True
        },
        {
            "icon": "🧠",
            "label": "AI Confidence",
            "value": "94%",
            "change": "+2%",
            "positive": True
        }
    ]
    
    for kpi in kpis:
        change_class = "" if kpi["positive"] else "negative"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">{kpi['icon']}</div>
            <div class="kpi-value">
                {kpi['value']}
                <span class="kpi-change {change_class}">{kpi['change']}</span>
            </div>
            <div class="kpi-label">{kpi['label']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_cinematic_timeline():
    """Render cinematic investigation timeline."""
    st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="timeline-header">Investigation Timeline</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="timeline-steps">', unsafe_allow_html=True)
    
    steps = [
        {"name": "Alert", "num": 1},
        {"name": "Triage", "num": 2},
        {"name": "Agents", "num": 3},
        {"name": "AI Reasoning", "num": 4},
        {"name": "Human Review", "num": 5},
        {"name": "Resolution", "num": 6}
    ]
    
    for i, step in enumerate(steps):
        is_completed = st.session_state.current_step > step["num"]
        is_active = st.session_state.current_step == step["num"]
        is_pending = st.session_state.current_step < step["num"]
        
        node_class = "active" if is_active else "completed" if is_completed else "pending"
        
        st.markdown(f"""
        <div class="timeline-step">
            <div class="timeline-node {node_class}">{step['num']}</div>
            <div class="timeline-label">{step['name']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if i < len(steps) - 1:
            progress_width = 100 if is_completed else (50 if is_active else 0)
            st.markdown(f"""
            <div class="timeline-line" style="background: linear-gradient(90deg, #00ff88 0%, #00ff88 {progress_width}%, #333333 {progress_width}%, #333333 100%);"></div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def step_1_war_room():
    """Step 1: Live Pulse with streaming event feed."""
    st.markdown("## 🌍 LIVE THREAT MONITORING")
    
    # Streaming event feed
    event_container = st.empty()
    
    # Simulate streaming events
    events = [
        "[12:17:21] Monitoring incoming payment rails...",
        "[12:17:22] Device fingerprint analysis active...",
        "[12:17:24] Velocity engine calibrated...",
        "[12:17:26] Geolocation verification running...",
        "[12:17:28] OFAC screening initialized...",
        "[12:17:30] Behavioral baseline established..."
    ]
    
    for event in events:
        event_container.markdown(f"""
        <div style="background: #1a1a1a; border: 1px solid #333333; border-radius: 8px; padding: 0.75rem; margin: 0.5rem 0; font-family: 'SF Mono', monospace; font-size: 0.875rem; color: #00ff88;">
            {event}
        </div>
        """, unsafe_allow_html=True)
        time.sleep(0.5)
    
    # Alert detection
    if st.button("🚨 TRIGGER HIGH-RISK ALERT", type="primary", use_container_width=True):
        # Flash red border and pulse
        new_alert = generate_fraud_alert()
        st.session_state.alerts.append(new_alert)
        st.session_state.selected_alert = new_alert
        
        st.session_state.investigation_log.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": f"High-risk alert {new_alert['id']} detected"
        })
        
        # Show dramatic alert
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%); border: 2px solid #ff0000; border-radius: 12px; padding: 2rem; margin: 2rem 0; text-align: center; animation: alert-pulse 1s infinite;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🚨</div>
            <h2 style="color: #ffffff; margin: 0 0 1rem 0; font-weight: 800;">NEW HIGH-RISK TRANSACTION DETECTED</h2>
            <div style="color: #ffaaaa; font-size: 1.125rem;">
                Alert ID: {new_alert['id']} | Risk Score: {new_alert['risk_score']:.0f}/100
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.toast(f"🚨 CRITICAL ALERT: {new_alert['id']}", icon="🚨")
        time.sleep(2)
        st.session_state.current_step = 2
        st.rerun()
    
    # Show current alerts
    if st.session_state.alerts:
        st.markdown("### 🚨 ACTIVE ALERTS")
        for alert in st.session_state.alerts:
            st.markdown(f"""
            <div class="alert-dangerous">
                <div class="alert-header">
                    <h3 class="alert-title">{alert['title']}</h3>
                    <span class="alert-badge">ACTIVE</span>
                </div>
                <div class="alert-details">
                    <div class="alert-detail">
                        <div class="alert-detail-label">Customer</div>
                        <div class="alert-detail-value">{alert['customer_id']}</div>
                    </div>
                    <div class="alert-detail">
                        <div class="alert-detail-label">Amount</div>
                        <div class="alert-detail-value" style="color: #ff4444;">${alert['amount']:,}</div>
                    </div>
                    <div class="alert-detail">
                        <div class="alert-detail-label">Country</div>
                        <div class="alert-detail-value">{alert['country']}</div>
                    </div>
                    <div class="alert-detail">
                        <div class="alert-detail-label">Risk</div>
                        <div class="alert-detail-value" style="color: #ffaa00;">{alert['risk_score']:.0f}/100</div>
                    </div>
                </div>
                <div class="alert-signals">
                    <div class="signal-item">
                        <div class="signal-icon">⚠️</div>
                        <div class="signal-text">New Device</div>
                    </div>
                    <div class="signal-item">
                        <div class="signal-icon">⚠️</div>
                        <div class="signal-text">Impossible Travel</div>
                    </div>
                    <div class="signal-item">
                        <div class="signal-icon">⚠️</div>
                        <div class="signal-text">OFAC Partial Match</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 1.5rem;">
                    <button class="massive-button" onclick="investigate_alert('{alert['id']}')">
                        🔍 LAUNCH INVESTIGATION
                    </button>
                </div>
            </div>
            """, unsafe_allow_html=True)

def step_2_triage_war_room():
    """Step 2: Triage with transaction history."""
    st.markdown("## 🚪 TRIAGE & TRANSACTION ANALYSIS")
    
    if not st.session_state.selected_alert:
        st.warning("⚠️ No alert selected for triage")
        return
    
    alert = st.session_state.selected_alert
    
    # Transaction history with spike
    st.markdown("### 📊 TRANSACTION HISTORY")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1a1a1a 0%, #262626 100%); border: 1px solid #333333; border-radius: 12px; padding: 2rem; margin: 1rem 0;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 0.5rem; margin-bottom: 1rem;">
            {"".join([f'<div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.02); border-radius: 6px; color: #00ff88; font-weight: 600;">${amt}</div>' for amt in alert['previous_transactions'][:-1]])}
            <div style="text-align: center; padding: 0.5rem; background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%); border-radius: 6px; color: #ffffff; font-weight: 800; animation: alert-pulse 1s infinite;">${alert['amount']:,}</div>
        </div>
        <div style="text-align: center; color: #ff4444; font-size: 1.125rem; font-weight: 700; margin-top: 1rem;">
            🚨 {((alert['amount'] - 20) / 20) * 100:.0f}% INCREASE FROM NORMAL
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Triage decision
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("❌ DISMISS AS FALSE POSITIVE", type="secondary", use_container_width=True):
            st.session_state.investigation_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": f"Alert {alert['id']} dismissed as false positive"
            })
            st.success("✅ Alert dismissed - Case closed")
            st.session_state.current_step = 1
            st.session_state.selected_alert = None
            st.rerun()
    
    with col2:
        if st.button("🚀 ESCALATE TO AI INVESTIGATION", type="primary", use_container_width=True):
            st.session_state.investigation_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": f"Alert {alert['id']} escalated to AI investigation"
            })
            st.success("🚀 Escalated to AI investigation")
            time.sleep(1)
            st.session_state.current_step = 3
            st.rerun()

def step_3_agents_war_room():
    """Step 3: Live AI agents with orchestration."""
    st.markdown("## 🤖 PARALLEL AI INVESTIGATION")
    
    if not st.session_state.selected_alert:
        st.warning("⚠️ No alert selected for investigation")
        return
    
    # Live agent orchestration
    st.markdown('<div class="agent-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="agent-status">🔄 AGENTS ORCHESTRATING</div>', unsafe_allow_html=True)
    
    agent_terminal = st.empty()
    
    # Simulate agent logs
    agent_logs = [
        "[Agent:Transaction] Velocity threshold exceeded by 900%",
        "[Agent:KYC] New device fingerprint detected",
        "[Agent:Sanctions] Partial OFAC entity correlation found",
        "[Scoring] Composite risk elevated to 0.92",
        "[Orchestrator] All agents complete - Synthesizing findings..."
    ]
    
    agent_terminal.markdown('<div class="agent-terminal">', unsafe_allow_html=True)
    
    for log in agent_logs:
        agent_terminal.markdown(f"""
        <div class="agent-log">
            <span class="agent-log.timestamp">{datetime.now().strftime('%H:%M:%S')}</span>
            <span class="agent-log.message">{log}</span>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
    
    agent_terminal.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Agent completion cards
    if st.button("🧠 VIEW AI SYNTHESIS", type="primary", use_container_width=True):
        st.session_state.current_step = 4
        st.rerun()

def step_4_executive_briefing():
    """Step 4: Premium AI reasoning with executive briefing."""
    st.markdown("## 🧠 AI EXECUTIVE BRIEFING")
    
    if not st.session_state.selected_alert:
        st.warning("⚠️ No alert selected for briefing")
        return
    
    alert = st.session_state.selected_alert
    
    # Executive briefing
    st.markdown('<div class="executive-briefing">', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="briefing-header">
        <div class="briefing-title">AI Risk Assessment</div>
        <div class="briefing-confidence">Confidence: 94%</div>
    </div>
    
    <div class="briefing-content">
        <p>The customer initiated a high-value transaction from an unrecognized device originating from a sanctioned region shortly after an anomalous login event.</p>
        
        <div class="briefing-section">
            <div class="briefing-section-title">Risk Amplification Factors</div>
            <ul style="color: #ffffff; line-height: 1.6;">
                <li>Impossible travel detected (San Francisco → Tehran in 2 hours)</li>
                <li>Device fingerprint mismatch (registered iPhone vs unknown Android)</li>
                <li>OFAC partial entity match on beneficiary</li>
                <li>Transaction velocity 900% above baseline</li>
            </ul>
        </div>
        
        <div class="briefing-section">
            <div class="briefing-section-title">Recommended Action</div>
            <p style="color: #ff4444; font-weight: 700;">Immediate account freeze pending analyst review.</p>
        </div>
        
        <div class="briefing-section">
            <div class="briefing-section-title">Risk Breakdown</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <strong>Transaction Anomaly:</strong> <span style="color: #ff4444;">0.45</span>
                </div>
                <div>
                    <strong>KYC Deviation:</strong> <span style="color: #ff4444;">0.35</span>
                </div>
                <div>
                    <strong>Sanctions Risk:</strong> <span style="color: #ff4444;">0.20</span>
                </div>
                <div>
                    <strong>Composite Score:</strong> <span style="color: #ff0000; font-size: 1.25rem; font-weight: 800;">{alert['risk_score']:.2f}</span>
                </div>
            </div>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("👤 ESCALATE TO HUMAN REVIEW", type="primary", use_container_width=True):
        st.session_state.current_step = 5
        st.rerun()

def step_5_human_review():
    """Step 5: High-stakes human review."""
    st.markdown("## 👤 HUMAN-IN-THE-LOOP REVIEW")
    
    if not st.session_state.selected_alert:
        st.warning("⚠️ No alert selected for review")
        return
    
    alert = st.session_state.selected_alert
    
    # High-stakes overlay
    st.markdown('<div class="human-review-overlay">', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="review-title">⚠️ HUMAN APPROVAL REQUIRED</div>
    <div class="review-subtitle">Risk Score: {alert['risk_score']:.0f}/100 (CRITICAL)</div>
    
    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 1.5rem; margin: 2rem 0;">
        <h4 style="color: #ffffff; margin: 0 0 1rem 0;">Final Review Parameters</h4>
        <div style="color: #999999; font-size: 0.875rem; line-height: 1.6;">
            <strong>Analyst:</strong> John Smith (Level 3)<br>
            <strong>Clearance:</strong> Fraud Operations<br>
            <strong>Escalation Reason:</strong> High-risk cross-border transfer from sanctioned region<br>
            <strong>Time to Decision:</strong> 3 minutes 42 seconds
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Massive action buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown('<button class="massive-button">🔒 FREEZE ACCOUNT</button>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<button class="massive-button safe">✅ APPROVE TRANSACTION</button>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<button class="massive-button">🚨 ESCALATE CASE</button>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Decision buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔒 CONFIRM FREEZE", type="primary", use_container_width=True):
            st.session_state.investigation_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": f"Account {alert['customer_id']} frozen by human analyst"
            })
            st.session_state.current_step = 6
            st.rerun()
    
    with col2:
        if st.button("✅ APPROVE TRANSACTION", type="secondary", use_container_width=True):
            st.session_state.investigation_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": f"Transaction {alert['id']} approved by human analyst"
            })
            st.session_state.current_step = 6
            st.rerun()

def step_6_resolution():
    """Step 6: Emotional payoff with animated success."""
    st.markdown("## ✅ RESOLUTION & FRAUD MEMORY")
    
    if not st.session_state.selected_alert:
        st.warning("⚠️ No alert selected for resolution")
        return
    
    alert = st.session_state.selected_alert
    
    # Animated success
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 255, 136, 0.05) 100%); border: 2px solid #00ff88; border-radius: 16px; padding: 3rem; margin: 2rem 0; text-align: center; animation: fadeIn 0.5s ease;">
        <div style="font-size: 4rem; margin-bottom: 1rem; animation: scaleIn 0.5s ease;">✅</div>
        <h2 style="color: #00ff88; margin: 0 0 1rem 0; font-weight: 800;">ACCOUNT FROZEN</h2>
        <div style="color: #ffffff; font-size: 1.25rem; margin-bottom: 2rem;">
            Account {alert['customer_id']} has been successfully frozen<br>
            SMS notification sent • Card suspended • Case closed
        </div>
        
        <div style="background: #1a1a1a; border: 1px solid #333333; border-radius: 12px; padding: 2rem; margin: 2rem 0; text-align: left;">
            <h3 style="color: #00ff88; margin: 0 0 1.5rem 0;">🧠 FRAUD MEMORY UPDATED</h3>
            <div style="color: #ffffff; font-family: 'SF Mono', monospace; font-size: 0.875rem; line-height: 1.6;">
                <strong>Device Blacklisted:</strong> <span style="color: #ff4444;">{alert['device_id']}</span><br>
                <small style="color: #666666;">Permanently blacklisted due to account takeover</small><br><br>
                
                <strong>Location Flag:</strong> <span style="color: #ff4444;">{alert['country']}</span><br>
                <small style="color: #666666;">Marked as high-risk geographic area</small><br><br>
                
                <strong>Pattern Learned:</strong> <span style="color: #ff4444;">Impossible Travel + Account Takeover</span><br>
                <small style="color: #666666;">Added to fraud detection model for future prevention</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Audit timeline
    st.markdown("### 🔍 PERSISTENT AUDIT TIMELINE")
    
    audit_events = [
        {"time": "12:17:21", "message": "Alert received - High-risk transaction detected"},
        {"time": "12:17:45", "message": "Triage complete - Risk score 92/100"},
        {"time": "12:18:12", "message": "Transaction agent complete - 900% velocity anomaly"},
        {"time": "12:18:34", "message": "KYC agent complete - New device fingerprint"},
        {"time": "12:18:56", "message": "Sanctions agent complete - OFAC partial match"},
        {"time": "12:19:23", "message": "AI synthesis complete - Risk score 0.92"},
        {"time": "12:19:45", "message": "Human analyst freeze approved"},
        {"time": "12:20:15", "message": "Account frozen - SMS notification sent"},
        {"time": "12:20:30", "message": "Fraud memory updated - Device blacklisted"}
    ]
    
    st.markdown('<div class="audit-timeline">', unsafe_allow_html=True)
    
    for event in audit_events:
        st.markdown(f"""
        <div class="audit-item">
            <div class="audit-time">{event['time']}</div>
            <div class="audit-message">{event['message']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Reset button
    if st.button("🔄 INITIATE NEW INVESTIGATION", type="primary", use_container_width=True):
        st.session_state.current_step = 1
        st.session_state.selected_alert = None
        st.session_state.alerts = []
        st.session_state.investigation_log = []
        st.success("🔄 Ready for new investigation")
        st.rerun()

def main():
    """Main enterprise-grade application."""
    
    # SOC Header
    render_soc_header()
    
    # Executive KPIs
    render_executive_kpis()
    
    # Cinematic Timeline
    render_cinematic_timeline()
    
    # Render current step
    if st.session_state.current_step == 1:
        step_1_war_room()
    elif st.session_state.current_step == 2:
        step_2_triage_war_room()
    elif st.session_state.current_step == 3:
        step_3_agents_war_room()
    elif st.session_state.current_step == 4:
        step_4_executive_briefing()
    elif st.session_state.current_step == 5:
        step_5_human_review()
    elif st.session_state.current_step == 6:
        step_6_resolution()

if __name__ == "__main__":
    main()
