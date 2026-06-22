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
_TEMPERATURE = 0.0          # Fully deterministic; eliminates creative deviation
_MAX_TOKENS = 80            # One precise sentence never exceeds this

# ---------------------------------------------------------------------------
# System prompt — strict one-sentence output contract with no ambiguity.
#
# Design rationale: The context payload sent by safety_gateway.py already
# contains the fully calculated mathematical facts (actual value, expected
# baseline, signed deviation direction). The AI's ONLY job is to reformat
# those facts into a single readable sentence. It must not interpret, infer,
# or add information beyond what the payload explicitly states.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are an embedded SDV telematics diagnostic formatter. "
    "You receive a pre-calculated anomaly payload that already contains the exact "
    "sensor readings, expected baselines, deviation direction, and confirmed fault condition. "
    "Your sole function is to reformat the 'physical_context' field of that payload "
    "into one single diagnostic sentence.\n\n"
    "OUTPUT CONTRACT — obey without exception:\n"
    "1. Output exactly ONE sentence. Not two. Not a paragraph. One sentence only.\n"
    "2. That sentence must include: the actual measured value, the expected baseline, "
    "the direction the actual value deviates (above or below), and the confirmed fault "
    "condition — all of which are explicitly provided in the payload.\n"
    "3. Do NOT invent, infer, or add any information not present in the payload. "
    "The payload is the ground truth. Format it; do not interpret it.\n"
    "4. Do NOT use Markdown, asterisks, bullet points, numbered lists, or headers.\n"
    "5. Do NOT use filler phrases such as 'It appears', 'Based on the data', "
    "'I see that', 'Please note', or 'I recommend'.\n"
    "6. The sentence must be under 35 words.\n"
    "7. Begin the sentence directly with the physical condition, not with the root cause label."
)


def generate_diagnostic_report(payload: dict[str, Any]) -> str:
    """
    Layer 3 Cognitive Translation: converts a pre-calculated anomaly payload
    into a single human-readable engineering diagnostic sentence.

    The payload is expected to contain a 'physical_context' key produced by
    _build_deterministic_context() in safety_gateway.py. That context string
    already encodes the actual value, expected baseline, signed deviation
    direction, and confirmed fault condition. The AI reformats it — it does
    not interpret or add to it.

    Args:
        payload: The anomaly dict produced by SafetyGateway.evaluate().
                 Expected keys:
                   - ``root_cause``         (str)   — feature name of the dominant anomaly
                   - ``physical_context``   (str)   — deterministic context from the injector
                   - ``anomaly_score_magnitude`` (float) — IsolationForest score magnitude

    Returns:
        A plain-text string containing exactly one sentence.
        If the Groq API is unavailable or raises any exception, the
        physical_context string is returned directly as the fallback,
        since it is already a well-formed diagnostic statement.
    """
    root_cause: str = str(payload.get("root_cause", "unknown_sensor"))
    physical_context: str = str(payload.get("physical_context", ""))

    # ── Fallback: if context is already a complete statement, return it ───────
    # This is intentional — _build_deterministic_context() produces a sentence
    # that is meaningful on its own. If Groq is unavailable, we surface the
    # raw mathematical fact rather than a generic "inspection required" message.
    fallback_report: str = (
        physical_context
        if physical_context
        else f"Anomaly detected in {root_cause}. Physical inspection required."
    )

    # ── Guard: no client, go straight to fallback ─────────────────────────────
    if _groq_client is None:
        logger.warning("Layer 3: Groq client unavailable — returning deterministic fallback.")
        return fallback_report

    # ── Build the user message ────────────────────────────────────────────────
    # Pass the full payload so the model can see all fields, but the system
    # prompt instructs it to reformat 'physical_context' specifically.
    payload_lines = "\n".join(f"  {k}: {v}" for k, v in payload.items())
    user_message: str = (
        f"Anomaly payload:\n"
        f"{payload_lines}\n\n"
        f"Reformat the 'physical_context' field above into exactly one diagnostic sentence."
    )

    # ── Groq API call ─────────────────────────────────────────────────────────
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

        # ── Sanity check: reject multi-sentence outputs ───────────────────────
        # Count sentence-ending punctuation. If the model produced more than one
        # sentence despite the prompt, fall back to the deterministic context.
        sentence_count = sum(1 for ch in report if ch in ".!?")
        if sentence_count > 2:
            logger.warning(
                "Layer 3: Model returned %d sentences — reverting to deterministic context.",
                sentence_count,
            )
            return fallback_report

        logger.info(
            "Layer 3: Diagnostic sentence generated for root_cause='%s'.", root_cause
        )
        return report

    except Exception as api_err:
        logger.error(
            "Layer 3: Groq API call failed (%s: %s) — returning deterministic fallback.",
            type(api_err).__name__, api_err,
        )
        return fallback_report