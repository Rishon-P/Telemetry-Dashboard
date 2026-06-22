# Complete Data Flow Analysis for Telemetry Dashboard Analysis Dashboard

## 📊 System Architecture Overview

The telemetry dashboard processes vehicle data through multiple layers, from raw simulation data to final analysis visualization. Here's the exact flow:

---

## 🔄 Data Flow Layers

### **LAYER 0: Data Simulation (Backend)**

**File:** `main.py` - `SimulationState` class

**Source:** 
- Auto-drive state machine (90-second cycle) generates baseline vehicle data
- Manual slider updates override baseline values
- Both sources converge at `state.get_snapshot()`

**Data Generated:**
```python
{
    "speed_kmh": float,              # 0-130 km/h
    "engine_rpm": float,             # 800-4000 RPM
    "throttle_pct": float,           # 0-100%
    "engine_load_pct": float,        # 0-100%
    "maf_g_sec": float,              # g/sec
    "engine_temp_c": float,          # 40-120°C
    "oil_pressure_psi": float,       # PSI
    "battery_voltage_v": float,      # 12-14.5V
    "fuel_level_pct": float,         # 0-100%
    "tire_pressure_fl_psi": float,   # 32 PSI (each tire)
    "tire_pressure_fr_psi": float,
    "tire_pressure_rl_psi": float,
    "tire_pressure_rr_psi": float
}
```

**Update Frequency:** Every 1 second via `broadcast_telemetry()` background task

---

### **LAYER 1: Safety Gateway Evaluation (Backend)**

**File:** `main.py` - `broadcast_telemetry()` function (Lines 1033-1250)
**Safety Logic:** `safety_gateway.py` - Three-layer evaluation

#### **Step 1: Layer 2 - Machine Learning Scout (Anomaly Detection)**

**Inputs:** 13 vehicle metrics from snapshot

**Process:**
1. Extract features in strict order:
   - Feature names: `["speed", "rpm", "throttle", "engine_load", "maf", "engine_temp", "oil_pressure", "battery_voltage", "fuel_level", "tp_fl", "tp_fr", "tp_rl", "tp_rr"]`
   - Map telemetry keys to features using `_REVERSE_MAPPING`

2. Normalize using `vehicle_scaler.pkl` (StandardScaler)
   ```python
   scaled_data = _scaler.transform([raw_data_array])
   ```

3. Run IsolationForest model (`vehicle_anomaly_model.pkl`)
   ```python
   ml_prediction = _model.predict(scaled_data)[0]  # 1 (normal) or -1 (anomaly)
   ml_anomaly_score = _model.score_samples(scaled_data)[0]  # -0.66 to -0.35
   ```

4. Local XAI (Z-Score deviation) identifies root cause:
   ```python
   abs_scaled = np.abs(scaled_data[0])
   max_dev_index = np.argmax(abs_scaled)
   ml_root_cause = FEATURE_NAMES[max_dev_index]  # Most deviant feature
   ```

**Output:**
- `ml_prediction`: 1 or -1
- `ml_anomaly_score`: float (lower = more anomalous)
- `ml_root_cause`: string (sensor name if anomaly detected)
- `is_ml_anomaly`: boolean

---

#### **Step 2: Layer 1 - Hard-Coded Safety Boundaries**

**Inputs:** Raw snapshot values

**Critical Thresholds:**
```
Rule A: MAF Sensor Dead
  - Condition: maf < 5 g/s AND rpm > 1000
  - Result: CRITICAL

Rule B: Transmission Disconnect
  - Condition: speed > 100 km/h AND rpm < 1000 AND throttle > 20%
  - Result: CRITICAL

Rule C: Engine Overheat
  - Condition: engine_temp > 115°C
  - Result: CRITICAL

Rule D: Critical Oil Loss
  - Condition: oil_pressure < 10 PSI AND rpm > 0
  - Result: CRITICAL

Rule E: Tire Blowout
  - Condition: ANY tire_pressure < 20 PSI
  - Result: CRITICAL (one violation per tire)
```

**Output:**
- `layer_1_triggered`: boolean (True if ANY rule violated)
- `layer_1_cause`: string (which rule triggered)
- `safety_violations`: list[string] (human-readable messages)

---

#### **Step 3: Safety Gateway Decision Matrix**

