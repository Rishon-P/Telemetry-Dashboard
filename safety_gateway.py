"""
Deterministic Safety Gateway
=============================
Three-layer safety evaluation system for vehicle telemetry:

LAYER 1: Hard-coded physical limits (overrides everything)
LAYER 2: Machine Learning Scout (IsolationForest — only if Layer 1 is safe)
LAYER 3: Groq AI (diagnostic breakdown — rate-limited in main.py)
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
from typing import Any

import numpy as np
import time

from layer_3_telematics import generate_diagnostic_report

logger = logging.getLogger("safety_gateway")

FEATURE_NAMES = [
    "speed",
    "rpm",
    "throttle",
    "engine_load",
    "maf",
    "engine_temp",
    "oil_pressure",
    "battery_voltage",
    "fuel_level",
    "tp_fl",
    "tp_fr",
    "tp_rl",
    "tp_rr",
    "airflow_deviation",
    "transmission_deviation",
    "tire_thermal_deviation",
    "electrical_deviation"
]

FEATURE_MAPPING = {
    "speed_kmh": "speed",
    "engine_rpm": "rpm",
    "throttle_pct": "throttle",
    "engine_load_pct": "engine_load",
    "maf_g_sec": "maf",
    "engine_temp_c": "engine_temp",
    "oil_pressure_psi": "oil_pressure",
    "battery_voltage_v": "battery_voltage",
    "fuel_level_pct": "fuel_level",
    "tire_pressure_fl_psi": "tp_fl",
    "tire_pressure_fr_psi": "tp_fr",
    "tire_pressure_rl_psi": "tp_rl",
    "tire_pressure_rr_psi": "tp_rr",
}

TIRE_RADIUS_M = 0.31
FINAL_DRIVE = 3.50
GEAR_RATIOS = {0: 0.0, 1: 2.97, 2: 2.07, 3: 1.43, 4: 1.00, 5: 0.84, 6: 0.56}

# REDLINE threshold — expected_rpm above this triggers a physical warning
REDLINE_RPM = 6000

_REVERSE_MAPPING = {v: k for k, v in FEATURE_MAPPING.items()}


class SafetyBoundaryChecker:
    """Layer 1: deterministic physical limits evaluated before ML."""

    def __init__(self):
        self.active_faults = set()

    def check_physical_safety(self, data: dict[str, float]) -> tuple[bool, list[str], str | None]:
        """
        Returns (layer_1_triggered, violations, layer_1_cause).
        Any violation immediately implies EMERGENCY — ML must not run.
        """
        violations: list[str] = []
        layer_1_cause: str | None = None

        speed = data.get("speed_kmh", 0)
        rpm = data.get("engine_rpm", 0)
        throttle = data.get("throttle_pct", 0)
        selected_gear = int(data.get("selected_gear", 6))
        engine_temp = data.get("engine_temp_c", 0)
        oil_pressure = data.get("oil_pressure_psi", 50)
        maf = data.get("maf_g_sec", 45)
        fuel_level = data.get("fuel_level_pct", 100)
        tp_fl = data.get("tire_pressure_fl_psi", 32)
        tp_fr = data.get("tire_pressure_fr_psi", 32)
        tp_rl = data.get("tire_pressure_rl_psi", 32)
        tp_rr = data.get("tire_pressure_rr_psi", 32)

        # Rule A: Dead MAF / Suffocation — ECU Hysteresis Logic
        # Activation Threshold < 7.0 | Healing Threshold > 10.5
        maf_is_faulty = "maf_sensor_dead" in self.active_faults

        if not maf_is_faulty:
            if maf < 7.0 and rpm > 1000:
                self.active_faults.add("maf_sensor_dead")
                layer_1_cause = layer_1_cause or "maf_sensor_dead"
                violations.append(f"CRITICAL: MAF sensor restricted ({maf} g/s) while engine running at {rpm} RPM")
        else:
            # Fault is active. Require mathematically reachable healing margin to turn off.
            if maf > 10.5 or rpm <= 1000:
                self.active_faults.remove("maf_sensor_dead")
            else:
                layer_1_cause = layer_1_cause or "maf_sensor_dead"
                violations.append(f"CRITICAL: MAF sensor restricted ({maf} g/s) while engine running at {rpm} RPM")

        # Rule B: Kinematic Mismatches (Gear-Aware)
        if speed > 100 and rpm < 1000 and throttle > 20:
            if selected_gear > 0:
                # Car is in gear, but engine is not spinning with the wheels
                layer_1_cause = layer_1_cause or "transmission_disconnect"
                violations.append(
                    f"CRITICAL: Transmission disconnect — "
                    f"Speed {speed} km/h, RPM {rpm} in Gear {selected_gear}"
                )
            else:
                # Car is in Neutral. Transmission is fine, but engine won't rev.
                layer_1_cause = layer_1_cause or "engine_unresponsive"
                violations.append(
                    f"CRITICAL: Engine unresponsive to throttle in Neutral — "
                    f"Throttle {throttle}%, RPM {rpm}"
                )

        # Rule C: Critical overheat
        if engine_temp > 115:
            layer_1_cause = layer_1_cause or "engine_overheat"
            violations.append(
                f"CRITICAL: Engine overheating at {engine_temp}°C (limit: 115°C)"
            )

        # Rule D: Oil loss — critically low oil while engine running
        if oil_pressure < 10 and rpm > 0:
            layer_1_cause = layer_1_cause or "critical_oil_loss"
            violations.append(
                f"CRITICAL: Oil pressure {oil_pressure} PSI — "
                f"catastrophic engine damage imminent"
            )

        # Rule E: Tire blowout — any tire below 20 PSI
        for tire_name, tire_val in [
            ("FL", tp_fl),
            ("FR", tp_fr),
            ("RL", tp_rl),
            ("RR", tp_rr),
        ]:
            if tire_val < 20:
                layer_1_cause = layer_1_cause or "tire_blowout"
                violations.append(
                    f"CRITICAL: Tire {tire_name} blowout risk — "
                    f"{tire_val} PSI (limit: 20 PSI)"
                )

        # Rule F: Battery voltage anomalies
        battery_voltage = data.get("battery_voltage_v", 13.8)
        if battery_voltage < 12.0:
            layer_1_cause = layer_1_cause or "battery_critical_low"
            violations.append(
                f"CRITICAL: Battery voltage critically low at {battery_voltage}V (limit: 12.0V)"
            )
        elif battery_voltage > 15.5:
            layer_1_cause = layer_1_cause or "battery_critical_high"
            violations.append(
                f"CRITICAL: Battery voltage critically high at {battery_voltage}V (limit: 15.5V)"
            )
        if fuel_level <= 0.8 and rpm > 0:
            layer_1_cause = layer_1_cause or "out_of_fuel"
            violations.append(
                f"CRITICAL: Vehicle out of fuel (0%) while engine running at {rpm} RPM"
            )

        return len(violations) > 0, violations, layer_1_cause


class MLScout:
    """Layer 2: IsolationForest with strict feature order and scaler.transform."""

    def __init__(
        self,
        scaler_path: str | Path | None = None,
        model_path: str | Path | None = None,
    ) -> None:
        self.scaler = None
        self.model = None
        self.loaded = False

        base = Path(__file__).resolve().parent
        scaler_path = Path(scaler_path or base / "vehicle_scaler.pkl")
        model_path = Path(model_path or base / "vehicle_anomaly_model.pkl")
        self._load_models(scaler_path, model_path)

    def _load_models(self, scaler_path: Path, model_path: Path) -> None:
        try:
            if not scaler_path.exists() or not model_path.exists():
                logger.warning("ML model files not found — ML Scout disabled.")
                return
            # Models are exported via joblib in train_model.py (not raw pickle)
            self.scaler = joblib.load(scaler_path)
            self.model = joblib.load(model_path)
            self.loaded = True
            logger.info("ML Scout models loaded (scaler + IsolationForest).")
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            self.loaded = False

    def evaluate(
        self, data: dict[str, float]
    ) -> tuple[int, float, str | None, bool]:
        """
        Returns (prediction, anomaly_score, root_cause, is_ml_anomaly).
        prediction: 1 = normal, -1 = anomaly
        """
        if not self.loaded:
            return 1, -0.4, None, False

        try:
            # --- LIVE FEATURE ENGINEERING (DUAL RESIDUALS) ---
            rpm_val = data.get(_REVERSE_MAPPING.get("rpm", "engine_rpm"), 800.0)
            load_val = data.get(_REVERSE_MAPPING.get("engine_load", "engine_load_pct"), 15.0)
            maf_val = data.get(_REVERSE_MAPPING.get("maf", "maf_g_sec"), 2.45)
            speed_val = data.get(_REVERSE_MAPPING.get("speed", "vehicle_speed"), 0.0)
            throttle_val = data.get(_REVERSE_MAPPING.get("throttle", "throttle_position"), 0.0)

            # 1. Air Intake Diagnostics
            safe_rpm = max(1.0, float(rpm_val))
            safe_load = max(1.0, float(load_val))
            expected_maf = (safe_rpm * safe_load * 2.0 * 1.225) / 12000.0
            data["airflow_deviation"] = abs(float(maf_val) - expected_maf)

            # 2. Drivetrain & Kinematic Diagnostics — MANUAL TRANSMISSION (user-selected gear)
            expected_gear = int(data.get("selected_gear", 6))
            # Clamp to valid range: 0 (Neutral) to 6
            expected_gear = max(0, min(6, expected_gear))

            if expected_gear == 0:
                # NEUTRAL STATE: Drivetrain disconnected.
                # RPM is dictated purely by engine idle (800) and free-revving throttle multiplier.
                expected_rpm = 800.0 + (float(throttle_val) * 30.0)
            else:
                # IN-GEAR STATE: Drivetrain connected.
                base_rpm = (float(speed_val) * GEAR_RATIOS[expected_gear] * FINAL_DRIVE / TIRE_RADIUS_M) * 2.65258
                expected_rpm = max(400.0, base_rpm + (float(throttle_val) * 5.0))

            data["transmission_deviation"] = abs(float(rpm_val) - expected_rpm)

            # Redline Warning: high speed + low gear → expected_rpm spikes over REDLINE_RPM
            data["redline_warning"] = 1.0 if expected_rpm > REDLINE_RPM else 0.0

            # 3. Tire Thermal & Asymmetry Diagnostics
            expected_tp = 32.0 + (float(speed_val) / 38.0)

            tp_fl = float(data.get(_REVERSE_MAPPING.get("tp_fl", "tire_pressure_fl"), 32.0))
            tp_fr = float(data.get(_REVERSE_MAPPING.get("tp_fr", "tire_pressure_fr"), 32.0))
            tp_rl = float(data.get(_REVERSE_MAPPING.get("tp_rl", "tire_pressure_rl"), 32.0))
            tp_rr = float(data.get(_REVERSE_MAPPING.get("tp_rr", "tire_pressure_rr"), 32.0))

            data["tire_thermal_deviation"] = max(
                abs(tp_fl - expected_tp), abs(tp_fr - expected_tp),
                abs(tp_rl - expected_tp), abs(tp_rr - expected_tp)
            )

            # 4. Electrical System Diagnostics
            expected_voltage = 13.8 if float(rpm_val) > 400.0 else 12.6
            batt_val = float(data.get(_REVERSE_MAPPING.get("battery_voltage", "battery_voltage"), 12.6))

            data["electrical_deviation"] = abs(batt_val - expected_voltage)

            raw_data_array = [
                data.get(_REVERSE_MAPPING.get(feat, feat), 0) for feat in FEATURE_NAMES
            ]

            logger.debug(
                "MLScout feature array: speed=%.1f rpm=%.0f gear=%d expected_rpm=%.0f "
                "transmission_dev=%.1f tire_thermal_dev=%.2f airflow_dev=%.2f electrical_dev=%.2f",
                float(speed_val), float(rpm_val), expected_gear, expected_rpm,
                data["transmission_deviation"], data["tire_thermal_deviation"],
                data["airflow_deviation"], data["electrical_deviation"],
            )

            scaled_data = self.scaler.transform([raw_data_array])

            # 1. Base ML Predictions
            prediction = int(self.model.predict(scaled_data)[0])
            anomaly_score = float(self.model.score_samples(scaled_data)[0])

            # 2. Z-Score Calculations
            abs_z_scores = np.abs(scaled_data[0])

            # --- THE WEIGHTING FIX ---
            # Discount the tire pressures so they don't steal the root cause
            # from complex engine anomalies due to minor 2 PSI fluctuations.
            # Indices 9, 10, 11, 12 are the four tires.
            for i in range(9, 13):
                abs_z_scores[i] = abs_z_scores[i] * 0.3

            max_z_score = float(np.max(abs_z_scores))
            max_dev_index = int(np.argmax(abs_z_scores))

            logger.debug(
                "MLScout z-scores: max=%.3f feature=%s",
                max_z_score, FEATURE_NAMES[max_dev_index],
            )

            is_ml_anomaly = False
            root_cause = None

            # ==========================================
            # THE HYBRID ML LOGIC
            # ==========================================
            # Extract the raw fuel value safely using your mapping
            fuel_val = data.get(_REVERSE_MAPPING.get("fuel_level", "fuel_level_pct"), 100)

            if prediction == -1:
                # Scenario A: Isolation Forest found a complex, multi-sensor anomaly
                is_ml_anomaly = True
                root_cause = FEATURE_NAMES[max_dev_index]

            elif max_z_score > 5.0:
                # Scenario B: Isolation Forest is blind, but Z-Score caught a massive single-sensor drop
                logger.warning(f"Z-Score Fallback Triggered! {FEATURE_NAMES[max_dev_index]} hit {max_z_score:.1f} standard deviations.")
                is_ml_anomaly = True
                root_cause = FEATURE_NAMES[max_dev_index]
                prediction = -1  # Force the prediction to -1 so the gateway understands it

            elif fuel_val < 10.0:
                # Scenario C: Predictive Maintenance (Low Fuel Warning)
                logger.warning(f"ML Scout Predictive Warning: Fuel Level low at {fuel_val:.1f}%.")
                is_ml_anomaly = True
                root_cause = "fuel_level"
                prediction = -1

            return prediction, anomaly_score, root_cause, is_ml_anomaly

        except Exception as e:
            logger.error(f"ML Scout evaluation error: {e}")
            return 1, -0.4, None, False


def _build_deterministic_context(ml_root_cause: str, filtered_data: dict[str, float]) -> str:
    """
    Build a strictly calculated, direction-explicit context string for the Groq AI.

    For every anomaly type, this function:
      1. Reads the actual live sensor values from filtered_data.
      2. Recalculates the same expected baseline that the ML used.
      3. Computes the signed deviation (actual - expected).
      4. States the direction (ABOVE / BELOW) and the magnitude explicitly.

    The returned string contains only mathematical facts — no guesses, no ambiguity.
    The Groq AI receives this string and must reformat it, not interpret it.
    """
    # --- Extract live sensor values (correct key names, post-filter) ---
    speed_val   = float(filtered_data.get("speed_kmh", 0.0))
    rpm_val     = float(filtered_data.get("engine_rpm", 800.0))
    load_val    = float(filtered_data.get("engine_load_pct", 15.0))
    throttle_val = float(filtered_data.get("throttle_pct", 0.0))
    actual_maf  = float(filtered_data.get("maf_g_sec", 0.0))
    actual_volt = float(filtered_data.get("battery_voltage_v", 13.8))
    gear        = int(filtered_data.get("selected_gear", 1))
    fuel_val    = float(filtered_data.get("fuel_level_pct", 100.0))

    tp_fl = float(filtered_data.get("tire_pressure_fl_psi", 32.0))
    tp_fr = float(filtered_data.get("tire_pressure_fr_psi", 32.0))
    tp_rl = float(filtered_data.get("tire_pressure_rl_psi", 32.0))
    tp_rr = float(filtered_data.get("tire_pressure_rr_psi", 32.0))

    # ── tire_thermal_deviation ────────────────────────────────────────────────
    if ml_root_cause == "tire_thermal_deviation":
        expected_tp = round(32.0 + (speed_val / 38.0), 1)

        # Evaluate each tire individually — averaging masks mixed fault states
        # (e.g. two over-inflated + two under-inflated = false "normal" average).
        tire_readings = {
            "FL": round(tp_fl, 1),
            "FR": round(tp_fr, 1),
            "RL": round(tp_rl, 1),
            "RR": round(tp_rr, 1),
        }

        tire_parts: list[str] = []
        problem_wheels: list[str] = []

        for wheel, actual in tire_readings.items():
            dev = round(actual - expected_tp, 1)
            abs_dev = abs(dev)

            if abs_dev < 0.5:
                # Within rounding noise — treat as matching
                status = "MATCHING"
                tire_parts.append(f"{wheel}={actual} PSI (MATCHING expected)")
            elif dev > 0:
                status = "OVER"
                tire_parts.append(f"{wheel}={actual} PSI ({abs_dev} PSI OVER)")
                problem_wheels.append(f"{wheel} over-pressurized by {abs_dev} PSI")
            else:
                status = "UNDER"
                tire_parts.append(f"{wheel}={actual} PSI ({abs_dev} PSI UNDER)")
                problem_wheels.append(f"{wheel} under-pressurized by {abs_dev} PSI")

        tire_summary = ", ".join(tire_parts)

        if problem_wheels:
            fault_detail = "; ".join(problem_wheels)
        else:
            fault_detail = "all tires near baseline — deviation is marginal"

        return (
            f"At {speed_val:.1f} km/h, thermodynamic baseline requires {expected_tp} PSI per tire. "
            f"Individual readings: {tire_summary}. "
            f"Confirmed per-wheel fault: {fault_detail}."
        )

    # ── airflow_deviation ─────────────────────────────────────────────────────
    if ml_root_cause == "airflow_deviation":
        safe_rpm      = max(1.0, rpm_val)
        safe_load     = max(1.0, load_val)
        expected_maf  = round((safe_rpm * safe_load * 2.0 * 1.225) / 12000.0, 2)
        deviation     = round(actual_maf - expected_maf, 2)
        direction     = "ABOVE" if deviation >= 0 else "BELOW"
        abs_dev       = abs(deviation)
        fault = (
            "excess airflow: intake air leak or MAF sensor reading falsely high"
            if deviation >= 0 else
            "insufficient airflow: intake restriction, clogged air filter, or failing MAF sensor"
        )
        return (
            f"At {rpm_val:.0f} RPM under {load_val:.0f}% engine load, calculated MAF requirement is "
            f"{expected_maf} g/s. Actual MAF is {actual_maf} g/s, which is {abs_dev} g/s {direction} "
            f"the breathing baseline. Confirmed condition: {fault}."
        )

    # ── transmission_deviation ────────────────────────────────────────────────
    if ml_root_cause == "transmission_deviation":
        clamped_gear = max(0, min(6, gear))
        if clamped_gear == 0:
            expected_rpm_val = round(800.0 + (throttle_val * 30.0), 0)
        else:
            base_rpm = (
                speed_val * GEAR_RATIOS[clamped_gear] * FINAL_DRIVE / TIRE_RADIUS_M
            ) * 2.65258
            expected_rpm_val = round(max(400.0, base_rpm + (throttle_val * 5.0)), 0)
        deviation    = round(rpm_val - expected_rpm_val, 0)
        direction    = "ABOVE" if deviation >= 0 else "BELOW"
        abs_dev      = abs(deviation)
        fault = (
            "RPM exceeds kinematic prediction: wheel slip, torque converter lockup failure, or gear ratio mismatch"
            if deviation >= 0 else
            "RPM below kinematic prediction: drivetrain disconnect, clutch slip, or transmission fault"
        )
        return (
            f"In Gear {clamped_gear} at {speed_val:.1f} km/h, kinematic ratio requires "
            f"{expected_rpm_val:.0f} RPM. Actual RPM is {rpm_val:.0f}, which is {abs_dev:.0f} RPM "
            f"{direction} the drivetrain baseline. Confirmed condition: {fault}."
        )

    # ── electrical_deviation ──────────────────────────────────────────────────
    if ml_root_cause == "electrical_deviation":
        expected_volt = 13.8 if rpm_val > 400.0 else 12.6
        deviation     = round(actual_volt - expected_volt, 2)
        direction     = "ABOVE" if deviation >= 0 else "BELOW"
        abs_dev       = abs(deviation)
        fault = (
            "voltage regulator failure or alternator overcharging the battery"
            if deviation >= 0 else
            "alternator underperformance, excessive parasitic drain, or failing alternator diode"
        )
        return (
            f"At {rpm_val:.0f} RPM, alternator output must maintain {expected_volt}V. "
            f"Actual battery voltage is {actual_volt}V, which is {abs_dev}V {direction} "
            f"the charging baseline. Confirmed condition: {fault}."
        )

    # ── fuel_level (predictive maintenance) ──────────────────────────────────
    if ml_root_cause == "fuel_level":
        return (
            f"Fuel level is at {fuel_val:.1f}%, which is below the 10% predictive maintenance "
            f"threshold. Refuel immediately to prevent engine starvation."
        )

    # ── generic fallback ──────────────────────────────────────────────────────
    return (
        f"Anomaly detected in feature '{ml_root_cause}'. "
        f"Physical inspection required to determine root cause."
    )


class SafetyGateway:
    """
    Gateway hierarchy (Layer 1 overrides Layer 2):
      1. Physical limits → EMERGENCY (ML skipped)
      2. ML anomaly (-1) → WARNING
      3. Otherwise (with Hysteresis) → HEALTHY
    """

    def __init__(self, ml_scout=None) -> None:
        self.boundary_checker = SafetyBoundaryChecker()
        self.ml_scout = ml_scout or MLScout()

        # 1. THE TIMERS (For API Rate Limiting & UI Hysteresis)
        self.last_gemini_call_time = 0.0
        self.warning_cooldown_time = 0.0

        # 2. THE SHOCK ABSORBER MEMORY
        self.smoothed_sensor_state = {}

        # 3. LAYER 3 AI DIAGNOSTIC CACHE
        self.cached_layer_3_report: str | None = None
        self.last_root_cause: str | None = None

    def apply_low_pass_filter(self, raw_data: dict[str, float], alpha: float = 0.2) -> dict[str, float]:
        """Filters out minor vibrations but snaps instantly on manual slider jumps."""
        filtered_data = {}
        for sensor, value in raw_data.items():
            # 1. EXEMPT DISCRETE STATES (Do not smooth mechanical gear shifts)
            if sensor == "selected_gear":
                self.smoothed_sensor_state[sensor] = value
                filtered_data[sensor] = value
                continue

            # 2. SMOOTH ANALOG SENSORS
            if sensor not in self.smoothed_sensor_state:
                self.smoothed_sensor_state[sensor] = value
                filtered_data[sensor] = value
            else:
                previous = self.smoothed_sensor_state[sensor]

                # Bypass filter if jump is > 10% + 2.0 flat buffer
                if abs(value - previous) > (abs(previous) * 0.1) + 2.0:
                    dynamic_alpha = 1.0
                else:
                    dynamic_alpha = alpha

                smoothed_val = (dynamic_alpha * value) + ((1.0 - dynamic_alpha) * previous)
                self.smoothed_sensor_state[sensor] = smoothed_val
                filtered_data[sensor] = smoothed_val

        return filtered_data

    def evaluate(self, data: dict[str, float]) -> dict[str, Any]:
        current_time = time.time()

        # ── Apply the Shock Absorber ────────────────────────────────────────
        filtered_data = self.apply_low_pass_filter(data, alpha=0.2)

        # ── Layer 1: physical limits FIRST ─────────────────────────────────
        layer_1_triggered, safety_violations, layer_1_cause = (
            self.boundary_checker.check_physical_safety(filtered_data)
        )

        ml_prediction = 1
        ml_anomaly_score = -0.4
        ml_root_cause = None
        is_ml_anomaly = False

        if layer_1_triggered:
            self.warning_cooldown_time = current_time

            # STRICT CACHE BARRIER: only regenerate if time elapsed or cause changed
            time_elapsed = (current_time - self.last_gemini_call_time) > 60
            cause_changed = layer_1_cause != self.last_root_cause

            if time_elapsed or cause_changed:
                # ANTI-HALLUCINATION PAYLOAD for Layer 1:
                # Send only the exact physical violation string — no ambiguous sensor arrays.
                strict_payload = {
                    "root_cause": layer_1_cause,
                    "violation_details": safety_violations[0] if safety_violations else "Critical limit exceeded."
                }
                self.cached_layer_3_report = generate_diagnostic_report(strict_payload)
                self.last_gemini_call_time = current_time
                self.last_root_cause = layer_1_cause

            logger.critical(f"EMERGENCY: {layer_1_cause} | Violations: {safety_violations}")

            return {
                "status": "EMERGENCY",
                "health_score": 0.0,
                "gateway_decision": "PHYSICAL_DANGER_DETECTED",
                "gateway_note": "Critical physical safety threshold violated.",
                "root_cause": layer_1_cause,
                "ml_prediction": 1,
                "ml_anomaly_score": -0.4,
                "ml_root_cause": None,
                "is_ml_anomaly": False,
                "layer_1_triggered": True,
                "layer_1_cause": layer_1_cause,
                "is_physically_dangerous": True,
                "safety_violations": safety_violations,
                "trigger_gemini": True,
                "layer_3_report": self.cached_layer_3_report,
                "redline_warning": False
            }

        # ── Layer 2: ML only when physical limits are safe ──────────────────
        ml_prediction, ml_anomaly_score, ml_root_cause, is_ml_anomaly = (
            self.ml_scout.evaluate(filtered_data)
        )

        # Extract redline_warning stamped into filtered_data by MLScout
        redline_warning = bool(filtered_data.get("redline_warning", 0.0))

        if is_ml_anomaly:
            self.warning_cooldown_time = current_time

            time_elapsed = (current_time - self.last_gemini_call_time) > 60
            cause_changed = ml_root_cause != self.last_root_cause

            if time_elapsed or cause_changed:
                # ── DETERMINISTIC CONTEXT INJECTION ────────────────────────
                # Build a mathematically precise context string that explicitly
                # states the actual value, the expected baseline, and the
                # signed direction of the deviation. The AI receives facts only
                # — it must reformat them, not interpret or guess.
                deterministic_context = _build_deterministic_context(
                    ml_root_cause, filtered_data
                )

                strict_ml_payload = {
                    "diagnostic_layer": "Machine Learning Anomaly Detection",
                    "root_cause": ml_root_cause,
                    "anomaly_score_magnitude": float(round(abs(ml_anomaly_score), 4)),
                    "physical_context": deterministic_context,
                }

                self.cached_layer_3_report = generate_diagnostic_report(strict_ml_payload)
                self.last_gemini_call_time = current_time
                self.last_root_cause = ml_root_cause

                logger.info(
                    "Layer 3 context built for %s: %s",
                    ml_root_cause, deterministic_context,
                )

            logger.warning(f"ML ANOMALY: {ml_root_cause}")

            return {
                "status": "WARNING",
                "health_score": 50.0,
                "gateway_decision": "ML_ANOMALY_DETECTED",
                "gateway_note": "ML model detected anomalous telemetry.",
                "root_cause": ml_root_cause,
                "ml_prediction": -1,
                "ml_anomaly_score": float(ml_anomaly_score),
                "ml_root_cause": ml_root_cause,
                "is_ml_anomaly": True,
                "layer_1_triggered": False,
                "layer_1_cause": None,
                "is_physically_dangerous": False,
                "safety_violations": [],
                "trigger_gemini": True,
                "layer_3_report": self.cached_layer_3_report,
                "redline_warning": False
            }

        # ── HYSTERESIS (Sticky UI) ──────────────────────────────────────────
        # Keep WARNING state for 3 seconds after clearing to prevent UI flickering.
        if (current_time - self.warning_cooldown_time) < 3.0:
            return {
                "status": "WARNING",
                "health_score": 87.5,
                "gateway_decision": "STABILIZING",
                "gateway_note": "Systems returning to normal. Stabilizing...",
                "root_cause": "Stabilizing",
                "ml_prediction": ml_prediction,
                "ml_anomaly_score": ml_anomaly_score,
                "ml_root_cause": None,
                "is_ml_anomaly": False,
                "layer_1_triggered": False,
                "layer_1_cause": None,
                "is_physically_dangerous": False,
                "safety_violations": [],
                "trigger_gemini": False,
                "redline_warning": redline_warning,
            }

        # ── ALL CLEAR ───────────────────────────────────────────────────────
        self.cached_layer_3_report = None
        self.last_gemini_call_time = 0.0
        self.last_root_cause = None
        return {
            "status": "HEALTHY",
            "health_score": 97.5,
            "gateway_decision": "ALL_SYSTEMS_NORMAL",
            "gateway_note": "All systems operating normally. No physical safety concerns.",
            "root_cause": None,
            "ml_prediction": ml_prediction,
            "ml_anomaly_score": ml_anomaly_score,
            "ml_root_cause": ml_root_cause,
            "is_ml_anomaly": False,
            "layer_1_triggered": False,
            "layer_1_cause": None,
            "is_physically_dangerous": False,
            "safety_violations": [],
            "trigger_gemini": False,
            "redline_warning": redline_warning,
        }


_ml_scout = MLScout()
safety_gateway = SafetyGateway(ml_scout=_ml_scout)


def evaluate_telemetry(data: dict[str, float]) -> dict[str, Any]:
    """Public API: evaluate telemetry through the 3-layer Safety Gateway."""
    return safety_gateway.evaluate(data)