"""
LLM client — Cerebras (primary, fast) + Gemini (deep reasoning fallback).

Strategy:
  - Cerebras (configured model) → fast triage scoring (low latency, cost-efficient)
  - Gemini Flash family        → synthesis / reasoning fallback (Google AI Studio)
  - Rule-based fallback        → if both APIs unavailable
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from typing import Any

import httpx
import google.generativeai as genai

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_model_json_response(raw: str | None) -> dict[str, Any] | None:
    """
    Parse a chat model reply into a JSON object.

    Handles fenced ```json blocks, leading/trailing prose, and a single top-level object.
    """
    if raw is None:
        return None
    text = re.sub(r"```(?:json)?\s*", "", str(raw)).strip().rstrip("`").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError as e:
        logger.warning("model_json_substring_parse_failed", error=str(e), prefix=text[start : start + 120])
        return None


# ── Cerebras ──────────────────────────────────────────────────────────────────
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_SYSTEM  = "You are an expert fraud analyst. Always respond with valid JSON only. No markdown, no explanation — pure JSON."


async def call_cerebras(prompt: str, max_tokens: int = 512) -> str:
    """Call Cerebras API and return raw text. Retries with backoff on HTTP 429."""
    if not settings.cerebras_key_usable():
        raise ValueError("CEREBRAS_API_KEY not configured")

    payload = {
        "model": settings.cerebras_model,
        "messages": [
            {"role": "system", "content": CEREBRAS_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {settings.cerebras_api_key}",
        "Content-Type": "application/json",
    }
    max_attempts = 4
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(max_attempts):
            resp = await client.post(CEREBRAS_API_URL, headers=headers, json=payload)
            if resp.status_code == 429 and attempt < max_attempts - 1:
                wait = (2**attempt) + random.uniform(0, 0.75)
                logger.warning(
                    "cerebras_rate_limited_retrying",
                    attempt=attempt + 1,
                    sleep_seconds=round(wait, 2),
                )
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


async def call_cerebras_json(prompt: str, max_tokens: int = 512) -> dict[str, Any]:
    """Call Cerebras and parse JSON. Returns {} on failure."""
    try:
        raw = await call_cerebras(prompt, max_tokens=max_tokens)
        parsed = parse_model_json_response(raw)
        return parsed if parsed is not None else {}
    except Exception as e:
        logger.error(f"Cerebras API call failed: {e}")
        return {}


# ── Gemini ────────────────────────────────────────────────────────────────────
_gemini_configured = False

# Ordered after ``settings.gemini_model`` when the configured id returns 404 (Google retires aliases).
_GEMINI_MODEL_FALLBACKS: tuple[str, ...] = (
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b",
)


def _gemini_model_not_found_message(exc: BaseException) -> bool:
    s = str(exc).lower()
    return "404" in s and ("not found" in s or "is not found" in s)


def _gemini_model_candidates() -> list[str]:
    primary = (settings.gemini_model or "").strip()
    out: list[str] = []
    for m in (primary, *_GEMINI_MODEL_FALLBACKS):
        if m and m not in out:
            out.append(m)
    return out


def _ensure_gemini() -> None:
    global _gemini_configured
    if not _gemini_configured:
        if not settings.gemini_key_usable():
            raise ValueError("GEMINI_API_KEY not configured")
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_configured = True


def _gemini_generate_sync(full_prompt: str, max_tokens: int) -> str:
    """Sync Gemini call; tries model ids until one works or a non-404 error occurs."""
    _ensure_gemini()
    last_err: BaseException | None = None
    for model_name in _gemini_model_candidates():
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=max_tokens,
                ),
            )
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            last_err = e
            if _gemini_model_not_found_message(e):
                logger.warning("gemini_model_unavailable_trying_next", model=model_name)
                continue
            raise
    assert last_err is not None
    raise last_err


async def call_gemini(prompt: str, max_tokens: int = 1024) -> str:
    """Call Gemini and return raw text (sync wrapped in thread)."""
    system = "You are an expert fraud analyst. Always respond with valid JSON only. No markdown, no explanation — pure JSON."
    full_prompt = f"{system}\n\n{prompt}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _gemini_generate_sync, full_prompt, max_tokens)


async def call_gemini_json(prompt: str, max_tokens: int = 1024) -> dict[str, Any]:
    """Call Gemini and parse JSON. Returns {} on failure."""
    try:
        raw = await call_gemini(prompt, max_tokens=max_tokens)
        parsed = parse_model_json_response(raw)
        return parsed if parsed is not None else {}
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return {}


# ── Unified interface ─────────────────────────────────────────────────────────

async def call_fast_json(prompt: str, max_tokens: int = 512) -> dict[str, Any]:
    """
    Fast call for triage/scoring — uses Cerebras when configured.
    Falls back to Gemini if Cerebras unavailable or rate-limited.
    """
    if settings.cerebras_key_usable():
        result = await call_cerebras_json(prompt, max_tokens=max_tokens)
        if result:
            return result
        logger.warning("Cerebras failed — falling back to Gemini")

    if settings.gemini_key_usable():
        return await call_gemini_json(prompt, max_tokens=max_tokens)

    return {}


async def call_reasoning_json(prompt: str, max_tokens: int = 1500) -> dict[str, Any]:
    """
    Deep reasoning call for investigation synthesis and HITL — prefers Gemini Flash.
    Falls back to Cerebras if Gemini unavailable.
    """
    if settings.gemini_key_usable():
        result = await call_gemini_json(prompt, max_tokens=max_tokens)
        if result:
            return result
        logger.warning("Gemini failed — falling back to Cerebras")

    if settings.cerebras_key_usable():
        return await call_cerebras_json(prompt, max_tokens=min(max_tokens, 1024))

    return {}
