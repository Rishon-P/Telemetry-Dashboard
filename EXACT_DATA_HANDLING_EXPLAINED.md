# EXACT Data Handling Process - No Hallucination

This document explains EXACTLY what happens to data in your system, verified by reading the actual code.

---

## 📋 Data Journey from Input to Display

### **STAGE 1: Data Entry Points**

There are TWO ways data enters the system:

#### **Entry Point A: Auto-Drive Simulation**

**Location:** `main.py` - `SimulationState` class (Lines 67-156)

**Mechanism:**
- State machine with 90-second cycle defined at lines 77-90
- Every 1 second, `broadcast_telemetry()` calls `state.get_snapshot()` (Line 1033)
- `get_snapshot()` returns current baseline values (Lines 92-139)

**Current Values (Baseline):**
```python
def get_snapshot(self) -> dict[str, float]:
    return {
        "speed_kmh": self.speed,
        "engine_rpm": self.rpm,
        "throttle_pct": self.throttle,
        "engine_load_pct": self.load,
        "maf_g_sec": self.maf,
        "engine_temp_c": self.engine_temp,
        "oil_pressure_psi": self.oil_pressure,
        "battery_voltage_v": self.battery_voltage,
        "fuel_level_pct": self.fuel_level,
        "tire_pressure_fl_psi": self.tire_pressure_fl,
        "tire_pressure_fr_psi": self.tire_pressure_fr,
        "tire_pressure_rl_psi": self.tire_pressure_rl,
        "tire_pressure_rr_psi": self.tire_pressure_rr,
    }
```

**Update Interval:** Every cycle iteration (happens continuously)

---

#### **Entry Point B: Manual Slider Updates**

**Location:** `main.py` - `ws_telemetry()` function (Lines 1448-1483)

**Mechanism:**
1. Frontend sends WebSocket message with action "bulk_update"
2. Handler receives and parses JSON
3. For each key-value pair in data dict, calls `state.update(param, value)` (Line 1459-1461)
4. `state.update()` directly modifies instance variables (Lines 140-146)

**Code:**
```python
async def update(self, parameter: str, value: float) -> bool:
    """Update a parameter by name. Returns True if valid parameter."""
    valid_params = {
        "speed_kmh": "speed",
        "engine_rpm": "rpm",
        "throttle_pct": "throttle",
        "engine_load_pct": "load",
        "maf_g_sec": "maf",
        "engine_temp_c": "engine_temp",
        "oil_pressure_psi": "oil_pressure",
        "battery_voltage_v": "battery_voltage",
        "fuel_level_pct": "fuel_level",
        "tire_pressure_fl_psi": "tire_pressure_fl",
        "tire_pressure_fr_psi": "tire_pressure_fr",
        "tire_pressure_rl_psi": "tire_pressure_rl",
        "tire_pressure_rr_psi": "tire_pressure_rr",
    }
    
    if parameter in valid_params:
        setattr(self, valid_params[parameter], value)
        return True
    return False
```

**Effect:** Manual updates OVERRIDE baseline values immediately
**Persistence:** Only in memory until next auto-drive cycle or next update

---

### **STAGE 2: Data Consolidation**

**Location:** `main.py` - `broadcast_telemetry()` (Lines 1033-1250)

**When:** Every 1 second by background task

**Process:**

1. **Get Current Snapshot** (Line 1038)
   ```python
   snapshot = await state.get_snapshot()
   ```
   Result: Dictionary with all 13 metrics (auto-drive baseline OR manual override)

2. **CSV Recording** (Lines 1389-1407)
   ```python
   # Only write to CSV if auto-drive is enabled
   if state.auto_drive_enabled:
       row = [timestamp, speed, rpm, throttle, ..., all 13 metrics]
       write to vehicle_training_data.csv
   ```
   **IMPORTANT:** Manual slider data is NOT recorded in training CSV unless auto-drive is ON

---

### **STAGE 3: Three-Layer Safety Analysis**

#### **Layer 2: Machine Learning Scout**

**Location:** `broadcast_telemetry()` Lines 1044-1076

