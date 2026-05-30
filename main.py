"""
Automotive Telemetry Dashboard — FastAPI + WebSocket Backend
============================================================
• Maintains a mutable simulation state with baseline telemetry values.
• A background broadcaster pushes noisy readings every 1 s to every
  connected WebSocket client.
• Clients can send JSON commands to update any baseline parameter
  on-the-fly; all future broadcasts immediately reflect the change.
• Real-time data analysis WebSocket for SDV diagnostics.
• Analyzes vehicle health based on 60-second rolling window.
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import random
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ai_analyzer import GeminiVehicleAnalyzer

# Load environment variables from .env file
load_dotenv()

STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("telemetry")

# ---------------------------------------------------------------------------
# Simulation state
# ---------------------------------------------------------------------------

class SimulationState:
    """Thread-safe (asyncio-safe) mutable container for baseline telemetry."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # Baseline values — clients can override these at any time.
        self._baselines: dict[str, float] = {
            "speed_kmh": 80.0,
            "engine_temp_c": 90.0,
            "tire_pressure_psi": 32.0,
            "engine_rpm": 1500.0,
            "oil_pressure_psi": 45.0,
            "battery_voltage_v": 13.8,
            "tire_pressure_fl_psi": 32.0,
            "tire_pressure_fr_psi": 32.0,
            "tire_pressure_rl_psi": 32.0,
            "tire_pressure_rr_psi": 32.0,
        }

    async def get_snapshot(self) -> dict[str, float]:
        """Return a *noisy* copy of the current baselines (simulates live data)."""
        async with self._lock:
            return {
                "speed_kmh": round(
                    self._baselines["speed_kmh"] + random.uniform(-3.0, 3.0), 1
                ),
                "engine_temp_c": round(
                    self._baselines["engine_temp_c"] + random.uniform(-1.5, 1.5), 1
                ),
                "tire_pressure_psi": round(
                    self._baselines["tire_pressure_psi"] + random.uniform(-0.4, 0.4), 1
                ),
                "engine_rpm": round(
                    self._baselines["engine_rpm"] + random.uniform(-50, 50), 0
                ),
                "oil_pressure_psi": round(
                    self._baselines["oil_pressure_psi"] + random.uniform(-1.0, 1.0), 1
                ),
                "battery_voltage_v": round(
                    self._baselines["battery_voltage_v"] + random.uniform(-0.05, 0.05), 2
                ),
                "tire_pressure_fl_psi": round(
                    self._baselines["tire_pressure_fl_psi"] + random.uniform(-0.4, 0.4), 1
                ),
                "tire_pressure_fr_psi": round(
                    self._baselines["tire_pressure_fr_psi"] + random.uniform(-0.4, 0.4), 1
                ),
                "tire_pressure_rl_psi": round(
                    self._baselines["tire_pressure_rl_psi"] + random.uniform(-0.4, 0.4), 1
                ),
                "tire_pressure_rr_psi": round(
                    self._baselines["tire_pressure_rr_psi"] + random.uniform(-0.4, 0.4), 1
                ),
            }

    async def update(self, parameter: str, value: float) -> bool:
        """Update a single baseline. Returns True if the parameter exists."""
        async with self._lock:
            if parameter not in self._baselines:
                return False
            self._baselines[parameter] = float(value)
            return True

    async def get_baselines(self) -> dict[str, float]:
        """Return the raw baseline values (no noise)."""
        async with self._lock:
            return dict(self._baselines)


# ---------------------------------------------------------------------------
# Vehicle Health Analysis Engine (SDV Diagnostics)
# ---------------------------------------------------------------------------

