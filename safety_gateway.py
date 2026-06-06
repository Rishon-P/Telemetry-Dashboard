"""
Deterministic Safety Gateway
=============================
Three-layer safety evaluation system for vehicle telemetry:

LAYER 1: Hard-coded physical limits (overrides everything)
LAYER 2: Machine Learning Scout (IsolationForest — only if Layer 1 is safe)
LAYER 3: Gemini AI (diagnostic breakdown — rate-limited in main.py)
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
from typing import Any

import numpy as np
import time

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

_REVERSE_MAPPING = {v: k for k, v in FEATURE_MAPPING.items()}


class SafetyBoundaryChecker:
    """Layer 1: deterministic physical limits evaluated before ML."""

    @staticmethod
    def check_physical_safety(data: dict[str, float]) -> tuple[bool, list[str], str | None]:
        """
        Returns (layer_1_triggered, violations, layer_1_cause).
        Any violation immediately implies EMERGENCY — ML must not run.
        """
        violations: list[str] = []
        layer_1_cause: str | None = None

        speed = data.get("speed_kmh", 0)
        rpm = data.get("engine_rpm", 0)
        throttle = data.get("throttle_pct", 0)
        engine_temp = data.get("engine_temp_c", 0)
        oil_pressure = data.get("oil_pressure_psi", 50)
        maf = data.get("maf_g_sec", 45)
        tp_fl = data.get("tire_pressure_fl_psi", 32)
        tp_fr = data.get("tire_pressure_fr_psi", 32)
        tp_rl = data.get("tire_pressure_rl_psi", 32)
        tp_rr = data.get("tire_pressure_rr_psi", 32)

        # Rule A: Dead MAF — sensor near zero while engine running
        if maf < 5 and rpm > 1000:
            layer_1_cause = layer_1_cause or "maf_sensor_dead"
            violations.append(
                f"CRITICAL: MAF sensor dead ({maf} g/s) while engine running at {rpm} RPM"
            )

        # Rule B: Transmission disconnect — high speed, low RPM, throttle applied
        if speed > 100 and rpm < 1000 and throttle > 20:
            layer_1_cause = layer_1_cause or "transmission_disconnect"
            violations.append(
                f"CRITICAL: Possible transmission disconnect — "
                f"Speed {speed} km/h, RPM {rpm}, Throttle {throttle}%"
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
        if battery_voltage < 10.0:
            layer_1_cause = layer_1_cause or "battery_critical_low"
            violations.append(
                f"CRITICAL: Battery voltage critically low at {battery_voltage}V (limit: 12.0V)"
            )
        elif battery_voltage > 15.5:
            layer_1_cause = layer_1_cause or "battery_critical_high"
            violations.append(
                f"CRITICAL: Battery voltage critically high at {battery_voltage}V (limit: 15.5V)"
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
            raw_data_array = [
                data.get(_REVERSE_MAPPING[feat], 0) for feat in FEATURE_NAMES
            ]
            scaled_data = self.scaler.transform([raw_data_array])
            
            # 1. Base ML Predictions
            prediction = int(self.model.predict(scaled_data)[0])
            anomaly_score = float(self.model.score_samples(scaled_data)[0])

            # 2. Z-Score Calculations
            abs_z_scores = np.abs(scaled_data[0])
            max_z_score = float(np.max(abs_z_scores))
            max_dev_index = int(np.argmax(abs_z_scores))
            
            is_ml_anomaly = False
            root_cause = None

            # ==========================================
            # THE HYBRID ML LOGIC
            # ==========================================
            if prediction == -1:
                # Scenario A: Isolation Forest found a complex, multi-sensor anomaly
                is_ml_anomaly = True
                root_cause = FEATURE_NAMES[max_dev_index]
                
            elif max_z_score > 5.0:
                # Scenario B: Isolation Forest is blind, but Z-Score caught a massive single-sensor drop
                logger.warning(f"Z-Score Fallback Triggered! {FEATURE_NAMES[max_dev_index]} hit {max_z_score:.1f} standard deviations.")
                is_ml_anomaly = True
                root_cause = FEATURE_NAMES[max_dev_index]
                prediction = -1 # Force the prediction to -1 so the gateway understands it

            return prediction, anomaly_score, root_cause, is_ml_anomaly
            
        except Exception as e:
            logger.error(f"ML Scout evaluation error: {e}")
            return 1, -0.4, None, False

class SafetyGateway:
    """
    Gateway hierarchy (Layer 1 overrides Layer 2):
      1. Physical limits → EMERGENCY (ML skipped)
      2. ML anomaly (-1) → WARNING
      3. Otherwise (with Hysteresis) → HEALTHY
    """

    def __init__(self, ml_scout=None) -> None:
        # Assuming SafetyBoundaryChecker and MLScout are imported
        self.boundary_checker = SafetyBoundaryChecker()
        self.ml_scout = ml_scout or MLScout()
        
        # 1. THE TIMERS (For API Rate Limiting & UI Hysteresis)
        self.last_gemini_call_time = 0.0
        self.warning_cooldown_time = 0.0
        
        # 2. THE SHOCK ABSORBER MEMORY
        self.smoothed_sensor_state = {}

    def apply_low_pass_filter(self, raw_data: dict[str, float], alpha: float = 0.2) -> dict[str, float]:
        """Filters out 0.1 sensor vibrations before evaluation."""
        filtered_data = {}
        for sensor, value in raw_data.items():
            if sensor not in self.smoothed_sensor_state:
                self.smoothed_sensor_state[sensor] = value
                filtered_data[sensor] = value
            else:
                smoothed_val = (alpha * value) + ((1.0 - alpha) * self.smoothed_sensor_state[sensor])
                self.smoothed_sensor_state[sensor] = smoothed_val
                filtered_data[sensor] = smoothed_val
        return filtered_data

    def evaluate(self, data: dict[str, float]) -> dict[str, Any]:
        current_time = time.time()

        # ── Step 0: Apply the Shock Absorber ───────────────────────────────
        filtered_data = self.apply_low_pass_filter(data, alpha=0.2)

        # ── Layer 1: physical limits FIRST ───────────────────────────────
        layer_1_triggered, safety_violations, layer_1_cause = (
            self.boundary_checker.check_physical_safety(filtered_data)
        )

        ml_prediction = 1
        ml_anomaly_score = -0.4
        ml_root_cause = None
        is_ml_anomaly = False
        trigger_gemini = False

        if layer_1_triggered:
            self.warning_cooldown_time = current_time # Reset sticky UI timer
            logger.critical(
                f"EMERGENCY: {layer_1_cause} | Violations: {safety_violations}"
            )
            return {
                "status": "EMERGENCY",
                "health_score": 0.0,
                "gateway_decision": "PHYSICAL_DANGER_DETECTED",
                "gateway_note": "Critical physical safety threshold violated. Immediate action required.",
                "root_cause": layer_1_cause,
                "ml_prediction": ml_prediction,
                "ml_anomaly_score": ml_anomaly_score,
                "ml_root_cause": ml_root_cause,
                "is_ml_anomaly": is_ml_anomaly,
                "layer_1_triggered": True,
                "layer_1_cause": layer_1_cause,
                "is_physically_dangerous": True,
                "safety_violations": safety_violations,
                "trigger_gemini": False # Hard limits don't need AI explanation
            }

        # ── Layer 2: ML only when physical limits are safe ─────────────
        ml_prediction, ml_anomaly_score, ml_root_cause, is_ml_anomaly = (
            self.ml_scout.evaluate(filtered_data)
        )

        if is_ml_anomaly:
            self.warning_cooldown_time = current_time # Reset sticky UI timer
            
            # API Debounce Check
            if (current_time - self.last_gemini_call_time) > 60:
                trigger_gemini = True
                self.last_gemini_call_time = current_time

            logger.warning(
                f"WARNING: ML anomaly (score: {ml_anomaly_score:.4f}, "
                f"root_cause: {ml_root_cause}). Physical systems normal."
            )
            return {
                "status": "WARNING",
                "health_score": 87.5,
                "gateway_decision": "ML_ANOMALY_DETECTED",
                "gateway_note": "Machine Learning detected anomalous pattern. Physical systems normal.",
                "root_cause": ml_root_cause,
                "ml_prediction": ml_prediction,
                "ml_anomaly_score": ml_anomaly_score,
                "ml_root_cause": ml_root_cause,
                "is_ml_anomaly": True,
                "layer_1_triggered": False,
                "layer_1_cause": None,
                "is_physically_dangerous": False,
                "safety_violations": [],
                "trigger_gemini": trigger_gemini
            }

        # ── Layer 3: HYSTERESIS (Sticky UI) ───────────────────────────
        # Even if the ML model thinks the car is safe, we force it to stay in 
        # a Warning state for 3 seconds to prevent UI flickering.
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
                "trigger_gemini": False
            }

        # ── Final Layer: ALL CLEAR ─────────────────────────────────────
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
            "trigger_gemini": False
        }

_ml_scout = MLScout()
safety_gateway = SafetyGateway(ml_scout=_ml_scout)


def evaluate_telemetry(data: dict[str, float]) -> dict[str, Any]:
    """Public API: evaluate telemetry through the 3-layer Safety Gateway."""
    return safety_gateway.evaluate(data)
