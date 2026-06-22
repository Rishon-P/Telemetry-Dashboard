# Project File Structure & Role of Each Component

---

## 📂 Project Structure

```
telemetry-dashboard/
│
├── 🐍 BACKEND (Python - FastAPI)
│   │
│   ├── main.py ⭐ [PRIMARY - 1700+ lines]
│   │   ├── SimulationState class [Lines 67-156]
│   │   │   └─ Manages mutable vehicle sensor baseline values
│   │   │
│   │   ├── VehicleHealthAnalyzer class [Lines 158-1030]
│   │   │   └─ 60-second rolling window analysis engine
│   │   │
│   │   ├── broadcast_telemetry() [Lines 1033-1300]
│   │   │   └─ Main processing loop (3-Layer Gateway + Rule Engine)
│   │   │
│   │   ├── ws_telemetry(ws) [Lines 1371-1575]
│   │   │   └─ WebSocket: /ws/telemetry (telemetry clients)
│   │   │   └─ Handles: manual slider updates, auto-drive toggle
│   │   │
│   │   ├── ws_data_analysis(ws) [Lines 1578-1665]
│   │   │   └─ WebSocket: /ws/data-analysis (analysis clients)
│   │   │   └─ Streams: analysis results, AI diagnoses
│   │   │
│   │   └── Routes
│   │       ├─ GET /analysis → analysis dashboard HTML
│   │       ├─ GET / → main dashboard HTML
│   │       ├─ GET /health → server status
│   │       ├─ GET /baselines → current sensor values
│   │       └─ GET /ai_status → Gemini API status
│   │
│   ├── safety_gateway.py ⭐ [CRITICAL - 400+ lines]
│   │   ├── SafetyBoundaryChecker class [Lines 24-103]
│   │   │   └─ Layer 1: Hard-coded physical safety thresholds
│   │   │   └─ 5 Rules: MAF dead, transmission slip, overheat, oil loss, tire blowout
│   │   │
│   │   ├── MLScout class [Lines 108-269]
│   │   │   └─ Layer 2: IsolationForest anomaly detection
│   │   │   └─ Uses: vehicle_scaler.pkl, vehicle_anomaly_model.pkl
│   │   │
│   │   ├── SafetyGateway class [Lines 274-389]
│   │   │   └─ Layer 0: Decision matrix (combines Layer 1 + Layer 2)
│   │   │   └─ Output: status (EMERGENCY/WARNING/HEALTHY), health_score
│   │   │
│   │   └── evaluate_telemetry(data) [Lines 394-399]
│   │       └─ Public API: Calls safety_gateway.evaluate(data)
│   │
│   ├── ai_analyzer.py [300+ lines]
│   │   ├── GeminiVehicleAnalyzer class
│   │   │   ├─ __init__() [Lines 113-137]
│   │   │   │  └─ Initializes Gemini API client
│   │   │   │
│   │   │   ├─ _build_prompt() [Lines 163-221]
│   │   │   │  └─ Constructs detailed analysis prompt
│   │   │   │
│   │   │   ├─ analyze() [Lines 256-403]
│   │   │   │  └─ Calls Gemini API (rate-limited every 10 seconds)
│   │   │   │
│   │   │   └─ _get_fallback_diagnosis() [Lines 405-426]
│   │   │      └─ Returns cached diagnosis on API error
│   │   │
│   │   └── AIVehicleDiagnosis class [Lines 37-65]
│   │       └─ Structured response data model
│   │
│   ├── train_model.py [80+ lines]
│   │   └─ Script to retrain IsolationForest model
│   │   └─ Reads: vehicle_training_data.csv
│   │   └─ Outputs: vehicle_scaler.pkl, vehicle_anomaly_model.pkl
│   │
│   ├── predict_anomalies.py [50+ lines]
│   │   └─ Script to test anomaly detection on CSV data
│   │
│   └── requirements.txt
│       └─ Dependencies:
│           fastapi, uvicorn, websockets, python-dotenv
│           numpy, scikit-learn, pandas, joblib, google-generativeai
│
├── 🌐 FRONTEND (JavaScript + HTML/CSS)
│   │
│   ├── static/
│   │   │
│   │   ├── index.html [Main Dashboard Page]
│   │   │   ├─ Telemetry display
│   │   │   ├─ 6 sensor gauge displays
│   │   │   ├─ Manual slider controls
│   │   │   ├─ Auto-drive toggle
│   │   │   └─ Connection status indicator
│   │   │
│   │   ├── analysis.html [Analysis Dashboard Page] ⭐
│   │   │   ├─ Health score circular arc
│   │   │   ├─ 6 metric cards with trends
│   │   │   ├─ 3 real-time line charts
│   │   │   ├─ Alert list
│   │   │   ├─ Service recommendation box
│   │   │   ├─ AI diagnosis panel
│   │   │   └─ Physics metrics display
│   │   │
│   │   ├── app.js [Main Dashboard Controller]
│   │   │   ├─ WebSocket connection to /ws/telemetry
│   │   │   ├─ Handles telemetry messages
│   │   │   ├─ Sends slider updates (bulk_update)
│   │   │   ├─ Sends auto-drive toggle
│   │   │   └─ Updates gauge displays
│   │   │
│   │   ├── analysis.js [Analysis Dashboard Controller] ⭐
│   │   │   ├─ WebSocket connection to /ws/data-analysis [Line 43]
│   │   │   ├─ Message handler [Lines 116-145]
│   │   │   ├─ updateAnalysisDashboard() [Lines 148-195]
│   │   │   ├─ updateHealthScore() [Lines 355-386]
│   │   │   ├─ updateMetrics() [Lines 461-495]
│   │   │   ├─ updateAlerts() [Lines 497-531]
│   │   │   ├─ updateCharts() [Lines 533-609]
│   │   │   ├─ displayContradictions() [Lines 386-427]
│   │   │   ├─ updateServiceRecommendation() [Lines 788-861]
│   │   │   └─ updateAIDiagnosis() [Lines 863-939]
│   │   │
│   │   ├── style.css [Main Dashboard Styling]
│   │   │   ├─ Gauge display styles
│   │   │   ├─ Slider controls
│   │   │   └─ Connection dot animation
│   │   │
│   │   └── analysis-style.css [Analysis Dashboard Styling]
│   │       ├─ Health arc styling
│   │       ├─ Metric card styles
│   │       ├─ Alert list styles
│   │       ├─ Chart canvas styling
│   │       └─ Status color schemes
│   │
├── 📊 DATA & MODELS
│   │
│   ├── vehicle_scaler.pkl [1.3 KB] ⭐
│   │   └─ StandardScaler object fitted on 55,052 training samples
│   │   └─ Used by: safety_gateway.py MLScout.evaluate()
│   │   └─ Purpose: Normalize features to mean=0, std=1 scale
│   │
│   ├── vehicle_anomaly_model.pkl [1.5 MB] ⭐
│   │   └─ IsolationForest model (100 estimators, contamination=0.01)
│   │   └─ Used by: safety_gateway.py MLScout.evaluate()
│   │   └─ Purpose: Detect anomalous vehicle patterns
│   │
│   ├── data/
│   │   │
│   │   ├── vehicle_training_data.csv [55,052 rows]
│   │   │   ├─ Generated by: Auto-drive simulation (when enabled)
│   │   │   ├─ Columns: timestamp, 13 metrics
│   │   │   ├─ Used by: train_model.py to train IsolationForest
│   │   │   └─ Write condition: auto_drive_enabled = True
│   │   │
│   │   └── analysis_*.csv [Multiple files, dated]
│   │       ├─ Generated by: VehicleHealthAnalyzer._log_to_csv()
│   │       ├─ Format: analysis_YYYYMMDD_HHMMSS.csv
│   │       ├─ Columns: 26 columns (metrics + statuses + scores + alerts)
│   │       ├─ Created: One file per analysis session
│   │       └─ Updated: Every 1 second while running
│   │
├── 📝 CONFIGURATION
│   │
│   ├── .env [Environment Variables]
│   │   └─ GEMINI_API_KEY (required for AI analysis)
│   │
│   ├── .env.example [Template]
│   │   └─ Show required environment variables
│   │
│   └── .gitignore [Git Ignore Rules]
│       └─ Excludes: .venv, __pycache__, .env, *.pkl, *.csv
│
└── 📚 DOCUMENTATION
    │
    ├── EXACT_DATA_HANDLING_EXPLAINED.md ⭐ [This explains exact flow]
    ├── DATA_FLOW_ANALYSIS.md ⭐ [Complete layer breakdown]
    ├── DATA_FLOW_DIAGRAM.md ⭐ [Visual diagrams]
    ├── GATEWAY_QUICK_REFERENCE.md [Decision matrix reference]
    ├── SAFETY_GATEWAY_ARCHITECTURE.md [Architecture details]
    ├── MODEL_TRAINING_GUIDE.md [How to train ML model]
    ├── README_ML.md [ML system explanation]
    └── [Various other documentation files]
```