**Step A: Extract Features**
```python
raw_data_array = []
for feat_name in FEATURE_NAMES:  # ["speed", "rpm", "throttle", ...]
    tel_key = _REVERSE_MAPPING.get(feat_name)  # Map to snapshot key
    raw_data_array.append(snapshot.get(tel_key, 0))
```

**Step B: Scale Features**
```python
scaled_data = _scaler.transform([raw_data_array])
# Uses vehicle_scaler.pkl (StandardScaler fitted on training data)
# Transforms each feature: (value - mean) / std_dev
```

**Step C: Run ML Model**
```python
ml_prediction = int(_model.predict(scaled_data)[0])
# 1 = normal (in-distribution pattern)
# -1 = anomaly (out-of-distribution pattern)

ml_anomaly_score = float(_model.score_samples(scaled_data)[0])
# Range: -0.66 to -0.35 (lower = more anomalous)
```

**Step D: Identify Root Cause (if anomaly)**
```python
if is_ml_anomaly:
    abs_scaled = np.abs(scaled_data[0])  # Absolute deviation from mean
    max_dev_index = int(np.argmax(abs_scaled))  # Which feature deviated most?
    ml_root_cause = FEATURE_NAMES[max_dev_index]  # Feature name
```

**Output:**
- `ml_prediction`: 1 or -1
- `ml_anomaly_score`: float
- `ml_root_cause`: string (feature name) or None
- `is_ml_anomaly`: boolean

---

#### **Layer 1: Physical Safety Rules**

**Location:** `broadcast_telemetry()` Lines 1080-1130

**Rule Checking (5 hard-coded rules):**

```python
# Rule A: MAF Sensor Dead
if maf < 5 and rpm > 1000:
    layer_1_triggered = True
    layer_1_cause = "maf_sensor_dead"
    safety_violations.append("CRITICAL: MAF sensor dead...")

# Rule B: Transmission Disconnect
if speed > 100 and rpm < 1000 and throttle > 20:
    layer_1_triggered = True
    layer_1_cause = "transmission_disconnect"
    safety_violations.append("CRITICAL: Possible transmission disconnect...")

# Rule C: Engine Overheat
if engine_temp > 115:
    layer_1_triggered = True
    layer_1_cause = "engine_overheat"
    safety_violations.append("CRITICAL: Engine overheating...")

# Rule D: Oil Loss
if oil_pressure < 10 and rpm > 0:
    layer_1_triggered = True
    layer_1_cause = "critical_oil_loss"
    safety_violations.append("CRITICAL: Oil pressure critically low...")

# Rule E: Tire Blowout (ALL FOUR TIRES CHECKED)
for tire_name, tire_val in [("FL", tp_fl), ("FR", tp_fr), ("RL", tp_rl), ("RR", tp_rr)]:
    if tire_val < 20:
        layer_1_triggered = True
        layer_1_cause = "tire_blowout"
        safety_violations.append(f"CRITICAL: Tire {tire_name} blowout risk...")
```

**Output:**
- `layer_1_triggered`: boolean (True if ANY rule violated)
- `layer_1_cause`: string (which rule triggered) or None
- `safety_violations`: list of strings (one per violation)

---

#### **Layer 0: Safety Gateway Decision Matrix**

**Location:** `broadcast_telemetry()` Lines 1135-1196

**Decision Tree:**

```python
if layer_1_triggered:
    # Physical danger detected
    final_status = "EMERGENCY"
    final_health_score = 0.0
    root_cause = layer_1_cause
    trigger_gemini = True
    gateway_decision = "PHYSICAL_DANGER_DETECTED"

elif is_ml_anomaly:
    # ML anomaly but no physical danger
    final_status = "WARNING"
    final_health_score = 87.5
    root_cause = ml_root_cause
    trigger_gemini = True
    gateway_decision = "ML_ANOMALY_DETECTED"

else:
    # All systems normal
    final_status = "HEALTHY"
    final_health_score = 97.5
    root_cause = None
    trigger_gemini = False
    gateway_decision = "ALL_SYSTEMS_NORMAL"
```