**Logic:**
```python
if layer_1_triggered:
    # Physical danger detected - HIGHEST PRIORITY
    final_status = "EMERGENCY"
    final_health_score = 0.0
    trigger_gemini = True
    gateway_decision = "PHYSICAL_DANGER_DETECTED"

elif is_ml_anomaly:
    # ML anomaly but physically safe
    final_status = "WARNING"
    final_health_score = 87.5
    trigger_gemini = True
    gateway_decision = "ML_ANOMALY_DETECTED"

else:
    # All systems normal
    final_status = "HEALTHY"
    final_health_score = 97.5
    trigger_gemini = False
    gateway_decision = "ALL_SYSTEMS_NORMAL"
```

**Output Structure Sent to Frontend:**
```json
{
    "type": "telemetry",
    "timestamp": float,
    "data": {...snapshot...},
    "gateway_status": "EMERGENCY" | "WARNING" | "HEALTHY",
    "gateway_health_score": 0.0 | 87.5 | 97.5,
    "gateway_decision": "PHYSICAL_DANGER_DETECTED" | "ML_ANOMALY_DETECTED" | "ALL_SYSTEMS_NORMAL",
    "gateway_note": string,
    "ml_anomaly_score": float,
    "is_physically_dangerous": boolean,
    "safety_violations": [string],
    "root_cause": string | null
}
```

---

### **LAYER 2: Rule-Engine Analysis (Backend)**

**File:** `main.py` - `VehicleHealthAnalyzer` class

**Input:** Same snapshot data

**Process:**
1. Add reading to 60-second rolling windows
   ```python
   self.speed_window.append(data["speed_kmh"])
   self.temp_window.append(data["engine_temp_c"])
   self.psi_window.append(data["tire_pressure_psi"])
   # ... etc for all 10 metrics
   ```

2. Compute analysis results:
   - `_compute_status()` - Status for each metric (optimal/warning/danger)
   - `_compute_trends()` - Trend analysis (increasing/stable/decreasing)
   - `_generate_alerts()` - Rule-based alerts
   - `_compute_health_score()` - Overall health score (0-100)

3. Log to CSV:
   - File: `data/analysis_YYYYMMDD_HHMMSS.csv`
   - Columns: timestamp, all metrics, statuses, trends, health score, alerts

**Output:**
```python
{
    "timestamp": float,
    "current_values": {...snapshot...},
    "status": {
        "speed": "optimal|warning|danger",
        "temp": "optimal|warning|danger",
        "psi": "optimal|warning|danger",
        "rpm": "...",
        "oil": "...",
        "battery": "..."
    },
    "trends": {
        "speed": {"direction": "increasing|stable|decreasing", ...},
        "temp": {...},
        "psi": {...}
    },
    "alerts": [list of alert strings],
    "health_score": {
        "score": float (0-100),
        "status": "EXCELLENT|GOOD|FAIR|CRITICAL|EMERGENCY",
        "component_scores": {
            "speed": float,
            "temperature": float,
            "tire_pressure": float
        },
        "emergency": boolean,
        "contradictions": [list of contradiction strings],
        "tire_speed_risk": float (0-100),
        "temp_correlation_penalty": float
    },
    "window_size": int
}
```

---

### **LAYER 3: AI Analysis (Backend)**

**File:** `ai_analyzer.py` - `GeminiVehicleAnalyzer` class

**Trigger:** 
- When `trigger_gemini = True` (every EMERGENCY or WARNING)
- OR every 10 seconds (rate-limited)

**Process:**
1. Build prompt from telemetry + rule analysis
2. Call Gemini API with:
   - Current sensor values
   - Rule engine analysis
   - Previously detected contradictions
   - ML anomaly info

3. Parse structured response:
```python
{
    "diagnosis": string,
    "root_cause": string,
    "prediction": string,
    "action": string,
    "affected_systems": [strings],
    "severity": "SAFE|MONITOR|WARNING|CRITICAL|EMERGENCY",
    "confidence": float (0-1),
    "timestamp": float,
    "call_count": int
}
```

**Caching:** Results cached for 10 seconds to reduce API calls

---

### **LAYER 4: WebSocket Broadcast (Backend → Frontend)**

**File:** `main.py` - `broadcast_telemetry()` function

#### **Telemetry Clients** (`/ws/telemetry`)

**Endpoint:** `ws_telemetry()` (Lines 1371-1575)

**Frequency:** Every 1 second

**Payload Sent:**
```json
{
    "type": "telemetry",
    "timestamp": float,
    "data": {sensor values},
    "gateway_status": string,
    "gateway_health_score": float,
    "gateway_decision": string,
    "gateway_note": string,
    "ml_anomaly_score": float,
    "is_physically_dangerous": boolean,
    "safety_violations": [strings],
    "root_cause": string
}
```