---

## 🔗 Data Flow Through Files

### **Path 1: Auto-Drive Data Generation**

```
SimulationState [main.py]
    ↓ (maintains baseline values)
    ↓ (updated every iteration of state machine)
    ↓
state.get_snapshot() [main.py:92]
    ↓ (returns 13 metrics dictionary)
    ↓
broadcast_telemetry() [main.py:1033]
    ↓ (Main processing loop, every 1 second)
    ├→ CSV Write (if auto_drive_enabled)
    ├→ ML Scout evaluation [safety_gateway.py:MLScout]
    ├→ Physical Rules check [safety_gateway.py:SafetyBoundaryChecker]
    ├→ Gateway Decision [safety_gateway.py:SafetyGateway]
    ├→ Rule Engine [VehicleHealthAnalyzer:add_reading()]
    ├→ AI Analysis [ai_analyzer.py:GeminiVehicleAnalyzer]
    └→ WebSocket Broadcast
       ├→ Telemetry clients [ws_telemetry()]
       └→ Analysis clients [ws_data_analysis()]
            ↓
            Frontend [static/analysis.js]
            └→ Display on dashboard
```

---

### **Path 2: Manual Slider Input**

```
Frontend Slider Change [static/app.js or analysis.js]
    ↓ (User moves slider)
    ↓
WebSocket Send
    {
      action: "bulk_update" or "update",
      data: {slider_name: new_value}
    }
    ↓
ws_telemetry() Handler [main.py:1448]
    ↓
state.update() [main.py:140]
    ↓ (Modifies baseline value in memory)
    ↓
evaluate_telemetry() [safety_gateway.py:394]
    ├→ ML Scout check [safety_gateway.py:MLScout.evaluate()]
    ├→ Physical Rules [safety_gateway.py:SafetyBoundaryChecker.check_physical_safety()]
    └→ Gateway Decision [safety_gateway.py:SafetyGateway.evaluate()]
    ↓
Send ACK Response
    {
      type: "ack",
      gateway_status: "EMERGENCY|WARNING|HEALTHY",
      gateway_health_score: 0.0 | 87.5 | 97.5,
      ...
    }
    ↓ (Should be processed by Frontend but may not be)
    ↓
Next broadcast_telemetry() call [After 1 second]
    ↓ (Evaluates updated value)
    ↓
Send Analysis Message
    {
      type: "analysis",
      data: {full analysis with gateway status}
    }
    ↓
Frontend receives [static/analysis.js:onmessage]
    └→ updateAnalysisDashboard()
        └→ Display updated status
```

