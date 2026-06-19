"""
Layer 3: Cognitive Translation Engine
======================================
Converts the Layer 2 ML anomaly payload (JSON dict) into a concise,
human-readable engineering diagnostic string using the Groq API.

Isolation boundary: This module has zero knowledge of the frontend,
WebSocket handlers, or any UI rendering logic. It accepts a plain dict
and returns a plain str — nothing else.

Usage:
    from layer_3_telematics import generate_diagnostic_report

    report: str = generate_diagnostic_report(anomaly_payload)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from groq import Groq

logger = logging.getLogger("layer_3_telematics")

# ---------------------------------------------------------------------------
# Groq client — instantiated once at module load time.
# The API key is read exclusively from the environment; never hardcoded.
# ---------------------------------------------------------------------------
_GROQ_API_KEY: str | None = os.environ.get("GROQ_API_KEY")
_groq_client: Groq | None = None

if _GROQ_API_KEY:
    try:
        _groq_client = Groq(api_key=_GROQ_API_KEY)
        logger.info("Layer 3: Groq client initialised successfully.")
    except Exception as _init_err:
        logger.error(f"Layer 3: Failed to initialise Groq client — {_init_err}")
        _groq_client = None
else:
    logger.warning(
        "Layer 3: GROQ_API_KEY not found in environment. "
        "Hardcoded fallback will be used for all diagnostics."
    )

# ---------------------------------------------------------------------------
# Model configuration — fixed to enforce deterministic outputs.
# ---------------------------------------------------------------------------
_MODEL_ID = "llama-3.1-8b-instant"
_TEMPERATURE = 0.1          # Near-deterministic; avoids creative hallucination
_MAX_TOKENS = 120           # Two concise sentences never exceed this

# ---------------------------------------------------------------------------
# System prompt — strict persona and output contract.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are an embedded SDV (Software-Defined Vehicle) telematics processor. Your sole function is to convert raw anomaly telemetry into a precise, two-sentence engineering diagnostic.

OUTPUT CONTRACT — obey these rules without exception:
1. Output exactly two sentences. No more, no less.
2. Sentence 1: State the physical mismatch or anomalous sensor relationship in plain engineering language. Reference specific sensor names and numeric values from the payload where available.
3. Sentence 2: State the single most immediate recommended mechanical action the driver or technician must take.
4. Do NOT use Markdown, asterisks, bullet points, headers, or any formatting characters.
5. Do NOT use conversational filler such as "I see", "It appears", "Based on the data", or "Please note".
6. Do NOT repeat the root cause label verbatim as a sentence opener; describe the physical condition it represents instead."""


def generate_diagnostic_report(payload: dict[str, Any]) -> str:
    """
    Layer 3 Cognitive Translation: converts a Layer 2 anomaly payload dict
    into a human-readable two-sentence engineering diagnostic string.

    Args:
        payload: The anomaly dict produced by SafetyGateway.evaluate() when
                 ``is_ml_anomaly`` is True.  Expected keys include:
                   - ``root_cause``        (str)   — feature name of the dominant anomaly
                   - ``ml_anomaly_score``  (float) — IsolationForest score_samples value
                   - Any live sensor keys forwarded from the telemetry frame.

    Returns:
        A plain-text string containing exactly two sentences.
        If the Groq API is unavailable or raises any exception, a hardcoded
        deterministic fallback string is returned instead.
    """
    root_cause: str = str(payload.get("root_cause", "unknown_sensor"))
    ml_anomaly_score: float = float(payload.get("ml_anomaly_score", 0.0))

    # ── Hardcoded deterministic fallback ─────────────────────────────────────
    # Computed before the API call so it is always available without a
    # second pass through the payload on exception paths.
    z_score_approx: float = round(abs(ml_anomaly_score) * 10, 2)
    fallback_report: str = (
        f"Diagnostic Alert: {root_cause} detected at {z_score_approx} severity. "
        f"Physical inspection required."
    )

    # ── Guard: no client, go straight to fallback ────────────────────────────
    if _groq_client is None:
        logger.warning("Layer 3: Groq client unavailable — using fallback report.")
        return fallback_report

    # ── Build the user message from the payload ──────────────────────────────
    # Serialise the payload into a compact, readable key=value block so the
    # LLM receives structured data without JSON noise.
    payload_lines = "\n".join(
        f"  {k}: {v}" for k, v in payload.items()
    )
    user_message: str = (
        f"Anomaly telemetry payload:\n"
        f"{payload_lines}\n\n"
        f"Generate the two-sentence engineering diagnostic now."
    )

    # ── Groq API call ────────────────────────────────────────────────────────
    try:
        completion = _groq_client.chat.completions.create(
            model=_MODEL_ID,
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        )
        report: str = completion.choices[0].message.content.strip()
        logger.info(
            f"Layer 3: Diagnostic report generated for root_cause='{root_cause}'."
        )
        return report

    except Exception as api_err:
        # Catches network timeouts, auth errors, rate-limit exceptions, etc.
        logger.error(
            f"Layer 3: Groq API call failed ({type(api_err).__name__}: {api_err}). "
            f"Returning hardcoded fallback."
        )
        return fallback_report