#### **Analysis Clients** (`/ws/data-analysis`)

**Endpoint:** `ws_data_analysis()` (Lines 1578-1665)

**Frequency:** Every 1 second

**Payload Sent:**
```json
{
    "type": "analysis",
    "timestamp": float,
    "data": {
        ...complete analysis_result object...,
        "ai_diagnosis": {...AI response...},
        "ai_status": {...AI system status...},
        "gateway_status": string,
        "gateway_health_score": float,
        "gateway_decision": string,
        "is_physically_dangerous": boolean,
        "safety_violations": [strings],
        "root_cause": string
    }
}
```

---

## 🎨 Frontend Processing (Analysis Dashboard)

**File:** `static/analysis.js` - Main analysis dashboard

### **WebSocket Connection** (Lines 42-88)

```javascript
ws = new WebSocket(`ws://${location.host}/ws/data-analysis`)
```

### **Message Handling** (Lines 116-145)

```javascript
ws.onmessage = (e) => {
    let msg = JSON.parse(e.data)
    
    if (msg.type === "analysis" && msg.data) {
        updateAnalysisDashboard(msg.data)  // Process analysis
    } else if (msg.type === "summary") {
        updateSessionSummary(msg.data)     // Process summary
    } else if (msg.type === "ai_diagnosis") {
        updateAIDiagnosis(msg.data)        // Process AI
    }
}
```

### **Analysis Dashboard Update** (Lines 148-195)

1. **Health Score Display:**
   - Updates circular progress arc
   - Changes color based on score (green/blue/orange/red)
   - Displays status badge

2. **Metrics Display:**
   - Speed, Temperature, Tire Pressure, RPM, Oil, Battery
   - Shows current value, status, trend, average

3. **Charts:**
   - Real-time line charts for Speed, Temperature, Pressure
   - 60-point rolling window history
   - Canvas-based rendering

4. **Alerts:**
   - Displays dynamic alert list
   - Severity-based colors (danger/warning/info)
   - Max 10 alerts shown

5. **Contradictions:**
   - Fixed position alert box (top-right)
   - Red background, animated slide-in
   - Auto-dismisses after 8 seconds

6. **Physics Metrics:**
   - Tire-Speed Risk percentage
   - Temperature Correlation Penalty

7. **Service Recommendation:**
   - Based on health score and contradictions
   - Shows icon, text, action, health value, critical count

8. **AI Diagnosis Panel:**
   - Shows Gemini AI diagnosis
   - Severity badge with icon
   - Confidence percentage
   - Affected systems tags
   - Root cause, prediction, action text

---

## 📁 Data Persistence

### **CSV Training Data** (`vehicle_training_data.csv`)
- **Location:** `data/vehicle_training_data.csv`
- **Write Condition:** Only when `auto_drive_enabled = True`
- **Columns:** 14 columns (timestamp + 13 metrics)
- **Usage:** Training data for IsolationForest model

### **CSV Analysis Data** (`analysis_YYYYMMDD_HHMMSS.csv`)
- **Location:** `data/analysis_*.csv`
- **Created:** When analysis session starts
- **Columns:** 26 columns (metrics + statuses + health scores + alerts)
- **Updated:** Every second a new reading arrives

### **ML Models**
- **Location:** Root directory
- **Files:** 
  - `vehicle_scaler.pkl` - StandardScaler for feature normalization
  - `vehicle_anomaly_model.pkl` - IsolationForest model

---

## 🔐 Manual Input Processing

### **WebSocket Handler for Manual Sliders**

**Entry Point:** `ws_telemetry()` - `bulk_update` action (Lines 1448-1483)

**Flow:**
```python
if action == "bulk_update":
    data = msg.get("data")  # {sensor_name: value, ...}
    
    # Update simulation state
    for param, value in data.items():
        await state.update(param, float(value))
    
    # IMPORTANT: Evaluate through safety gateway
    gateway_result = evaluate_telemetry(data)
    
    # Send response with gateway fields
    await ws.send_text(json.dumps({
        "type": "ack",
        "detail": "Bulk update applied",
        "baselines": await state.get_baselines(),
        "gateway_status": gateway_result["status"],
        "gateway_health_score": gateway_result["health_score"],
        "gateway_safety_level": gateway_result["safety_level"],
        "gateway_decision": gateway_result["gateway_decision"],
        "gateway_note": gateway_result.get("gateway_note", ""),
        "ml_anomaly_score": gateway_result.get("ml_anomaly_score", -0.4),
        "is_physically_dangerous": gateway_result["is_physically_dangerous"],
        "safety_violations": gateway_result.get("safety_violations", []),
    }))