---

### **Path 3: ML Model Training & Prediction**

```
Training Phase:
    │
    vehicle_training_data.csv [55,052 rows] [main.py writes when auto_drive_enabled]
    ↓
    train_model.py [Executed manually]
    ├→ Read CSV with pandas
    ├→ Drop timestamp column
    ├→ Fit StandardScaler on 13 metrics
    ├→ Fit IsolationForest (100 estimators, contamination=0.01)
    ├→ Save vehicle_scaler.pkl
    └→ Save vehicle_anomaly_model.pkl
    
Prediction Phase (During Runtime):
    │
    snapshot = state.get_snapshot() [main.py:1038]
    ↓
    Extract 13 features in order [main.py:1048-1051]
    ↓
    Scale with vehicle_scaler.pkl [main.py:1056]
    ↓
    Predict with vehicle_anomaly_model.pkl [main.py:1059-1063]
    ├→ Prediction (1 or -1)
    ├→ Anomaly score (float)
    └→ Root cause (feature name with max deviation)
    ↓
    Used in Gateway Decision [main.py:1167]
```

---

## 🎛️ Component Interactions

### **The Three Layers (All in broadcast_telemetry)**

```
┌─────────────────────────────────────────────────────────┐
│ BROADCAST_TELEMETRY() [main.py:1033]                    │
│ Main processing loop (every 1 second)                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ LAYER 2: ML Scout [main.py:1044-1076]                  │
├─────────────────────────────────────────────────────────┤
│ Imports:                                               │
│   - _scaler (vehicle_scaler.pkl loaded at startup)     │
│   - _model (vehicle_anomaly_model.pkl loaded)          │
│   - np (numpy for array operations)                    │
│                                                         │
│ Process:                                               │
│   1. Extract features from snapshot                    │
│   2. Scale using vehicle_scaler                        │
│   3. Predict using vehicle_anomaly_model               │
│   4. Calculate root cause via max Z-score deviation    │
│                                                         │
│ Output:                                                │
│   - ml_prediction (1 or -1)                           │
│   - ml_anomaly_score (float)                          │
│   - ml_root_cause (string or None)                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ LAYER 1: Physical Rules [main.py:1080-1130]            │
├─────────────────────────────────────────────────────────┤
│ Process:                                               │
│   1. Extract raw metric values from snapshot           │
│   2. Check 5 hard-coded rules                          │
│   3. Build violation messages                          │
│                                                         │
│ Output:                                                │
│   - layer_1_triggered (boolean)                        │
│   - layer_1_cause (string)                             │
│   - safety_violations (list of strings)                │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ LAYER 0: Gateway Decision [main.py:1135-1196]          │
├─────────────────────────────────────────────────────────┤
│ Decision Tree:                                         │
│   if layer_1_triggered:                                │
│       → EMERGENCY (0.0)                                │
│   elif is_ml_anomaly:                                  │
│       → WARNING (87.5)                                 │
│   else:                                                │
│       → HEALTHY (97.5)                                 │
│                                                         │
│ Output:                                                │
│   - final_status (EMERGENCY/WARNING/HEALTHY)           │
│   - final_health_score (0.0/87.5/97.5)                │
│   - root_cause (string or None)                        │
│   - trigger_gemini (boolean)                           │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ PARALLEL: Rule Engine [VehicleHealthAnalyzer]          │
├─────────────────────────────────────────────────────────┤
│ Imports:                                               │
│   - collections.deque (rolling windows)                │
│   - csv (for logging)                                  │
│   - numpy (for calculations)                           │
│                                                         │
│ Process:                                               │
│   1. Add snapshot to 60-sec rolling windows             │
│   2. Compute status for each metric                    │
│   3. Compute trends                                    │
│   4. Generate alerts                                   │
│   5. Calculate health score                            │
│   6. Log to CSV                                        │
│                                                         │
│ Output:                                                │
│   - analysis_result (dict with all analysis)           │
│   - CSV file update                                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ OPTIONAL: AI Analysis [ai_analyzer.py]                 │
├─────────────────────────────────────────────────────────┤
│ Trigger: When EMERGENCY/WARNING OR every 10 seconds    │
│                                                         │
│ Imports:                                               │
│   - google.generativeai (Gemini API)                  │
│                                                         │
│ Process:                                               │
│   1. Build prompt from telemetry + analysis            │
│   2. Call Gemini API                                   │
│   3. Parse JSON response                               │
│   4. Cache result for 10 seconds                       │
│                                                         │
│ Output:                                                │
│   - ai_diagnosis (dict from Gemini)                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 WebSocket Message Flows

### **WebSocket #1: /ws/telemetry (Telemetry Clients)**

```
Handler: ws_telemetry() [main.py:1371]