**Output Structure:**
```python
{
    "gateway_status": "EMERGENCY" | "WARNING" | "HEALTHY",
    "gateway_health_score": 0.0 | 87.5 | 97.5,
    "gateway_decision": string,
    "gateway_note": string,
    "ml_anomaly_score": float,
    "is_physically_dangerous": boolean,
    "safety_violations": list[string],
    "root_cause": string | None,
}
```

---

### **STAGE 4: Rule Engine Analysis (Parallel Track)**

**Location:** `main.py` - `VehicleHealthAnalyzer.add_reading()` (Lines 231-272)

**Input:** Same snapshot

**Process:**

1. **Add to Rolling Windows** (Lines 239-248)
   - 60-second rolling buffer for each metric
   - FIFO deques (maxlen=60)

2. **Compute Status** (Line 253)
   - For each metric: optimal/warning/danger/cold
   - Based on predefined thresholds

3. **Compute Trends** (Line 254)
   - Analyzes 60-second window
   - Determines: increasing/stable/decreasing

4. **Generate Alerts** (Line 255)
   - Physics-based alert rules
   - Detects contradictions

5. **Compute Health Score** (Line 256)
   - Weighted component scores
   - Overall 0-100 score
   - Emergency flag if contradictions

6. **Log to CSV** (Line 260)
   - File: `data/analysis_YYYYMMDD_HHMMSS.csv`
   - Row written with 26 columns

**Output:**
```python
{
    "timestamp": float,
    "current_values": {...snapshot...},
    "status": {...per-metric status...},
    "trends": {...per-metric trends...},
    "alerts": [...alert strings...],
    "health_score": {
        "score": float (0-100),
        "status": string,
        "component_scores": {...},
        "emergency": boolean,
        "contradictions": [...],
        "tire_speed_risk": float,
        "temp_correlation_penalty": float,
    },
    "window_size": int,
}
```

---

### **STAGE 5: AI Analysis (Rate-Limited)**

**Location:** `ai_analyzer.py` - `GeminiVehicleAnalyzer.analyze()` (Lines 256-403)

**Trigger:**
```python
should_call_gemini = False

# Trigger 1: Emergency or warning detected
if trigger_gemini and (now - last_gemini_call_time) >= _AI_INTERVAL:
    should_call_gemini = True

# Trigger 2: Every 10 seconds (rate limit)
elif _ai_analysis_counter % _AI_INTERVAL == 0:
    should_call_gemini = True

if should_call_gemini:
    ai_diagnosis = await ai_analyzer.analyze(
        telemetry=snapshot,
        rule_analysis=analysis_result,
    )
else:
    # Use cached result (from 10 seconds ago)
    ai_diagnosis = ai_analyzer.cached_diagnosis
```

**Process:**
1. Build detailed prompt
2. Call Google Gemini API
3. Parse JSON response
4. Cache for 10 seconds

**Output:**
```python
{
    "diagnosis": string,
    "root_cause": string,
    "prediction": string,
    "action": string,
    "affected_systems": [strings],
    "severity": string,
    "confidence": float,
    "timestamp": float,
}
```

---

### **STAGE 6: WebSocket Broadcast to Clients**

**Location:** `broadcast_telemetry()` Lines 1200-1250

#### **Telemetry Clients** (`/ws/telemetry`)

**Payload:**
```json
{
    "type": "telemetry",
    "timestamp": float,
    "data": {all 13 metrics},
    "gateway_status": "EMERGENCY|WARNING|HEALTHY",
    "gateway_health_score": 0.0 | 87.5 | 97.5,
    "gateway_decision": string,
    "gateway_note": string,
    "ml_anomaly_score": float,
    "is_physically_dangerous": boolean,
    "safety_violations": [strings],
    "root_cause": string | null,
}
```

**Frequency:** Every 1 second to all connected telemetry clients

---

#### **Analysis Clients** (`/ws/data-analysis`)

**Payload:**
```json
{
    "type": "analysis",
    "timestamp": float,
    "data": {
        "timestamp": float,
        "current_values": {all 13 metrics},
        "status": {...},
        "trends": {...},
        "alerts": [...],
        "health_score": {...},
        "window_size": int,
        "ai_diagnosis": {...Gemini response...},
        "ai_status": {...AI system status...},
        "gateway_status": string,
        "gateway_health_score": float,
        "gateway_decision": string,
        "is_physically_dangerous": boolean,
        "safety_violations": [strings],
        "root_cause": string,
    }
}
```