```

**Expected Behavior:**
- Manual slider values SHOULD be evaluated through `evaluate_telemetry()`
- If value triggers ML anomaly detection → `status = "WARNING"`, `health_score = 87.5`
- If value triggers physical safety rule → `status = "EMERGENCY"`, `health_score = 0.0`
- Response sent back to client with gateway fields
- Frontend updates color/badge based on `gateway_status`

---

## ⚠️ Critical Data Flow Points

### **Point 1: Data Validation**
- All numeric values validated as floats before entering pipeline
- Invalid values silently ignored (no crash)

### **Point 2: Feature Scaling**
- ALL 13 features must be normalized using same scaler trained on dataset
- Feature order MUST match training data order
- Scaling happens BEFORE ML prediction

### **Point 3: Gateway Priority**
- Physical safety (Layer 1) > ML anomaly (Layer 2) > Normal (Layer 3)
- Once physical danger detected, CANNOT be downgraded
- Status enum: EMERGENCY > WARNING > HEALTHY

### **Point 4: CSV Logging**
- Only occurs when `auto_drive_enabled = True`
- Manual slider data NOT logged unless auto-drive on
- Analysis CSV created immediately, updated every 1 second

### **Point 5: WebSocket Broadcast**
- Two separate WebSocket endpoints
- Telemetry clients get raw gateway status every second
- Analysis clients get full analysis + AI diagnosis every second
- Stale connections automatically removed

---

## 🐛 Common Issues & Debugging

### **Issue: Manual Anomalies Not Detected**

**Root Cause:** Manual slider values NOT being routed through `evaluate_telemetry()`

**Check:**
1. Is `bulk_update` handler calling `evaluate_telemetry(data)` ? ✓ Yes (Line 1451)
2. Is response including `gateway_*` fields? ✓ Yes (Lines 1458-1466)
3. Is frontend listening to these fields? 
   - Need to check `app.js` for how it processes telemetry response

**Fix:** Frontend must extract and display `gateway_status` field from acknowledgment response

---

### **Issue: Analysis Dashboard Not Updating**

**Root Cause:** Analysis clients connected but not receiving messages

**Check:**
1. Is `analysis_clients` set growing? (Check logs)
2. Is `analyze()` function being called? (Check logs for "AI diagnosis error")
3. Is WebSocket sending analysis payload? (Check network tab)

**Fix:** Verify WebSocket connection endpoint matches: `/ws/data-analysis`

---

### **Issue: ML Model Not Detecting Anomalies**

**Root Cause:** Features not scaled correctly, or model not loaded

**Check:**
1. Are model files present? ✓ `vehicle_anomaly_model.pkl` and `vehicle_scaler.pkl`
2. Is `_ml_loaded` flag True? (Check logs for "ML Scout models loaded")
3. Are features extracted in correct order?
4. Is scaling happening? (Add debug logs to see scaled values)

**Fix:** 
- Retrain model: `python3 train_model.py`
- Verify feature order matches training script

---

## 📊 Data Metrics Summary

| Metric | Range | Normal | Warning | Danger |
|--------|-------|--------|---------|--------|
| **Speed** | 0-250 km/h | 20-120 | >150 | >250 |
| **Engine Temp** | 40-140°C | 80-100 | >110 | >115 |
| **Tire Pressure** | 0-50 PSI | 30-35 | <25 | <20 |
| **Engine RPM** | 0-6000 | 800-3500 | >4500 | >5500 |
| **Oil Pressure** | 0-60 PSI | 40-60 | <20 | <10 |
| **Battery** | 10-15V | 13.5-14.5 | <12.5 | <11 |
| **Throttle** | 0-100% | 0-75 | >80 | 100 |
| **Engine Load** | 0-100% | 0-75 | >85 | 100 |
| **MAF** | 0-100 g/s | 20-80 | - | <5 |

---

## 🎯 Conclusion

The analysis dashboard uses a **three-layer deterministic safety gate** that prioritizes physical safety over ML predictions. Manual slider inputs SHOULD trigger this gate if they violate thresholds, but the frontend integration may need verification to ensure gateway responses are being displayed correctly.