Incoming Actions:
├─ "toggle_auto_drive"
│  └─ Toggle state.auto_drive_enabled flag
│  └─ Send back: ack with flag state
│
├─ "bulk_update"
│  └─ Update multiple sliders at once
│  └─ Evaluate through gateway
│  └─ Send back: ack with gateway fields
│
├─ "update"
│  └─ Update single parameter
│  └─ Evaluate through gateway
│  └─ Send back: ack with gateway fields
│
└─ "get_baselines"
   └─ Return current sensor values
   └─ Send back: baselines dict

Outgoing Messages (from broadcast_telemetry):
    Every 1 second to all connected telemetry clients:
    {
        "type": "telemetry",
        "timestamp": float,
        "data": {13 metrics},
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

---

### **WebSocket #2: /ws/data-analysis (Analysis Clients)**

```
Handler: ws_data_analysis() [main.py:1578]

Incoming Actions:
├─ "get_summary"
│  └─ Return session summary statistics
│  └─ Send back: summary dict
│
└─ "force_ai_analysis"
   └─ Trigger immediate Gemini analysis
   └─ Send back: ai_diagnosis dict

Outgoing Messages (from broadcast_telemetry):
    Every 1 second to all connected analysis clients:
    {
        "type": "analysis",
        "timestamp": float,
        "data": {
            "timestamp": float,
            "current_values": {13 metrics},
            "status": {per-metric status},
            "trends": {per-metric trends},
            "alerts": [alert strings],
            "health_score": {
                "score": float,
                "status": string,
                "component_scores": {...},
                "emergency": boolean,
                "contradictions": [strings],
                "tire_speed_risk": float,
                "temp_correlation_penalty": float,
            },
            "window_size": int,
            "ai_diagnosis": {Gemini response},
            "ai_status": {AI system status},
            "gateway_status": "EMERGENCY|WARNING|HEALTHY",
            "gateway_health_score": 0.0 | 87.5 | 97.5,
            "gateway_decision": string,
            "is_physically_dangerous": boolean,
            "safety_violations": [strings],
            "root_cause": string,
        }
    }
```

---

## 🔐 Critical File Dependencies

```
safety_gateway.py
├─ Imports: joblib, numpy, logging, pathlib
├─ Files: vehicle_scaler.pkl, vehicle_anomaly_model.pkl
└─ Used by: main.py broadcast_telemetry()

main.py
├─ Imports: safety_gateway.evaluate_telemetry()
├─ Imports: ai_analyzer.GeminiVehicleAnalyzer()
├─ Imports: csv, json, asyncio, fastapi, websockets
├─ Files: data/vehicle_training_data.csv (write)
├─ Files: data/analysis_*.csv (write)
└─ Depends: .env (GEMINI_API_KEY)

ai_analyzer.py
├─ Imports: google.generativeai
└─ Depends: .env (GEMINI_API_KEY)

app.js (Frontend)
├─ Connects: ws://host/ws/telemetry
├─ Sends: toggle_auto_drive, bulk_update, update
└─ Updates: gauge displays, slider values

analysis.js (Frontend)
├─ Connects: ws://host/ws/data-analysis
├─ Receives: analysis messages
├─ Processes: health scores, metrics, alerts, trends, charts
└─ Updates: dashboard visualization
```

---

## ⚡ Execution Timeline (Every 1 Second)

```
T=0.000s
    ├─ broadcast_telemetry() loop iteration starts
    ├─ state.get_snapshot() → returns 13 metrics
    └─ (milliseconds pass)

T=0.010s
    ├─ ML Scout evaluation
    │  ├─ Extract 13 features
    │  ├─ Scale with vehicle_scaler.pkl
    │  ├─ Predict with vehicle_anomaly_model.pkl
    │  └─ Calculate anomaly_score and root_cause
    └─ (milliseconds pass)

T=0.020s
    ├─ Physical Safety Rules check
    │  ├─ Check Rule A (MAF dead)
    │  ├─ Check Rule B (transmission slip)
    │  ├─ Check Rule C (overheat)
    │  ├─ Check Rule D (oil loss)
    │  └─ Check Rule E (tire blowout)
    └─ (milliseconds pass)

T=0.025s
    ├─ Gateway Decision Matrix
    │  └─ Determine final_status based on Layer 1 + Layer 2 results
    └─ (milliseconds pass)

T=0.030s
    ├─ Rule Engine Analysis (Parallel)
    │  ├─ Add readings to 60-sec windows
    │  ├─ Compute status/trends/alerts
    │  ├─ Calculate health score
    │  └─ Log to CSV
    └─ (milliseconds pass)

T=0.100s
    ├─ Optional: Gemini AI Analysis
    │  └─ IF (trigger_gemini OR every 10 seconds):
    │     ├─ Build prompt
    │     ├─ Call Gemini API (~2-3 seconds)
    │     └─ Cache result
    └─ (seconds pass during API call)

T=0.900s (after API or if skipped)
    ├─ Broadcast to Telemetry Clients
    │  └─ Send JSON with telemetry + gateway fields
    └─ (milliseconds pass)

T=0.950s
    ├─ Broadcast to Analysis Clients
    │  └─ Send JSON with full analysis + AI
    └─ (milliseconds pass)

T=1.000s
    ├─ Loop iteration completes
    ├─ await asyncio.sleep(1)
    └─ Repeat from T=0.000s
```

---

## 📋 Summary

**Core Processing:** `main.py` - broadcast_telemetry() function
**Safety Logic:** `safety_gateway.py` - Three-layer evaluation
**Analysis Logic:** `main.py` - VehicleHealthAnalyzer class
**AI Logic:** `ai_analyzer.py` - GeminiVehicleAnalyzer class
**ML Models:** `vehicle_scaler.pkl`, `vehicle_anomaly_model.pkl`
**Frontend Display:** `static/analysis.js` - Dashboard visualization
**WebSocket Endpoints:** `/ws/telemetry`, `/ws/data-analysis`

**Every 1 second:**
1. Get snapshot
2. Run ML Scout (0.01s)
3. Check Physical Rules (0.01s)
4. Apply Gateway Decision (0.01s)
5. Run Rule Engine (0.03s)
6. Optional: AI Analysis (2-3s if triggered)
7. Broadcast to all connected clients

This is the complete data pipeline of your telemetry dashboard system.

