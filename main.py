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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    Real-time vehicle health analysis based on 60-second rolling window.
    Uses automotive industry standards for diagnostics thresholds.
    
    Standards Reference:
    - Engine Temp: SAE J1349 (80-110°C normal, 60-130°C extended range)
    - Tire Pressure: DOT TPMS (30-35 PSI optimal, 25-40 PSI acceptable)
    - Speed: OBD-II standard monitoring
    """

    def __init__(self, window_size: int = 60):
        """Initialize analyzer with 60-second rolling window."""
        self._lock = asyncio.Lock()
        self.window_size = window_size
        
        # Rolling window buffers (FIFO deques)
        self.speed_window: deque = deque(maxlen=window_size)
        self.temp_window: deque = deque(maxlen=window_size)
        self.psi_window: deque = deque(maxlen=window_size)
        
        # Timestamp tracking
        self.last_update = time.time()
        self.session_start = time.time()
        
        # CSV logging
        self.csv_file = DATA_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()

    def _init_csv(self) -> None:
        """Initialize CSV file with headers."""
        try:
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "speed_kmh", "engine_temp_c", "tire_pressure_psi",
                    "speed_status", "temp_status", "psi_status",
                    "speed_trend", "temp_trend", "psi_trend",
                    "overall_health", "alerts"
                ])
        except Exception as e:
            logger.error(f"Failed to initialize CSV: {e}")

    async def add_reading(self, data: dict[str, float]) -> dict[str, Any]:
        """
        Add a new telemetry reading and return analysis results.
        
        Args:
            data: {"speed_kmh": float, "engine_temp_c": float, "tire_pressure_psi": float}
        
        Returns:
            Analysis results with status, trends, and alerts
        """
        async with self._lock:
            self.speed_window.append(data["speed_kmh"])
            self.temp_window.append(data["engine_temp_c"])
            self.psi_window.append(data["tire_pressure_psi"])
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
            return {"speed": "—", "temp": "—", "psi": "—"}

        current_speed = self.speed_window[-1]
        current_temp = self.temp_window[-1]
        current_psi = self.psi_window[-1]

        return {
            "speed": self._speed_status(current_speed),
            "temp": self._temp_status(current_temp),
            "psi": self._psi_status(current_psi),
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
        """Generate diagnostic alerts based on current conditions."""
        alerts = []

        if not self.speed_window or not self.temp_window or not self.psi_window:
            return alerts

        current_speed = self.speed_window[-1]
        current_temp = self.temp_window[-1]
        current_psi = self.psi_window[-1]

        # Speed alerts
        if current_speed > 160:
            alerts.append("⚠️ EXCESSIVE_SPEED: Vehicle speed exceeds safe limits")

        # Temperature alerts
        if current_temp < 50:
            alerts.append("❄️ COLD_ENGINE: Engine not warmed up properly")
        elif current_temp > 115:
            alerts.append("🔥 OVERHEATING: Engine temperature critical")
        elif current_temp > 105:
            alerts.append("⚠️ HIGH_TEMP: Engine running hot")

        # Tire pressure alerts
        if current_psi < 25:
            alerts.append("🛞 LOW_PRESSURE: Tire pressure dangerously low")
        elif current_psi < 30:
            alerts.append("⚠️ UNDER_INFLATED: Tire pressure below optimal")
        elif current_psi > 40:
            alerts.append("⚠️ OVER_INFLATED: Tire pressure above safe range")

        # Trend-based alerts
        if len(self.temp_window) >= 10:
            temp_trend = self._analyze_trend(list(self.temp_window), "temp")
            if temp_trend["rate"] > 2.0:
                alerts.append("📈 RAPID_TEMP_RISE: Engine temperature rising quickly")

        if len(self.psi_window) >= 10:
            psi_trend = self._analyze_trend(list(self.psi_window), "psi")
            if psi_trend["rate"] < -0.5:
                alerts.append("💨 PRESSURE_LEAK: Tire pressure dropping")

        return alerts

    def _compute_health_score(self) -> dict[str, Any]:
        """
        Compute overall vehicle health score (0-100).
        Based on weighted average of all metrics.
        """
        if not self.speed_window or not self.temp_window or not self.psi_window:
            return {"score": 0, "status": "INITIALIZING"}

        # Get status scores
        speed_score = 100 if self._speed_status(self.speed_window[-1]) == "optimal" else 70
        temp_score = 100 if self._temp_status(self.temp_window[-1]) == "optimal" else 70
        psi_score = 100 if self._psi_status(self.psi_window[-1]) == "optimal" else 70

        # Weighted average (equal weights for now)
        overall_score = round((speed_score + temp_score + psi_score) / 3, 1)

        # Determine health status
        if overall_score >= 90:
            health_status = "EXCELLENT"
        elif overall_score >= 75:
            health_status = "GOOD"
        elif overall_score >= 60:
            health_status = "FAIR"
        else:
            health_status = "CRITICAL"

        return {
            "score": overall_score,
            "status": health_status,
            "component_scores": {
                "speed": speed_score,
                "temperature": temp_score,
                "tire_pressure": psi_score,
            },
        }

    def _log_to_csv(self, analysis: dict[str, Any]) -> None:
        """Log analysis results to CSV file."""
        try:
            with open(self.csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    analysis["timestamp"],
                    analysis["current_values"]["speed_kmh"],
                    analysis["current_values"]["engine_temp_c"],
                    analysis["current_values"]["tire_pressure_psi"],
                    analysis["status"]["speed"],
                    analysis["status"]["temp"],
                    analysis["status"]["psi"],
                    analysis["trends"]["speed"]["direction"],
                    analysis["trends"]["temp"]["direction"],
                    analysis["trends"]["psi"]["direction"],
                    analysis["health_score"]["status"],
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

# ---------------------------------------------------------------------------
# Background broadcaster
# ---------------------------------------------------------------------------

async def broadcast_telemetry() -> None:
    """Push a noisy telemetry snapshot to every connected client each second."""
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
        
        # Always analyze and broadcast to analysis clients
        # (analysis runs continuously for real-time diagnostics)
        if analysis_clients:
            analysis_result = await analyzer.add_reading(snapshot)
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
        else:
            # Even if no analysis clients connected, keep analyzer running
            # so data is ready when they connect
            await analyzer.add_reading(snapshot)
        
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
                                f"Valid: speed_kmh, engine_temp_c, tire_pressure_psi",
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

                # ---- Unknown action ----
                else:
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "detail": f"Unknown action: {action!r}. "
                                f"Supported: 'get_summary'",
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