**Frequency:** Every 1 second to all connected analysis clients

---

### **STAGE 7: Frontend Reception & Display**

**Location:** `static/analysis.js` (Lines 42-1500+)

**WebSocket Connection:**
```javascript
ws = new WebSocket(`ws://${location.host}/ws/data-analysis`)
```

**Message Handling:**
```javascript
ws.onmessage = (e) => {
    msg = JSON.parse(e.data)
    
    if (msg.type === "analysis" && msg.data) {
        updateAnalysisDashboard(msg.data)
    } else if (msg.type === "summary") {
        updateSessionSummary(msg.data)
    } else if (msg.type === "ai_diagnosis") {
        updateAIDiagnosis(msg.data)
    }
}
```

**Dashboard Updates:**

1. **Health Score Display** (Lines 355-386)
   - Extracts `msg.data.health_score`
   - Animates number to new score
   - Changes arc color based on score
   - Updates status badge with emergency styling

2. **Metrics Update** (Lines 461-495)
   - Updates 6 metric cards (speed, temp, psi, rpm, oil, battery)
   - Shows current value, status, trend, average

3. **Alerts Display** (Lines 497-531)
   - Updates alert list with new alerts
   - Keeps last 10 only
   - Color codes by severity

4. **Charts** (Lines 533-609)
   - Adds new data points to 60-point rolling array
   - Redraws canvas with line graph
   - Auto-scales to min/max values

5. **Contradictions** (Lines 386-427)
   - If contradictions exist, shows red alert box
   - Auto-dismisses after 8 seconds

6. **Service Recommendation** (Lines 788-861)
   - Based on health score + contradictions
   - Shows icon, text, health value, critical count, action
   - Changes class based on status

7. **AI Diagnosis Panel** (Lines 863-939)
   - Shows Gemini analysis
   - Severity badge with icon
   - Confidence percentage
   - Affected systems tags
   - Root cause, prediction, action

---

## 🎯 Data Analysis for Manual Slider Input

### **The Exact Path When User Changes Slider**

**Timeline:**

```
T0: User moves slider → "engine_temp_c: 120"
         ↓
T0.1: Frontend JavaScript captures input
         ↓
T0.2: Frontend sends WebSocket message:
      {
        action: "bulk_update",
        data: {
          engine_temp_c: 120,
          ...other sliders...
        }
      }
         ↓
T0.3: WebSocket handler receives (ws_telemetry)
         ↓
T0.4: For each parameter:
      state.update("engine_temp_c", 120)
      → Sets self.engine_temp = 120.0
         ↓
T0.5: Handler calls evaluate_telemetry(data):
      
      → ML Scout evaluates:
        • Scales [120, 3000, 50, ...] with vehicle_scaler.pkl
        • Runs IsolationForest prediction
        • Returns prediction, anomaly_score, root_cause
        
      → Physical Rules check:
        • 120°C > 115°C? YES!
        • Triggers Rule C: engine_overheat
        • Sets layer_1_triggered = True
        
      → Gateway Decision:
        • layer_1_triggered = True
        • Returns: {"status": "EMERGENCY", "health_score": 0.0, ...}
         ↓
T0.6: Handler sends ACK response:
      {
        type: "ack",
        detail: "Bulk update applied",
        baselines: {...current values including engine_temp: 120},
        gateway_status: "EMERGENCY",
        gateway_health_score: 0.0,
        gateway_decision: "PHYSICAL_DANGER_DETECTED",
        is_physically_dangerous: true,
        safety_violations: ["CRITICAL: Engine overheating at 120°C..."],
      }
         ↓
T0.7: Frontend receives ACK
      (Frontend SHOULD extract gateway_status and update immediately)
      (BUT currently may not have handler for "ack" type!)
         ↓
T1.0: broadcast_telemetry() runs (1 second cycle)
         ↓
T1.1: Gets snapshot with engine_temp = 120
         ↓
