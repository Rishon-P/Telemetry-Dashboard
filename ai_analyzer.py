"""
AI-Powered Vehicle Diagnostics — Gemini Flash Integration
==========================================================
Provides intelligent, natural-language vehicle health analysis
using Google Gemini Flash API as a layer on top of the existing
rule-based VehicleHealthAnalyzer.

Architecture:
• The rule engine (VehicleHealthAnalyzer) runs every 1 second
  for instant, deterministic safety alerts.
• This AI layer runs every ~10 seconds, analyzing the accumulated
  telemetry context to produce:
  - Natural-language diagnosis
  - Root cause analysis
  - Predictive warnings
  - Confidence-scored service recommendations
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger("telemetry.ai")

# ---------------------------------------------------------------------------
# Pydantic schema for structured AI output
# ---------------------------------------------------------------------------

class AIVehicleDiagnosis(BaseModel):
    """Structured output schema that Gemini must follow."""

    severity: Literal["SAFE", "MONITOR", "WARNING", "CRITICAL", "EMERGENCY"] = Field(
        description="Overall severity level based on all sensor data"
    )
    diagnosis: str = Field(
        description="Detailed natural-language diagnosis explaining the current vehicle condition in 2-3 sentences"
    )
    root_cause: str = Field(
        description="Most likely root cause if any issues are detected, or 'No issues detected' if healthy"
    )
    prediction: str = Field(
        description="What will happen in the next 5-15 minutes if current trends continue"
    )
    action: str = Field(
        description="Specific recommended action for the driver right now"
    )
    confidence: float = Field(
        description="AI confidence score from 0.0 to 1.0 in this diagnosis"
    )
    affected_systems: list[str] = Field(
        description="List of vehicle systems affected, e.g. ['engine', 'tires', 'battery']"
    )


# ---------------------------------------------------------------------------
# AI Analyzer class
# ---------------------------------------------------------------------------

class GeminiVehicleAnalyzer:
    """
    Wraps the Google Gemini Flash API for vehicle telemetry analysis.

    • Runs asynchronously alongside the existing rule engine.
    • Uses structured outputs (JSON schema) for reliable parsing.
    • Caches results and rate-limits API calls to stay within free tier.
    • Falls back gracefully if API key is missing or calls fail.
    """

    # System prompt — gives Gemini deep automotive expertise
    SYSTEM_PROMPT = """\
You are an expert automotive diagnostic AI with deep knowledge of:
- Engine thermal dynamics (SAE J1349 standards)
- Tire physics and pressure-speed interactions (DOT TPMS)
- OBD-II diagnostic standards and fault correlation
- Battery and electrical system diagnostics
- Oil pressure and lubrication system analysis
- Predictive maintenance and failure forecasting

You receive real-time vehicle telemetry data including sensor readings,
trend analysis, and rule-engine alerts. Your job is to:

1. DIAGNOSE: Provide a clear, professional explanation of the vehicle's
   current condition that a driver can understand.
2. ROOT CAUSE: Identify the most likely root cause of any anomalies by
   correlating multiple sensor readings together.
3. PREDICT: Based on current trends (rate of change, stability), predict
   what will happen in the next 5-15 minutes.
4. RECOMMEND: Give specific, actionable advice to the driver.

CRITICAL RULES:
- Never hallucinate sensor values — only reference data provided.
- If all readings are in normal ranges, say so clearly and confidently.
- Prioritize SAFETY — always err on the side of caution.
- Consider cross-sensor correlations (e.g., high speed + low tire pressure,
  high RPM + rising temperature, battery voltage drop + high electrical load).
