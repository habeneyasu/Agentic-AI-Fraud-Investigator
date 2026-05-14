"""Shared dashboard client config (Streamlit walkthrough + investigator console)."""

from __future__ import annotations

import os

API_BASE = os.getenv("FRAUD_API_BASE", "http://127.0.0.1:8000")


def _api_headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    key = (os.getenv("API_KEY") or "").strip()
    if key:
        h["X-API-Key"] = key
    return h


def analyst_headers() -> dict[str, str]:
    h = _api_headers()
    h["X-User-Role"] = "Analyst"
    return h