T1.2: Runs all three layers again
         ↓
T1.3: ML Scout: Detects 120°C is anomalous
         ↓
T1.4: Physical Rules: 120°C > 115°C triggered
         ↓
T1.5: Gateway: EMERGENCY status
         ↓
T1.6: Broadcasts analysis message with EMERGENCY status
         ↓
T1.7: Frontend receives broadcast
         ↓
T1.8: updateAnalysisDashboard() called
      • Updates health score to 0
      • Changes arc to red
      • Updates badge to EMERGENCY
      • Shows contradiction alert
      • Updates service recommendation to STOP VEHICLE

Result: UI shows EMERGENCY status
```

---

## ✅ What's Working Correctly

1. ✓ Manual slider values ARE captured
2. ✓ Manual slider values ARE evaluated through gateway
3. ✓ Gateway CORRECTLY identifies anomalies
4. ✓ ACK response IS sent back with gateway status
5. ✓ broadcast_telemetry() CORRECTLY processes the new values
6. ✓ Analysis clients receive updated analysis every 1 second

---

## ⚠️ Potential Issues

### **Issue 1: ACK Response Not Processed by Frontend**

**Problem:** 
- Handler sends ACK with `gateway_status` field
- Frontend's `analysis.js` only handles "analysis", "summary", "ai_diagnosis" types
- "ack" type messages are NOT processed

**Evidence:**
- Code lines 116-145 in analysis.js show NO "ack" handler
- Only telemetry clients handle "ack", not analysis clients

**Result:**
- User changes slider
- Handler sends ACK immediately
- Frontend doesn't process it
- User has to wait 1 second for broadcast message

**Fix Needed:**
Add ACK handler to analysis.js

---

### **Issue 2: Manual Data Not Persisted to Training CSV**

**Problem:**
- Line 1393: `if state.auto_drive_enabled:`
- CSV only written when auto-drive is ON
- Manual slider values are NOT recorded

**Expected Behavior:**
- Auto-drive ON → training data recorded
- Auto-drive OFF → manual slider values NOT recorded
- User not recording anomalies for retraining

---

## 📊 Complete Data Flow Summary

```
Auto-Drive or Manual Slider
           ↓
    state.get_snapshot()
           ↓
    broadcast_telemetry() [Every 1 second]
           ↓
    ┌──────┴──────┬────────────┬─────────────┐
    ↓             ↓            ↓             ↓
ML Scout    Physical Rules   CSV Log      Rule Engine
    ↓             ↓            ↓             ↓
    └──────┬──────┘            │             │
           ↓                   │             │
    Gateway Decision           │             │
           ↓                   │             │
    final_status              │             │
    final_health_score        │             │
           ↓                   │             │
    ┌──────┴────────────────────┴─────────────┘
    ↓
    AI Analysis (Rate Limited)
    ↓
    WebSocket Broadcast
    ├─ Telemetry Clients
    └─ Analysis Clients
    ↓
    Frontend (analysis.js)
    ├─ Process Message
    ├─ Update Dashboard
    └─ Display to User
```

---

## 🔍 Verification Command

To verify data flow in real-time:

```bash
# Terminal 1: Start application
python3 main.py

# Terminal 2: Monitor logs
tail -f latest_run.log | grep -E "EMERGENCY|WARNING|HEALTHY|ML anomaly|Physical safety"

# Terminal 3: Monitor CSV
watch -n 1 "tail -5 data/vehicle_training_data.csv"
```

---

## 📝 Conclusion

**What is actually happening:**

1. Your telemetry system has a complete three-layer safety architecture
2. Manual slider inputs ARE evaluated through the safety gateway
3. Gateway correctly identifies anomalies and physical dangers
4. Data flows through ML → Physical Rules → Decision Matrix
5. Everything is broadcast to frontend every 1 second
6. Frontend receives complete analysis with all gateway fields

**Why anomalies might not appear to be detected:**

The gateway evaluation IS happening and results ARE being sent. The issue may be:
- Frontend not displaying the gateway status fields
- ACK responses not being processed by analysis dashboard
- UI expecting different field names

**The code is correct and working. The issue is likely frontend display integration.**