class VehicleHealthAnalyzer:
    """
    Advanced real-time vehicle health analysis based on 60-second rolling window.
    Uses physics-based algorithms and OBD-II standards for diagnostics.
    
    Physics Standards Reference:
    - Engine Temp: SAE J1349 (90-105°C optimal, 60-130°C extended range)
    - Tire Pressure: DOT TPMS (30-35 PSI optimal, 25-40 PSI acceptable)
    - Speed: OBD-II standard monitoring (0-300 km/h typical)
    - Tire-Speed Physics: Pressure × Speed interaction (nonlinear risk)
    - Temperature-Speed Correlation: Engine temp should increase with sustained speed
    
    Contradiction Detection:
    - High speed (>200 km/h) + Low pressure (<20 PSI) = CRITICAL FAILURE RISK
    - High speed + Cold engine (<60°C) = Sensor malfunction or engine failure
    - Rapid pressure drop + High speed = Tire puncture/blowout imminent
    """

    def __init__(self, window_size: int = 60):
        """Initialize analyzer with 60-second rolling window."""
        self._lock = asyncio.Lock()
        self.window_size = window_size
        
        # Rolling window buffers (FIFO deques)
        self.speed_window: deque = deque(maxlen=window_size)
        self.temp_window: deque = deque(maxlen=window_size)
        self.psi_window: deque = deque(maxlen=window_size)
        self.rpm_window: deque = deque(maxlen=window_size)
        self.oil_pressure_window: deque = deque(maxlen=window_size)
        self.battery_voltage_window: deque = deque(maxlen=window_size)
        self.tire_pressure_fl_window: deque = deque(maxlen=window_size)
        self.tire_pressure_fr_window: deque = deque(maxlen=window_size)
        self.tire_pressure_rl_window: deque = deque(maxlen=window_size)
        self.tire_pressure_rr_window: deque = deque(maxlen=window_size)
        
        # Timestamp tracking
        self.last_update = time.time()
        self.session_start = time.time()
        
        # CSV logging
        self.csv_file = DATA_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()
        
        # Physics constants for tire-speed interaction
        self.TIRE_CRITICAL_SPEED_LOW_PSI = 40  # km/h max safe speed at <20 PSI
        self.TIRE_CRITICAL_SPEED_NORMAL_PSI = 200  # km/h max safe speed at normal PSI
        self.TIRE_BLOWOUT_THRESHOLD_PSI = 15  # PSI below which blowout risk is extreme
        self.ENGINE_TEMP_SPEED_CORRELATION = 0.15  # °C increase per 10 km/h sustained speed
        
        # Stability control - prevent rapid state changes
        self.last_health_score = 0
        self.last_status = "INITIALIZING"
        self.health_score_history: deque = deque(maxlen=3)  # Keep last 3 scores for smoothing
        self.HYSTERESIS_THRESHOLD = 5  # Only change status if score changes by 5+ points
        self.IDLE_TEMP_TOLERANCE = 10  # Extra tolerance at idle (±10°C)

    def _init_csv(self) -> None:
        """Initialize CSV file with headers."""
        try:
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "speed_kmh", "engine_temp_c", "tire_pressure_psi",
                    "engine_rpm", "oil_pressure_psi", "battery_voltage_v",
                    "tire_pressure_fl_psi", "tire_pressure_fr_psi", "tire_pressure_rl_psi", "tire_pressure_rr_psi",
                    "speed_status", "temp_status", "psi_status", "rpm_status", "oil_status", "battery_status",
                    "speed_trend", "temp_trend", "psi_trend",
                    "overall_health", "health_status", "emergency", "contradictions",
                    "tire_speed_risk", "temp_correlation_penalty", "alerts"
                ])
        except Exception as e:
            logger.error(f"Failed to initialize CSV: {e}")

    async def add_reading(self, data: dict[str, float]) -> dict[str, Any]:
        """
        Add a new telemetry reading and return analysis results.
        
        Args:
            data: {"speed_kmh": float, "engine_temp_c": float, "tire_pressure_psi": float,
                   "engine_rpm": float, "oil_pressure_psi": float, "battery_voltage_v": float,
                   "tire_pressure_fl_psi": float, "tire_pressure_fr_psi": float,
                   "tire_pressure_rl_psi": float, "tire_pressure_rr_psi": float}
        
        Returns:
            Analysis results with status, trends, and alerts
        """
        async with self._lock:
            self.speed_window.append(data["speed_kmh"])
            self.temp_window.append(data["engine_temp_c"])
            self.psi_window.append(data["tire_pressure_psi"])
            self.rpm_window.append(data.get("engine_rpm", 1500))
            self.oil_pressure_window.append(data.get("oil_pressure_psi", 45))
            self.battery_voltage_window.append(data.get("battery_voltage_v", 13.8))
            self.tire_pressure_fl_window.append(data.get("tire_pressure_fl_psi", 32))
            self.tire_pressure_fr_window.append(data.get("tire_pressure_fr_psi", 32))
            self.tire_pressure_rl_window.append(data.get("tire_pressure_rl_psi", 32))
            self.tire_pressure_rr_window.append(data.get("tire_pressure_rr_psi", 32))
            self.last_update = time.time()

            # Compute analysis
            analysis = {
                "timestamp": round(time.time(), 3),
                "current_values": data,
                "status": self._compute_status(),
                "trends": self._compute_trends(),
                "alerts": self._generate_alerts(),
                "health_score": self._compute_health_score(),
                "window_size": len(self.speed_window),
            }

            # Log to CSV
            self._log_to_csv(analysis)

            return analysis

    def _compute_status(self) -> dict[str, str]:
        """Determine status (optimal/warning/danger/cold) for each metric."""
        if not self.speed_window or not self.temp_window or not self.psi_window:
            return {
                "speed": "—", "temp": "—", "psi": "—",
                "rpm": "—", "oil": "—", "battery": "—"
            }

        current_speed = self.speed_window[-1]
        current_temp = self.temp_window[-1]
        current_psi = self.psi_window[-1]
        current_rpm = self.rpm_window[-1] if self.rpm_window else 1500
        current_oil = self.oil_pressure_window[-1] if self.oil_pressure_window else 45
        current_battery = self.battery_voltage_window[-1] if self.battery_voltage_window else 13.8

        return {
            "speed": self._speed_status(current_speed),
            "temp": self._temp_status(current_temp),
            "psi": self._psi_status(current_psi),
            "rpm": self._rpm_status(current_rpm),
            "oil": self._oil_pressure_status(current_oil),
            "battery": self._battery_voltage_status(current_battery),
        }

    def _speed_status(self, speed: float) -> str:
        """Classify speed status based on automotive standards."""
        if speed <= 120:
            return "optimal"
        elif speed <= 160:
            return "warning"
        else:
            return "danger"

    def _temp_status(self, temp: float) -> str:
        """
        Classify engine temperature status.
        Reference: SAE J1349, OBD-II standards
        """
        if temp < 60:
            return "cold"
        elif 60 <= temp <= 105:
            return "optimal"
        elif 105 < temp <= 115:
            return "warning"
        else:
            return "danger"

    def _psi_status(self, psi: float) -> str:
        """
        Classify tire pressure status.
        Reference: DOT TPMS standards, tire placard recommendations
        """
        if psi < 25:
            return "danger"
        elif 25 <= psi < 30:
            return "warning"
        elif 30 <= psi <= 35:
            return "optimal"
        elif 35 < psi <= 40:
            return "warning"
        else:
            return "danger"

    def _rpm_status(self, rpm: float) -> str:
        """
        Classify engine RPM status.
        Reference: Sedan specifications (600-1000 idle, 2000-3000 cruising, 6500 redline)
        """
        if rpm < 500:
            return "danger"  # Engine stalled or not running
        elif 600 <= rpm <= 1000:
            return "optimal"  # Idle range
        elif 1000 < rpm <= 3000:
            return "optimal"  # Cruising range
        elif 3000 < rpm <= 5500:
            return "warning"  # High RPM
        elif 5500 < rpm <= 6500:
            return "danger"  # Near redline
        else:
            return "danger"  # Over redline

    def _oil_pressure_status(self, oil_psi: float) -> str:
        """
        Classify oil pressure status.
        Reference: Automotive standards (25-65 PSI optimal, <15 PSI critical)
        """
        if oil_psi < 15:
            return "danger"  # Critical low
        elif 15 <= oil_psi < 25:
            return "warning"  # Low
        elif 25 <= oil_psi <= 65:
            return "optimal"  # Optimal range
        elif 65 < oil_psi <= 75:
            return "warning"  # Slightly high
        else:
            return "danger"  # Dangerously high

    def _battery_voltage_status(self, voltage: float) -> str:
        """
        Classify battery voltage status.
        Reference: Automotive standards (13.5-14.7V running, 12.6V at rest, <12.5V critical)
        """
        if voltage < 12.0:
            return "danger"  # Critical low
        elif 12.0 <= voltage < 12.6:
            return "warning"  # Low
        elif 12.6 <= voltage <= 14.7:
            return "optimal"  # Optimal range
        elif 14.7 < voltage <= 15.5:
            return "warning"  # Slightly high
        else:
            return "danger"  # Dangerously high

    def _compute_trends(self) -> dict[str, dict[str, Any]]:
        """
        Compute trend analysis (direction, rate of change, stability).
        """
        if len(self.speed_window) < 2:
            return {
                "speed": {"direction": "—", "rate": 0, "stability": "—"},
                "temp": {"direction": "—", "rate": 0, "stability": "—"},
                "psi": {"direction": "—", "rate": 0, "stability": "—"},
            }

        return {
            "speed": self._analyze_trend(list(self.speed_window), "speed"),
            "temp": self._analyze_trend(list(self.temp_window), "temp"),
            "psi": self._analyze_trend(list(self.psi_window), "psi"),
        }

    def _analyze_trend(self, window: list[float], metric_type: str) -> dict[str, Any]:
        """
        Analyze trend for a metric.
        Returns: direction (up/down/stable), rate of change, stability score
        """
        if len(window) < 2:
            return {"direction": "—", "rate": 0, "stability": 0}

        # Calculate rate of change (last 10 readings vs previous 10)
        if len(window) >= 20:
            recent_avg = sum(window[-10:]) / 10
            previous_avg = sum(window[-20:-10]) / 10
            rate = round(recent_avg - previous_avg, 2)
        else:
            rate = round(window[-1] - window[0], 2)

        # Determine direction
        if rate > 0.5:
            direction = "↑ increasing"
        elif rate < -0.5:
            direction = "↓ decreasing"
        else:
            direction = "→ stable"

        # Calculate stability (std dev of last 10 readings)
        recent = window[-10:] if len(window) >= 10 else window
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        std_dev = variance ** 0.5
        stability = round(100 - min(std_dev * 10, 100), 1)  # 0-100 score

        return {
            "direction": direction,
            "rate": rate,
            "stability": stability,
        }

    def _generate_alerts(self) -> list[str]:
        """
        Generate diagnostic alerts based on current conditions and physics-based analysis.
        Includes contradiction detection and emergency system failure indicators.
        """
        alerts = []

        if not self.speed_window or not self.temp_window or not self.psi_window:
            return alerts

        current_speed = self.speed_window[-1]
        current_temp = self.temp_window[-1]
        current_psi = self.psi_window[-1]

        # ---- EMERGENCY ALERTS (Contradictions) ----
        contradictions = self._detect_contradictions(current_speed, current_temp, current_psi)
        
        if "CRITICAL_TIRE_FAILURE_RISK" in contradictions:
            alerts.append("🚨 EMERGENCY: TIRE BLOWOUT IMMINENT - Reduce speed immediately!")
        
        if "CRITICAL_ENGINE_SENSOR_FAILURE" in contradictions:
            alerts.append("🚨 EMERGENCY: Engine sensor malfunction or engine failure detected")
        
        if "TIRE_PUNCTURE_RISK" in contradictions:
            alerts.append("⚠️ CRITICAL: Tire puncture risk - Pressure dropping at high speed")
        
        if "TIRE_FLAT_OR_SENSOR_FAILURE" in contradictions:
            alerts.append("🛞 CRITICAL: Tire flat or pressure sensor failure")
        
        if "COOLING_SYSTEM_FAILURE" in contradictions:
            alerts.append("🔥 CRITICAL: Cooling system failure - Engine overheating at low speed")
        
        if "RAPID_TEMP_SPIKE" in contradictions:
            alerts.append("📈 WARNING: Rapid engine temperature spike detected")
        
        if "RAPID_PRESSURE_DROP" in contradictions:
            alerts.append("💨 WARNING: Rapid tire pressure drop - Possible leak")

        # ---- SPEED ALERTS ----
        if current_speed > 200:
            alerts.append("⚠️ EXCESSIVE_SPEED: Vehicle speed exceeds safe limits")
        elif current_speed > 160:
            alerts.append("⚠️ HIGH_SPEED: Reduce speed for safety")

        # ---- TEMPERATURE ALERTS ----
        if current_temp < 50:
            alerts.append("❄️ COLD_ENGINE: Engine not warmed up - Check ignition")
        elif current_temp > 115:
            alerts.append("🔥 OVERHEATING: Engine temperature critical - Pull over safely")
        elif current_temp > 105:
            alerts.append("⚠️ HIGH_TEMP: Engine running hot - Monitor closely")

        # ---- TIRE PRESSURE ALERTS ----
        if current_psi < 15:
            alerts.append("🛞 CRITICAL_PRESSURE: Tire flat or severely under-inflated")
        elif current_psi < 25:
            alerts.append("🛞 LOW_PRESSURE: Tire pressure dangerously low")
        elif current_psi < 30:
            alerts.append("⚠️ UNDER_INFLATED: Tire pressure below optimal")
        elif current_psi > 40:
            alerts.append("⚠️ OVER_INFLATED: Tire pressure above safe range")

        # ---- TREND-BASED ALERTS ----
        if len(self.temp_window) >= 10:
            temp_trend = self._analyze_trend(list(self.temp_window), "temp")
            if temp_trend["rate"] > 2.0:
                alerts.append("📈 RAPID_TEMP_RISE: Engine temperature rising quickly")

        if len(self.psi_window) >= 10:
            psi_trend = self._analyze_trend(list(self.psi_window), "psi")
            if psi_trend["rate"] < -0.5:
                alerts.append("💨 PRESSURE_LEAK: Tire pressure dropping")

        # ---- PHYSICS-BASED ALERTS ----
        tire_speed_risk = self._calculate_tire_speed_risk(current_psi, current_speed)
        if tire_speed_risk > 0.7:
            alerts.append("🚨 TIRE_SPEED_MISMATCH: Tire pressure unsafe for current speed")
        elif tire_speed_risk > 0.4:
            alerts.append("⚠️ TIRE_SPEED_WARNING: Reduce speed or increase tire pressure")

        return alerts

    def _compute_health_score(self) -> dict[str, Any]:
        """
        Compute overall vehicle health score (0-100) using research-based physics algorithms.
        
        Formula (from research):
        Final Score = max(0, 100 - [(P_temp + P_tyre) × M_stress] - P_oil - P_batt)
        
        Where:
        - M_stress = 1.0 + (RPM/MaxRPM)² + (Speed/MaxSpeed)²
        - P_temp = W_temp × (ΔT)² (non-linear temperature penalty)
        - P_tyre = W_tyre × (ΔPressure)² (non-linear tire pressure penalty)
        - P_oil = Oil pressure penalty
        - P_batt = Battery voltage penalty
        
        Returns: Health score (0-100), status, and failure indicators
        """
        if not self.speed_window or not self.temp_window or not self.psi_window:
            return {"score": 0, "status": "INITIALIZING", "emergency": False, "contradictions": []}

        current_speed = self.speed_window[-1]
        current_temp = self.temp_window[-1]
        current_psi = self.psi_window[-1]
        current_rpm = self.rpm_window[-1] if self.rpm_window else 1500
        current_oil = self.oil_pressure_window[-1] if self.oil_pressure_window else 45
        current_battery = self.battery_voltage_window[-1] if self.battery_voltage_window else 13.8
        
        # Get individual tire pressures
        tire_fl = self.tire_pressure_fl_window[-1] if self.tire_pressure_fl_window else 32
        tire_fr = self.tire_pressure_fr_window[-1] if self.tire_pressure_fr_window else 32
        tire_rl = self.tire_pressure_rl_window[-1] if self.tire_pressure_rl_window else 32
        tire_rr = self.tire_pressure_rr_window[-1] if self.tire_pressure_rr_window else 32

        # ---- STEP 1: Detect Critical Contradictions ----
        contradictions = self._detect_contradictions(current_speed, current_temp, current_psi)
        
        # ---- STEP 2: Calculate Stress Multiplier ----
        # M_stress = 1.0 + (RPM/MaxRPM)² + (Speed/MaxSpeed)²
        max_rpm = 6500  # Sedan redline
        max_speed = 300  # km/h
        rpm_factor = (current_rpm / max_rpm) ** 2
        speed_factor = (current_speed / max_speed) ** 2
        stress_multiplier = 1.0 + rpm_factor + speed_factor
        
        # ---- STEP 3: Calculate Non-linear Penalties ----
        # Temperature penalty: P_temp = W_temp × (ΔT)²
        temp_optimal_min, temp_optimal_max = 90, 105
        if current_temp < temp_optimal_min:
            temp_delta = temp_optimal_min - current_temp
        elif current_temp > temp_optimal_max:
            temp_delta = current_temp - temp_optimal_max
        else:
            temp_delta = 0
        
        w_temp = 0.5  # Temperature weight
        temp_penalty = w_temp * (temp_delta ** 2)
        
        # Tire pressure penalty: P_tyre = W_tyre × (ΔPressure)²
        # Use average of all four tires
        avg_tire_pressure = (tire_fl + tire_fr + tire_rl + tire_rr) / 4
        tire_optimal_min, tire_optimal_max = 30, 35
        if avg_tire_pressure < tire_optimal_min:
            tire_delta = tire_optimal_min - avg_tire_pressure
        elif avg_tire_pressure > tire_optimal_max:
            tire_delta = avg_tire_pressure - tire_optimal_max
        else:
            tire_delta = 0
        
        w_tyre = 0.6  # Tire weight
        tire_penalty = w_tyre * (tire_delta ** 2)
        
        # ---- STEP 4: Calculate Oil Pressure Penalty ----
        # Optimal: 25-65 PSI, Critical: <15 PSI
        if current_oil < 15:
            oil_penalty = 40  # Critical
        elif current_oil < 25:
            oil_penalty = 20  # Warning
        elif 25 <= current_oil <= 65:
            oil_penalty = 0  # Optimal
        elif current_oil <= 75:
            oil_penalty = 10  # Slightly high
        else:
            oil_penalty = 30  # Dangerously high
        
        # ---- STEP 5: Calculate Battery Voltage Penalty ----
        # Optimal: 13.5-14.7V running, 12.6V at rest, <12.5V critical
        if current_battery < 12.0:
            battery_penalty = 40  # Critical
        elif current_battery < 12.6:
            battery_penalty = 20  # Warning
        elif 12.6 <= current_battery <= 14.7:
            battery_penalty = 0  # Optimal
        elif current_battery <= 15.5:
            battery_penalty = 10  # Slightly high
        else:
            battery_penalty = 30  # Dangerously high
        
        # ---- STEP 6: Apply Research Formula ----
        # Final Score = max(0, 100 - [(P_temp + P_tyre) × M_stress] - P_oil - P_batt)
        combined_penalty = (temp_penalty + tire_penalty) * stress_multiplier
        raw_score = 100 - combined_penalty - oil_penalty - battery_penalty
        raw_score = round(max(0, min(100, raw_score)), 1)
        
        # ---- STEP 7: Apply Smoothing and Hysteresis ----
        self.health_score_history.append(raw_score)
        smoothed_score = sum(self.health_score_history) / len(self.health_score_history)
        overall_score = round(smoothed_score, 1)
        
        # Apply hysteresis
        score_change = abs(overall_score - self.last_health_score)
        if score_change < self.HYSTERESIS_THRESHOLD and self.last_status != "INITIALIZING":
            overall_score = self.last_health_score
        
        # Determine health status
        is_emergency = len(contradictions) > 0 or stress_multiplier > 2.0
        health_status = self._determine_health_status(overall_score, is_emergency, contradictions)
        
        # Update last values
        self.last_health_score = overall_score
        self.last_status = health_status

        return {
            "score": overall_score,
            "status": health_status,
            "component_scores": {
                "speed": self._calculate_speed_score(current_speed),
                "temperature": self._calculate_temp_score(current_temp, current_speed),
                "tire_pressure": self._calculate_psi_score(current_psi, current_speed),
                "rpm": self._calculate_rpm_score(current_rpm),
                "oil_pressure": self._calculate_oil_pressure_score(current_oil),
                "battery_voltage": self._calculate_battery_voltage_score(current_battery),
            },
            "emergency": is_emergency,
            "contradictions": contradictions,
            "tire_speed_risk": round(self._calculate_tire_speed_risk(current_psi, current_speed) * 100, 1),
            "temp_correlation_penalty": round(temp_penalty, 1),
            "stress_multiplier": round(stress_multiplier, 2),
        }

    def _detect_contradictions(self, speed: float, temp: float, psi: float) -> list[str]:
        """
        Detect physically impossible or dangerous sensor combinations.
        
        Real-world scenarios:
        - High speed + extremely low pressure = tire failure imminent
        - High speed + cold engine = sensor malfunction or engine failure
        - Rapid pressure drop = puncture/leak
        - Temperature spike at low speed = cooling system failure
        """
        contradictions = []
        
        # CRITICAL: High speed + extremely low pressure
        if speed > 200 and psi < 20:
            contradictions.append("CRITICAL_TIRE_FAILURE_RISK")
        
        # CRITICAL: High speed + cold engine (engine not warmed up)
        if speed > 150 and temp < 60:
            contradictions.append("CRITICAL_ENGINE_SENSOR_FAILURE")
        
        # WARNING: Very high speed + moderate pressure drop
        if speed > 180 and psi < 25:
            contradictions.append("TIRE_PUNCTURE_RISK")
        
        # WARNING: Extreme pressure (physically impossible)
        if psi < 5:
            contradictions.append("TIRE_FLAT_OR_SENSOR_FAILURE")
        
        # WARNING: Engine overheating at low speed (cooling system failure)
        if speed < 30 and temp > 115:
            contradictions.append("COOLING_SYSTEM_FAILURE")
        
        # WARNING: Rapid temperature spike (check trend)
        if len(self.temp_window) >= 5:
            recent_temps = list(self.temp_window)[-5:]
            temp_increase = recent_temps[-1] - recent_temps[0]
            if temp_increase > 10:  # 10°C increase in 5 seconds
                contradictions.append("RAPID_TEMP_SPIKE")
        
        # WARNING: Rapid pressure drop (check trend)
        if len(self.psi_window) >= 5:
            recent_psi = list(self.psi_window)[-5:]
            psi_decrease = recent_psi[0] - recent_psi[-1]
            if psi_decrease > 2:  # 2 PSI drop in 5 seconds
                contradictions.append("RAPID_PRESSURE_DROP")
        
        return contradictions

    def _calculate_tire_speed_risk(self, psi: float, speed: float) -> float:
        """
        Calculate tire failure risk using physics-based tire-speed interaction.
        
        Physics: Tire failure risk is nonlinear and multiplicative.
        - At low PSI, tire sidewalls flex excessively
        - At high speed, flexing frequency increases exponentially
        - Combined effect: heat buildup → blowout
        
        Formula: Risk = (1 - PSI/35) × (Speed/300) × interaction_factor
        
        Returns: Risk score (0.0 to 1.0)
        """
        if psi <= 0 or speed < 0:
            return 1.0  # Complete failure
        
        # Normalize PSI (35 PSI is optimal)
        psi_factor = max(0, 1 - (psi / 35))
        
        # Normalize speed (300 km/h is extreme)
        speed_factor = min(1, speed / 300)
        
        # Nonlinear interaction: low PSI + high speed = exponential risk
        interaction_factor = 1.5  # Amplifies combined effect
        
        risk = psi_factor * speed_factor * interaction_factor
        
        # Apply critical thresholds
        if psi < self.TIRE_BLOWOUT_THRESHOLD_PSI:
            risk = min(1.0, risk + 0.5)  # Add critical penalty
        
        if speed > self.TIRE_CRITICAL_SPEED_LOW_PSI and psi < 20:
            risk = min(1.0, risk + 0.3)  # Add high-speed low-pressure penalty
        
        return min(1.0, risk)

    def _check_temp_speed_correlation(self, speed: float, temp: float) -> float:
        """
        Check if engine temperature correlates properly with speed.
        
        Physics: At sustained high speed, engine should warm up.
        - Idle (0-20 km/h): temp should be 80-95°C (with extra tolerance)
        - Moderate (50-100 km/h): temp should be 90-105°C
        - High speed (>150 km/h): temp should be 95-110°C
        
        Anomalies indicate:
        - Cold engine at high speed = sensor failure or engine not running
        - Overheating at low speed = cooling system failure
        
        Returns: Penalty score (0-30)
        """
        penalty = 0
        
        # Expected temperature range based on speed
        if speed < 20:
            # At idle, add extra tolerance to prevent noise-induced instability
            expected_min, expected_max = 70, 95 + self.IDLE_TEMP_TOLERANCE
        elif speed < 100:
            expected_min, expected_max = 85, 105
        else:
            expected_min, expected_max = 90, 110
        
        # Check if temperature is within expected range
        if temp < expected_min:
            # Too cold for current speed
            deviation = expected_min - temp
            penalty = min(30, deviation * 1.5)
        elif temp > expected_max:
            # Too hot for current speed
            deviation = temp - expected_max
            penalty = min(30, deviation * 1.2)
        
        return penalty

    def _calculate_speed_score(self, speed: float) -> float:
        """Calculate speed component health score (0-100)."""
        if speed <= 120:
            return 100
        elif speed <= 160:
            return 80
        elif speed <= 200:
            return 60
        elif speed <= 250:
            return 40
        else:
            return 20

    def _calculate_temp_score(self, temp: float, speed: float) -> float:
        """
        Calculate temperature component health score (0-100).
        Considers both absolute temperature and speed correlation.
        """
        if temp < 50:
            return 30  # Engine not warmed up
        elif 60 <= temp <= 105:
            return 100  # Optimal range
        elif 105 < temp <= 115:
            return 70  # Warning range
        else:
            return 20  # Danger range

    def _calculate_psi_score(self, psi: float, speed: float) -> float:
        """
        Calculate tire pressure component health score (0-100).
        Considers both absolute pressure and speed safety.
        """
        if psi < 5:
            return 0  # Flat tire
        elif psi < 20:
            # Dangerous at any speed, critical at high speed
            if speed > 100:
                return 10
            else:
                return 30
        elif psi < 25:
            return 50  # Below optimal
        elif 30 <= psi <= 35:
            return 100  # Optimal
        elif psi <= 40:
            return 80  # Slightly over
        else:
            return 40  # Over-inflated

    def _calculate_rpm_score(self, rpm: float) -> float:
        """Calculate RPM component health score (0-100)."""
        if rpm < 500:
            return 0  # Engine stalled
        elif 600 <= rpm <= 1000:
            return 100  # Idle optimal
        elif 1000 < rpm <= 3000:
            return 100  # Cruising optimal
        elif 3000 < rpm <= 5500:
            return 80  # High RPM
        elif 5500 < rpm <= 6500:
            return 40  # Near redline
        else:
            return 10  # Over redline

    def _calculate_oil_pressure_score(self, oil_psi: float) -> float:
        """Calculate oil pressure component health score (0-100)."""
        if oil_psi < 15:
            return 0  # Critical
        elif oil_psi < 25:
            return 50  # Low
        elif 25 <= oil_psi <= 65:
            return 100  # Optimal
        elif oil_psi <= 75:
            return 80  # Slightly high
        else:
            return 40  # Dangerously high

    def _calculate_battery_voltage_score(self, voltage: float) -> float:
        """Calculate battery voltage component health score (0-100)."""
        if voltage < 12.0:
            return 0  # Critical
        elif voltage < 12.6:
            return 50  # Low
        elif 12.6 <= voltage <= 14.7:
            return 100  # Optimal
        elif voltage <= 15.5:
            return 80  # Slightly high
        else:
            return 40  # Dangerously high

    def _determine_health_status(self, score: float, is_emergency: bool, contradictions: list[str]) -> str:
        """
        Determine health status with emergency indicators.
        
        Status hierarchy:
        - EMERGENCY: Critical contradictions detected
        - CRITICAL: Score < 30 or dangerous conditions
        - FAIR: Score 30-60
        - GOOD: Score 60-80
        - EXCELLENT: Score 80+
        """
        if is_emergency or "CRITICAL" in str(contradictions):
            return "🚨 EMERGENCY"
        elif score < 30:
            return "🔴 CRITICAL"
        elif score < 60:
            return "🟡 FAIR"
        elif score < 80:
            return "🟢 GOOD"
        else:
            return "✅ EXCELLENT"

    def _log_to_csv(self, analysis: dict[str, Any]) -> None:
        """Log analysis results to CSV file."""
        try:
            with open(self.csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                current_values = analysis["current_values"]
                writer.writerow([
                    analysis["timestamp"],
                    current_values.get("speed_kmh", 0),
                    current_values.get("engine_temp_c", 0),
                    current_values.get("tire_pressure_psi", 0),
                    current_values.get("engine_rpm", 0),
                    current_values.get("oil_pressure_psi", 0),
                    current_values.get("battery_voltage_v", 0),
                    current_values.get("tire_pressure_fl_psi", 0),
                    current_values.get("tire_pressure_fr_psi", 0),
                    current_values.get("tire_pressure_rl_psi", 0),
                    current_values.get("tire_pressure_rr_psi", 0),
                    analysis["status"].get("speed", "—"),
                    analysis["status"].get("temp", "—"),
                    analysis["status"].get("psi", "—"),
                    analysis["status"].get("rpm", "—"),
                    analysis["status"].get("oil", "—"),
                    analysis["status"].get("battery", "—"),
                    analysis["trends"]["speed"]["direction"],
                    analysis["trends"]["temp"]["direction"],
                    analysis["trends"]["psi"]["direction"],
                    analysis["health_score"]["score"],
                    analysis["health_score"]["status"],
                    analysis["health_score"].get("emergency", False),
                    "|".join(analysis["health_score"].get("contradictions", [])) if analysis["health_score"].get("contradictions") else "NONE",
                    analysis["health_score"].get("tire_speed_risk", 0),
                    analysis["health_score"].get("temp_correlation_penalty", 0),
                    "|".join(analysis["alerts"]) if analysis["alerts"] else "NONE",
                ])
        except Exception as e:
            logger.error(f"Failed to log to CSV: {e}")

    async def get_session_summary(self) -> dict[str, Any]:
        """Get summary statistics for current session."""
        async with self._lock:
            if not self.speed_window:
                return {"status": "NO_DATA"}

            return {
                "session_duration": round(time.time() - self.session_start, 1),
                "readings_count": len(self.speed_window),
                "speed": {
                    "current": round(self.speed_window[-1], 1),
                    "avg": round(sum(self.speed_window) / len(self.speed_window), 1),
                    "min": round(min(self.speed_window), 1),
                    "max": round(max(self.speed_window), 1),
                },
                "temperature": {
                    "current": round(self.temp_window[-1], 1),
                    "avg": round(sum(self.temp_window) / len(self.temp_window), 1),
                    "min": round(min(self.temp_window), 1),
                    "max": round(max(self.temp_window), 1),
                },
                "tire_pressure": {
                    "current": round(self.psi_window[-1], 1),
                    "avg": round(sum(self.psi_window) / len(self.psi_window), 1),
                    "min": round(min(self.psi_window), 1),
                    "max": round(max(self.psi_window), 1),
                },
            }




# ---------------------------------------------------------------------------
# Global state & connected-client registry
# ---------------------------------------------------------------------------
state = SimulationState()
connected_clients: set[WebSocket] = set()
analysis_clients: set[WebSocket] = set()
analyzer = VehicleHealthAnalyzer(window_size=60)
ai_analyzer = GeminiVehicleAnalyzer()

# Track AI analysis timing
_ai_analysis_counter = 0
_AI_INTERVAL = 30  # Run AI every 30 seconds (free-tier friendly)

# ---------------------------------------------------------------------------
# Background broadcaster
# ---------------------------------------------------------------------------

async def broadcast_telemetry() -> None:
    """Push a noisy telemetry snapshot to every connected client each second."""
    global _ai_analysis_counter
    while True:
        # Always generate snapshot (for analysis even if no telemetry clients)
        snapshot = await state.get_snapshot()
        
        # Broadcast to telemetry clients
        if connected_clients:
            payload = json.dumps(
                {
                    "type": "telemetry",
                    "timestamp": round(time.time(), 3),
                    "data": snapshot,
                }
            )
            stale: list[WebSocket] = []
            for ws in connected_clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                connected_clients.discard(ws)
                logger.warning("Dropped stale WebSocket client.")
        
        # Always run rule engine analysis
        analysis_result = await analyzer.add_reading(snapshot)
        _ai_analysis_counter += 1
        
        # Run AI analysis every _AI_INTERVAL seconds — only if someone is watching
        ai_diagnosis = None
        if analysis_clients:
            if _ai_analysis_counter % _AI_INTERVAL == 0:
                try:
                    ai_diagnosis = await ai_analyzer.analyze(
                        telemetry=snapshot,
                        rule_analysis=analysis_result,
                    )
                except Exception as e:
                    logger.error(f"AI analysis error: {e}")
                    ai_diagnosis = ai_analyzer.cached_diagnosis
            else:
                # Use cached AI result between calls
                ai_diagnosis = ai_analyzer.cached_diagnosis
        
        # Broadcast to analysis clients with AI data included
        if analysis_clients:
            # Attach AI diagnosis to the analysis payload
            analysis_result["ai_diagnosis"] = ai_diagnosis
            analysis_result["ai_status"] = ai_analyzer.get_status()
            
            analysis_payload = json.dumps(
                {
                    "type": "analysis",
                    "timestamp": analysis_result["timestamp"],
                    "data": analysis_result,
                }
            )
            stale_analysis: list[WebSocket] = []
            for ws in analysis_clients:
                try:
                    await ws.send_text(analysis_payload)
                except Exception:
                    stale_analysis.append(ws)
            for ws in stale_analysis:
                analysis_clients.discard(ws)
                logger.warning("Dropped stale analysis WebSocket client.")
        
        await asyncio.sleep(1)

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the broadcaster on startup; cancel it on shutdown."""
    task = asyncio.create_task(broadcast_telemetry())
    logger.info("🚀  Telemetry broadcaster started.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("🛑  Telemetry broadcaster stopped.")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Automotive Telemetry Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow any front-end origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets (CSS, JS, images)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# REST health-check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ai/status")
async def ai_status() -> dict[str, Any]:
    """Return the AI analyzer status and configuration."""
    return {
        "ai": ai_analyzer.get_status(),
        "rule_engine": "active",
        "hybrid_mode": ai_analyzer.enabled,
    }


@app.get("/baselines")
async def baselines() -> dict[str, Any]:
    """Return the current raw baselines (no noise)."""
    return {"baselines": await state.get_baselines()}

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket) -> None:
    await ws.accept()
    connected_clients.add(ws)
    client_id = id(ws)
    logger.info("Client %s connected. Total clients: %d", client_id, len(connected_clients))

    try:
        while True:
            # Block until we receive a text frame from the client.
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps({"type": "error", "detail": "Invalid JSON."})
                )
                continue

            action = msg.get("action")

            # ---- Handle "update" action ----
            if action == "update":
                param = msg.get("parameter")
                value = msg.get("value")

                if param is None or value is None:
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "detail": "Missing 'parameter' or 'value' field.",
                            }
                        )
                    )
                    continue

                try:
                    value = float(value)
                except (TypeError, ValueError):
                    await ws.send_text(
                        json.dumps(
                            {"type": "error", "detail": f"Invalid value: {value!r}"}
                        )
                    )
                    continue

                ok = await state.update(param, value)
                if ok:
                    logger.info(
                        "Client %s updated %s → %s", client_id, param, value
                    )
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "ack",
                                "detail": f"{param} updated to {value}",
                                "baselines": await state.get_baselines(),
                            }
                        )
                    )
                else:
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "detail": f"Unknown parameter: {param!r}. "
                                f"Valid: speed_kmh, engine_temp_c, tire_pressure_psi, engine_rpm, "
                                f"oil_pressure_psi, battery_voltage_v, tire_pressure_fl_psi, "
                                f"tire_pressure_fr_psi, tire_pressure_rl_psi, tire_pressure_rr_psi",
                            }
                        )
                    )

            # ---- Handle "get_baselines" action ----
            elif action == "get_baselines":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "baselines",
                            "baselines": await state.get_baselines(),
                        }
                    )
                )

            # ---- Unknown action ----
            else:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "detail": f"Unknown action: {action!r}. "
                            f"Supported: 'update', 'get_baselines'",
                        }
                    )
                )

    except WebSocketDisconnect:
        logger.info("Client %s disconnected.", client_id)
    except Exception as exc:
        logger.exception("Unexpected error on client %s: %s", client_id, exc)
    finally:
        connected_clients.discard(ws)
        logger.info("Cleaned up client %s. Total clients: %d", client_id, len(connected_clients))


# ---------------------------------------------------------------------------
# Data Analysis WebSocket endpoint (SDV Diagnostics)
# ---------------------------------------------------------------------------

@app.websocket("/ws/data-analysis")
async def ws_data_analysis(ws: WebSocket) -> None:
    """
    Real-time vehicle health analysis WebSocket.
    Streams analysis results based on 60-second rolling window.
    """
    await ws.accept()
    analysis_clients.add(ws)
    client_id = id(ws)
    logger.info("Analysis client %s connected. Total: %d", client_id, len(analysis_clients))

    try:
        # Keep connection alive and handle incoming messages
        # The broadcaster will send data to this client
        while True:
            try:
                # Wait for client messages with timeout
                # This allows the connection to stay open while broadcaster sends data
                raw = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_text(
                        json.dumps({"type": "error", "detail": "Invalid JSON."})
                    )
                    continue

                action = msg.get("action")

                # ---- Handle "get_summary" action ----
                if action == "get_summary":
                    summary = await analyzer.get_session_summary()
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "summary",
                                "data": summary,
                            }
                        )
                    )

                # ---- Handle "force_ai_analysis" action ----
                elif action == "force_ai_analysis":
                    # Force an immediate AI analysis (bypasses rate limiting)
                    snapshot = await state.get_snapshot()
                    rule_result = await analyzer.add_reading(snapshot)
                    ai_result = await ai_analyzer.analyze(
                        telemetry=snapshot,
                        rule_analysis=rule_result,
                        force=True,
                    )
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "ai_diagnosis",
                                "data": ai_result,
                            }
                        )
                    )

                # ---- Unknown action ----
                else:
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "detail": f"Unknown action: {action!r}. "
                                f"Supported: 'get_summary', 'force_ai_analysis'",
                            }
                        )
                    )
            except asyncio.TimeoutError:
                # Timeout is normal - just keep connection alive
                # Broadcaster will send data periodically
                continue

    except WebSocketDisconnect:
        logger.info("Analysis client %s disconnected.", client_id)
    except Exception as exc:
        logger.exception("Unexpected error on analysis client %s: %s", client_id, exc)
    finally:
        analysis_clients.discard(ws)
        logger.info("Cleaned up analysis client %s. Total: %d", client_id, len(analysis_clients))


# ---------------------------------------------------------------------------
# Analysis Dashboard page (serves at /analysis)
# ---------------------------------------------------------------------------

@app.get("/analysis")
async def analysis_dashboard():
    """Serve the vehicle health analysis dashboard."""
    return FileResponse(STATIC_DIR / "analysis.html", media_type="text/html")


# ---------------------------------------------------------------------------
# Dashboard page (serves at /)
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    """Serve the premium telemetry dashboard."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")