- Be concise but thorough — drivers need quick, clear answers.
"""

    # ---- Free-tier protection constants ----
    DAILY_CALL_CAP = 1000            # Max API calls per calendar day
    DEFAULT_MIN_INTERVAL = 30        # Seconds between automatic AI calls
    FORCE_COOLDOWN = 60              # Min seconds between force_ai_analysis calls
    MAX_BACKOFF = 300                # Max backoff on consecutive errors (5 min)

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self.enabled = False
        self.last_analysis_time = 0
        self.min_interval = self.DEFAULT_MIN_INTERVAL
        self.cached_diagnosis: dict[str, Any] | None = None
        self.call_count = 0
        self.error_count = 0
        self._lock = asyncio.Lock()

        # ---- Free-tier quota tracking ----
        self._today: str = date.today().isoformat()
        self._daily_calls: int = 0
        self._quota_exhausted: bool = False

        # ---- Exponential backoff state ----
        self._consecutive_errors: int = 0
        self._backoff_until: float = 0  # timestamp until which calls are blocked

        # ---- Force-analysis cooldown ----
        self._last_force_time: float = 0

        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Gemini client if API key is available."""
        if not self.api_key or self.api_key == "your_api_key_here":
            logger.warning(
                "⚠️  GEMINI_API_KEY not set. AI analysis disabled. "
                "Get a free key at https://aistudio.google.com"
            )
            self.enabled = False
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.enabled = True
            logger.info("✅ Gemini AI analyzer initialized successfully")
        except ImportError:
            logger.error(
                "❌ google-genai package not installed. "
                "Run: pip install google-genai"
            )
            self.enabled = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            self.enabled = False

    def _build_prompt(
        self,
        telemetry: dict[str, float],
        rule_analysis: dict[str, Any],
        trend_history: dict[str, list[float]] | None = None,
    ) -> str:
        """Build a detailed prompt from current telemetry and rule engine output."""

        # Extract key info from rule analysis
        status = rule_analysis.get("status", {})
        trends = rule_analysis.get("trends", {})
        alerts = rule_analysis.get("alerts", [])
        health_score = rule_analysis.get("health_score", {})
        contradictions = health_score.get("contradictions", [])

        prompt = f"""## LIVE VEHICLE TELEMETRY DATA

### Current Sensor Readings:
- Speed: {telemetry.get('speed_kmh', 0):.1f} km/h
- Engine Temperature: {telemetry.get('engine_temp_c', 0):.1f} °C
- Tire Pressure (avg): {telemetry.get('tire_pressure_psi', 0):.1f} PSI
- Engine RPM: {telemetry.get('engine_rpm', 0):.0f}
- Oil Pressure: {telemetry.get('oil_pressure_psi', 0):.1f} PSI
- Battery Voltage: {telemetry.get('battery_voltage_v', 0):.2f} V
- Tire FL: {telemetry.get('tire_pressure_fl_psi', 0):.1f} PSI
- Tire FR: {telemetry.get('tire_pressure_fr_psi', 0):.1f} PSI
- Tire RL: {telemetry.get('tire_pressure_rl_psi', 0):.1f} PSI
- Tire RR: {telemetry.get('tire_pressure_rr_psi', 0):.1f} PSI

### Rule Engine Status:
- Speed: {status.get('speed', 'N/A')}
- Temperature: {status.get('temp', 'N/A')}
- Tire Pressure: {status.get('psi', 'N/A')}
- RPM: {status.get('rpm', 'N/A')}
- Oil Pressure: {status.get('oil', 'N/A')}
- Battery: {status.get('battery', 'N/A')}

### Trend Analysis (60-second window):
- Speed trend: {trends.get('speed', {}).get('direction', 'N/A')} (rate: {trends.get('speed', {}).get('rate', 0)}, stability: {trends.get('speed', {}).get('stability', 'N/A')})
- Temp trend: {trends.get('temp', {}).get('direction', 'N/A')} (rate: {trends.get('temp', {}).get('rate', 0)}, stability: {trends.get('temp', {}).get('stability', 'N/A')})
- PSI trend: {trends.get('psi', {}).get('direction', 'N/A')} (rate: {trends.get('psi', {}).get('rate', 0)}, stability: {trends.get('psi', {}).get('stability', 'N/A')})

### Rule Engine Health Score: {health_score.get('score', 0)}/100 ({health_score.get('status', 'N/A')})
- Stress Multiplier: {health_score.get('stress_multiplier', 1.0)}
- Tire-Speed Risk: {health_score.get('tire_speed_risk', 0)}%

### Active Alerts: {len(alerts)}
{chr(10).join(f'- {a}' for a in alerts) if alerts else '- None'}

### Contradictions Detected: {len(contradictions)}
{chr(10).join(f'- {c}' for c in contradictions) if contradictions else '- None'}

Based on ALL the above data, provide your expert automotive diagnosis."""

        return prompt

    # ------------------------------------------------------------------
    # Internal helpers for free-tier protection
    # ------------------------------------------------------------------

    def _reset_daily_counter_if_needed(self) -> None:
        """Reset the daily call counter at midnight (by calendar date)."""
        today = date.today().isoformat()
        if today != self._today:
            logger.info(
                f"📅 New day ({today}) — resetting daily AI call counter "
                f"(yesterday used {self._daily_calls}/{self.DAILY_CALL_CAP})"
            )
            self._today = today
            self._daily_calls = 0
            self._quota_exhausted = False

    def _apply_backoff(self) -> None:
        """Set a backoff window after a consecutive error."""
        self._consecutive_errors += 1
        # Cap the exponent to avoid absurd backoff times (max ~128s before MAX_BACKOFF clamp)
        capped_exp = min(self._consecutive_errors, 7)
        wait = min(2 ** capped_exp, self.MAX_BACKOFF)
        self._backoff_until = time.time() + wait
        logger.warning(
            f"⏳ Backoff: next AI call blocked for {wait}s "
            f"(consecutive errors: {self._consecutive_errors})"
        )

    def _clear_backoff(self) -> None:
        """Reset backoff state after a successful call."""
        self._consecutive_errors = 0
        self._backoff_until = 0

    # ------------------------------------------------------------------
    # Main analysis entry point
    # ------------------------------------------------------------------

    async def analyze(
        self,
        telemetry: dict[str, float],
        rule_analysis: dict[str, Any],
        trend_history: dict[str, list[float]] | None = None,
        force: bool = False,
    ) -> dict[str, Any] | None:
        """
        Run AI analysis on current telemetry data.

        Returns cached result if called too frequently (<min_interval).
        Returns None if AI is disabled or an error occurs.

        Free-tier protections applied:
        • Daily call cap (DAILY_CALL_CAP) — auto-disables until midnight.
        • Exponential backoff on consecutive errors.
        • Force-analysis cooldown (FORCE_COOLDOWN seconds).
        """
        async with self._lock:
            now = time.time()

            # ---- Daily quota reset ----
            self._reset_daily_counter_if_needed()

            # ---- Daily cap check ----
            if self._quota_exhausted:
                return self.cached_diagnosis or self._get_fallback_diagnosis(
                    reason="Daily API quota reached. Resets at midnight."
                )

            # ---- Exponential backoff check (skip for forced/manual calls) ----
            if not force and now < self._backoff_until:
                remaining = round(self._backoff_until - now, 0)
                logger.debug(f"⏳ Backoff active — {remaining}s remaining")
                return self.cached_diagnosis or self._get_fallback_diagnosis(
                    reason=f"Backoff active ({remaining}s). Retrying soon."
                )

            # ---- Force-analysis cooldown ----
            if force and (now - self._last_force_time) < self.FORCE_COOLDOWN:
                logger.info(
                    f"⏳ Force-analysis cooldown — "
                    f"{round(self.FORCE_COOLDOWN - (now - self._last_force_time))}s left"
                )
                return self.cached_diagnosis

            # ---- Normal rate limiting — return cached result if too soon ----
            if not force and (now - self.last_analysis_time) < self.min_interval:
                return self.cached_diagnosis

            if not self.enabled or not self.client:
                return self._get_fallback_diagnosis()

            try:
                from google.genai import types

                prompt = self._build_prompt(telemetry, rule_analysis, trend_history)

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=AIVehicleDiagnosis,
                        temperature=0.3,  # Low temperature for consistent, factual output
                        max_output_tokens=1024,
                    ),
                )

                # Parse the structured response
                if response and response.text:
                    diagnosis_data = json.loads(response.text)
                    # Validate with Pydantic
                    diagnosis = AIVehicleDiagnosis(**diagnosis_data)

                    self.call_count += 1
                    self._daily_calls += 1

                    result = {
                        "enabled": True,
                        "source": "gemini-flash",
                        "timestamp": round(now, 3),
                        "severity": diagnosis.severity,
                        "diagnosis": diagnosis.diagnosis,
                        "root_cause": diagnosis.root_cause,
                        "prediction": diagnosis.prediction,
                        "action": diagnosis.action,
                        "confidence": round(diagnosis.confidence, 2),
                        "affected_systems": diagnosis.affected_systems,
                        "call_count": self.call_count,
                        "daily_calls": self._daily_calls,
                        "daily_cap": self.DAILY_CALL_CAP,
                    }

                    self.cached_diagnosis = result
                    self.last_analysis_time = now
                    if force:
                        self._last_force_time = now

                    self._clear_backoff()

                    # Check if we just hit the daily cap
                    if self._daily_calls >= self.DAILY_CALL_CAP:
                        self._quota_exhausted = True
                        logger.warning(
                            f"🛑 Daily API call cap reached ({self.DAILY_CALL_CAP}). "
                            f"AI analysis paused until midnight."
                        )

                    logger.info(
                        f"🧠 AI analysis #{self.call_count} "
                        f"(today: {self._daily_calls}/{self.DAILY_CALL_CAP}): "
                        f"{diagnosis.severity} (confidence: {diagnosis.confidence:.0%})"
                    )
                    return result

                logger.warning("⚠️ Empty response from Gemini API")
                self.error_count += 1
                self._apply_backoff()
                return self.cached_diagnosis or self._get_fallback_diagnosis()

            except Exception as e:
                self.error_count += 1
                error_str = str(e)

                # Detect 429 rate-limit errors and extract the suggested retry delay
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Try to parse the retry delay from the error message
                    retry_seconds = 60  # Default retry for 429
                    import re
                    match = re.search(r"retry in ([\d.]+)s", error_str, re.IGNORECASE)
                    if match:
                        retry_seconds = min(int(float(match.group(1))) + 5, self.MAX_BACKOFF)

                    self._backoff_until = time.time() + retry_seconds
                    self._consecutive_errors += 1
                    logger.warning(
                        f"🛑 Rate limited (429) — backing off for {retry_seconds}s. "
                        f"Error #{self.error_count}"
                    )
                else:
                    self._apply_backoff()
                    logger.error(f"❌ AI analysis error #{self.error_count}: {e}")

                # Return cached or fallback — never crash the dashboard
                fallback_reason = "AI API Rate Limit (Quota Exceeded). Please try again later." if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str else f"AI Error: {e}"
                return self.cached_diagnosis or self._get_fallback_diagnosis(reason=fallback_reason)

    def _get_fallback_diagnosis(self, reason: str | None = None) -> dict[str, Any]:
        """Return a fallback when AI is not available."""
        default_reason = (
            "AI analysis is currently unavailable. "
            "The rule-based engine is monitoring your vehicle. "
            "Set GEMINI_API_KEY in .env to enable AI diagnostics."
        )
        return {
            "enabled": False,
            "source": "fallback",
            "timestamp": round(time.time(), 3),
            "severity": "MONITOR",
            "diagnosis": reason or default_reason,
            "root_cause": "AI service not configured" if not reason else reason,
            "prediction": "Unable to predict — AI offline",
            "action": "Rely on rule-based alerts above for safety guidance",
            "confidence": 0.0,
            "affected_systems": [],
            "call_count": self.call_count,
            "daily_calls": self._daily_calls,
            "daily_cap": self.DAILY_CALL_CAP,
        }

    def get_status(self) -> dict[str, Any]:
        """Return AI analyzer status info, including free-tier quota details."""
        now = time.time()
        return {
            "enabled": self.enabled,
            "model": "gemini-2.5-flash" if self.enabled else "none",
            "total_calls": self.call_count,
            "total_errors": self.error_count,
            "min_interval_seconds": self.min_interval,
            "last_analysis_age": (
                round(now - self.last_analysis_time, 1)
                if self.last_analysis_time > 0
                else None
            ),
            # Free-tier quota info
            "daily_calls": self._daily_calls,
            "daily_cap": self.DAILY_CALL_CAP,
            "daily_remaining": max(0, self.DAILY_CALL_CAP - self._daily_calls),
            "quota_exhausted": self._quota_exhausted,
            "backoff_active": now < self._backoff_until,
            "backoff_remaining": (
                round(self._backoff_until - now, 0)
                if now < self._backoff_until
                else 0
            ),
            "consecutive_errors": self._consecutive_errors,
        }
