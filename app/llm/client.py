"""
LLM client — Cerebras (primary, fast) + Gemini (deep reasoning fallback).

Strategy:
  - Cerebras llama3.1-70b  → fast triage scoring (low latency, cost-efficient)
  - Gemini 1.5 Flash       → AI synthesis and HITL reasoning (strong reasoning)
  - Rule-based fallback    → if both APIs unavailable
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import google.generativeai as genai

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Cerebras ──────────────────────────────────────────────────────────────────
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_SYSTEM  = "You are an expert fraud analyst. Always respond with valid JSON only. No markdown, no explanation — pure JSON."


async def call_cerebras(prompt: str, max_tokens: int = 512) -> str:
    """Call Cerebras API and return raw text."""
    if not settings.cerebras_api_key:
        raise ValueError("CEREBRAS_API_KEY not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            CEREBRAS_API_URL,
            headers={
                "Authorization": f"Bearer {settings.cerebras_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.cerebras_model,
                "messages": [
                    {"role": "system", "content": CEREBRAS_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def call_cerebras_json(prompt: str, max_tokens: int = 512) -> dict[str, Any]:
    """Call Cerebras and parse JSON. Returns {} on failure."""
    try:
        raw = await call_cerebras(prompt, max_tokens=max_tokens)
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Cerebras JSON parse error: {e}")
        return {}
    except Exception as e:
        logger.error(f"Cerebras API call failed: {e}")
        return {}


# ── Gemini ────────────────────────────────────────────────────────────────────
_gemini_configured = False


def _ensure_gemini() -> None:
    global _gemini_configured
    if not _gemini_configured:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_configured = True


async def call_gemini(prompt: str, max_tokens: int = 1024) -> str:
    """Call Gemini and return raw text (sync wrapped in thread)."""
    import asyncio
    _ensure_gemini()

    system = "You are an expert fraud analyst. Always respond with valid JSON only. No markdown, no explanation — pure JSON."
    full_prompt = f"{system}\n\n{prompt}"

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=max_tokens,
        ),
    )

    # Gemini SDK is sync — run in thread pool
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, model.generate_content, full_prompt)
    return response.text


async def call_gemini_json(prompt: str, max_tokens: int = 1024) -> dict[str, Any]:
    """Call Gemini and parse JSON. Returns {} on failure."""
    try:
        raw = await call_gemini(prompt, max_tokens=max_tokens)
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Gemini JSON parse error: {e}")
        return {}
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return {}


# ── Unified interface ─────────────────────────────────────────────────────────

async def call_fast_json(prompt: str, max_tokens: int = 512) -> dict[str, Any]:
    """
    Fast call for triage/scoring — uses Cerebras (llama3.1-70b).
    Falls back to Gemini Flash if Cerebras unavailable.
    """
    if settings.cerebras_api_key:
        result = await call_cerebras_json(prompt, max_tokens=max_tokens)
        if result:
            return result
        logger.warning("Cerebras failed — falling back to Gemini")

    if settings.gemini_api_key:
        return await call_gemini_json(prompt, max_tokens=max_tokens)

    return {}


async def call_reasoning_json(prompt: str, max_tokens: int = 1500) -> dict[str, Any]:
    """
    Deep reasoning call for investigation synthesis and HITL — uses Gemini 1.5 Flash.
    Falls back to Cerebras if Gemini unavailable.
    """
    if settings.gemini_api_key:
        result = await call_gemini_json(prompt, max_tokens=max_tokens)
        if result:
            return result
        logger.warning("Gemini failed — falling back to Cerebras")

    if settings.cerebras_api_key:
        return await call_cerebras_json(prompt, max_tokens=min(max_tokens, 1024))

    return {}
