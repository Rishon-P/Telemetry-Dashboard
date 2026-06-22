# Visual Data Flow Diagram

## 🔄 Complete Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VEHICLE DATA SOURCES                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  AUTO-DRIVE      │  │  MANUAL SLIDERS  │
        │  STATE MACHINE   │  │  (Frontend UI)   │
        │  (90-sec cycle)  │  │                  │
        └──────────────────┘  └──────────────────┘
                    │                ▼
                    │          WebSocket Handler:
                    │          /ws/telemetry
                    │          (bulk_update action)
                    │                │
                    └────────────────┼────────────────┐
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │         SimulationState.get_snapshot()                      │
        │  (Merge auto-drive baseline + manual overrides)            │
        │                                                             │
        │  Returns 13 vehicle metrics dictionary:                    │
        │  - speed_kmh, engine_rpm, throttle_pct, ...               │
        │  - engine_temp_c, oil_pressure_psi, ...                   │
        │  - battery_voltage_v, fuel_level_pct, ...                 │
        │  - tire_pressure_fl/fr/rl/rr_psi                          │
        └────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │   broadcast_telemetry() - Main Processing Loop (Every 1s)  │
        │                                                             │
        │   STEP 1: Layer 2 - ML Scout (IsolationForest)             │
        │   STEP 2: Layer 1 - Physical Safety Rules                  │
        │   STEP 3: Safety Gateway (Decision Matrix)                 │
        │   STEP 4: Rule Engine Analysis                             │
        │   STEP 5: AI Analysis (Gemini - Rate Limited)              │
        │   STEP 6: WebSocket Broadcast                              │
        └────────────────────────────────────────────────────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
        ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐
        │ STEP 1: ML      │  │ STEP 2: Physical │  │ STEP 3:      │
        │ SCOUT           │  │ Safety Rules     │  │ Decision     │
        │ (Anomaly        │  │                  │  │ Matrix       │
        │ Detection)      │  │ 5 Hard-coded     │  │              │
        │                 │  │ thresholds:      │  │ IF Layer 1   │
        │ Input: 13       │  │ • MAF dead?      │  │   TRIGGERED  │
        │ metrics scaled  │  │ • Transmission   │  │   → EMERGENCY│
        │                 │  │   slip?          │  │              │
        │ Process:        │  │ • Overheating?   │  │ ELSE IF ML   │
        │ 1. Extract      │  │ • Oil loss?      │  │   ANOMALY    │
        │    features     │  │ • Tire blowout?  │  │   → WARNING  │
        │ 2. Scale with   │  │                  │  │              │
        │    vehicle_     │  │ Output:          │  │ ELSE         │
        │    scaler.pkl   │  │ • layer_1_       │  │   → HEALTHY  │
        │ 3. Predict with │  │   triggered      │  │              │
        │    vehicle_     │  │ • layer_1_cause  │  │ Output:      │
        │    anomaly_     │  │ • safety_        │  │ • final_     │
        │    model.pkl    │  │   violations[]   │  │   status     │
        │ 4. Calculate    │  │                  │  │ • final_     │
        │    z-score      │  │                  │  │   health_    │
        │    root cause   │  │                  │  │   score      │
        │                 │  │                  │  │ • root_cause │
        │ Output:         │  │                  │  │              │
        │ • ml_prediction │  │                  │  │ Priority:    │
        │ • ml_anomaly_   │  │                  │  │ Physical > ML│
        │   score         │  │                  │  │              │
        │ • ml_root_cause │  │                  │  │              │
        │ • is_ml_anomaly │  │                  │  │              │
        └─────────────────┘  └──────────────────┘  └──────────────┘
                 │                   │                   │
                 └───────────────────┼───────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │ STEP 4: Rule Engine Analysis                               │
        │ (VehicleHealthAnalyzer - Parallel Track)                   │
        │                                                             │
        │ Input: Same snapshot                                       │
        │                                                             │
        │ Process:                                                   │
        │ 1. Add to 60-second rolling windows (10 deques)            │
        │ 2. Compute status (optimal/warning/danger) for each metric │
        │ 3. Compute trends (increasing/stable/decreasing)          │
        │ 4. Generate physics-based alerts                           │
        │ 5. Calculate component scores (0-100)                      │
        │ 6. Calculate overall health score (0-100)                  │
        │                                                             │
        │ Output:                                                    │
        │ {                                                          │
        │   "timestamp": float,                                      │
        │   "current_values": {...snapshot...},                      │
        │   "status": {...per-metric status...},                     │
        │   "trends": {...per-metric trends...},                     │
        │   "alerts": [...alert strings...],                         │
        │   "health_score": {                                        │
        │     "score": 0-100,                                        │
        │     "status": "EXCELLENT|GOOD|FAIR|CRITICAL",             │
        │     "component_scores": {...},                             │
        │     "emergency": bool,                                     │
        │     "contradictions": [...],                               │
        │     "tire_speed_risk": 0-100,                              │
        │     "temp_correlation_penalty": float                      │
        │   },                                                       │
        │   "window_size": int                                       │
        │ }                                                          │
        │                                                             │
        │ CSV Log: data/analysis_YYYYMMDD_HHMMSS.csv                 │
        └────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │ STEP 5: AI Analysis (Gemini - Rate Limited)                │
        │                                                             │
        │ Trigger Condition:                                         │
        │ • EMERGENCY or WARNING status detected, OR                 │
        │ • Every 10 seconds (max 6 calls/min, ~0.1/sec)             │
        │                                                             │
        │ Input: Snapshot + Rule Analysis                            │
        │                                                             │
        │ Process:                                                   │
        │ 1. Build detailed prompt with all telemetry               │
        │ 2. Call Google Gemini API                                  │
        │ 3. Parse structured JSON response                          │
        │ 4. Cache result for 10 seconds                             │
        │                                                             │
        │ Output:                                                    │
        │ {                                                          │
        │   "diagnosis": "Vehicle issue description",                │
        │   "root_cause": "Root cause analysis",                     │
        │   "prediction": "What will happen if ignored",             │
        │   "action": "Recommended action",                          │
        │   "affected_systems": ["engine", "cooling", ...],          │
        │   "severity": "SAFE|MONITOR|WARNING|CRITICAL|EMERGENCY",  │
        │   "confidence": 0.85,                                      │
        │   "timestamp": float,                                      │
        │   "call_count": int                                        │
        │ }                                                          │
        │                                                             │
        │ Cache: Reused for 10 seconds if no change                  │
        │        On API error: Falls back to cached response         │
        └────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │ STEP 6: WebSocket Broadcast (Two Separate Endpoints)       │
        └────────────────────────────────────────────────────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 ▼                   ▼                   ▼
        ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐
        │ Telemetry       │  │ Analysis         │  │ Data-Analysis│
        │ Clients         │  │ Clients (Old)    │  │ Clients (New)│
        │ /ws/telemetry   │  │ /ws/data_        │  │ /ws/data-    │
        │                 │  │ analysis         │  │ analysis     │
        │ Payload:        │  │                  │  │ (SAME as     │
        │ {               │  │ Payload:         │  │ analysis)    │
        │   "type":       │  │ {                │  │              │
        │   "telemetry",  │  │   "type":        │  │ Full         │
        │   "timestamp":  │  │   "analysis",    │  │ analysis_    │
        │   "data": {...} │  │   "timestamp":   │  │ result +     │
        │   "gateway_     │  │   "data": {      │  │ AI diagnosis │
        │   status":      │  │     "current_    │  │              │
        │   "EMERGENCY|   │  │     values": {}, │  │              │
        │   WARNING|      │  │     "status": {} │  │              │
        │   HEALTHY",     │  │     "trends": {} │  │              │
        │   "gateway_     │  │     "health_     │  │              │
        │   health_       │  │     score": {},  │  │              │
        │   score": 0|    │  │     "ai_         │  │              │
        │   87.5|97.5,    │  │     diagnosis":  │  │              │
        │   "gateway_     │  │     {...},       │  │              │
        │   decision":    │  │     "ai_status": │  │              │
        │   "PHYSICAL_    │  │     {...},       │  │              │
        │   DANGER|ML_    │  │     "gateway_    │  │              │
        │   ANOMALY|ALL_" │  │     status": "",  │  │              │
        │   "ml_anomaly_  │  │     ...          │  │              │
        │   score": float │  │   }              │  │              │
        │   "is_          │  │ }                │  │              │
        │   physically_   │  │                  │  │              │
        │   dangerous":   │  │ Broadcast: Every │  │              │
        │   bool,         │  │ 1 second to all  │  │              │
        │   "safety_      │  │ connected        │  │              │
        │   violations":  │  │ analysis_clients │  │              │
        │   []            │  │                  │  │              │
        │ }               │  │ Stale clients    │  │              │
        │                 │  │ auto-removed     │  │              │
        │ Broadcast:      │  │                  │  │              │
        │ Every 1 second  │  │                  │  │              │
        │ to all          │  │                  │  │              │
        │ connected_      │  │                  │  │              │
        │ clients         │  │                  │  │              │
        │                 │  │                  │  │              │
        │ Stale clients   │  │                  │  │              │
        │ auto-removed    │  │                  │  │              │
        └─────────────────┘  └──────────────────┘  └──────────────┘
                 │                   │                   │
                 └───────────────────┼───────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │                        FRONTEND                             │
        │              (static/analysis.js)                           │
        │                                                             │
        │ WebSocket Connection: /ws/data-analysis                    │
        │                                                             │
        │ Receive Messages:                                          │
        │ • "analysis" - Update dashboard with latest data           │
        │ • "summary" - Update session statistics                    │
        │ • "ai_diagnosis" - Update AI panel                         │
        │                                                             │
        │ Update Steps:                                              │
        │ 1. updateHealthScore() - Arc, badge, color               │
        │ 2. updateMetrics() - Speed, temp, pressure cards          │
        │ 3. updateAlerts() - Alert list display                    │
        │ 4. updateCharts() - Real-time line charts                 │
        │ 5. updateSessionStats() - Duration, data points           │
        │ 6. displayContradictions() - Red alert box (if any)       │
        │ 7. displayPhysicsMetrics() - Tire-speed risk              │
        │ 8. updateServiceRecommendation() - Icon, text, action     │
        │ 9. updateAIDiagnosis() - AI panel update                  │
        │                                                             │
        │ Display Elements:                                          │
        │ • Circular health arc (0-100 with colors)                 │
        │ • Status badges (HEALTHY/WARNING/EMERGENCY)               │
        │ • 6 metric cards with trends                              │
        │ • Alert scrolling list                                    │
        │ • 3 real-time charts (speed, temp, pressure)              │
        │ • Physics metrics display                                 │
        │ • Service recommendation box                              │
        │ • AI diagnosis panel                                      │
        │ • Session stats (duration, data points)                   │
        │                                                             │
        │ Color Scheme:                                             │
        │ • Green (#00ff00): Health ≥ 80%                           │
        │ • Blue (#00b4ff): Health 60-80%                           │
        │ • Orange (#ffaa00): Health 40-60%                         │
        │ • Red (#ff6b35): Health < 40%                             │
        │ • Red (#ff0000): EMERGENCY status                         │
        │ • Red (#ff0000): Contradictions                           │
        └────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │                   USER VISUALIZATION                        │
        │                                                             │
        │ • Real-time health score with smooth animation             │
        │ • Status badge changes color/text based on gateway status  │
        │ • Live metric values update every second                   │
        │ • Alert notifications appear/disappear                     │
        │ • Charts scroll with new data points                       │
        │ • Contradiction alert pops up when detected                │
        │ • Service recommendation updates dynamically               │
        │ • AI diagnosis shows Gemini analysis with confidence       │
        └────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Format Transformations

### **Transformation 1: Raw Snapshot → Scaled Features**

```
Input: {speed_kmh: 95, engine_rpm: 3000, engine_temp_c: 95, ...}
         ↓
Extract: [95, 3000, 50, 65, 35, 95, 45, 13.8, 75, 32, 32, 32, 32]
         (13 features in order)
         ↓
Scale:   [-0.45, 0.32, -0.12, 0.18, -0.05, 0.22, -0.10, 0.15, -0.08, 0.05, 0.05, 0.05, 0.05]
         (StandardScaler: mean=0, std=1)
         ↓
Output:  Normalized array ready for ML model
```

---

### **Transformation 2: ML Prediction → Anomaly Decision**

```
Scaled Input: [-0.45, 0.32, ...]
              ↓
IsolationForest.predict()  → 1 (normal) or -1 (anomaly)
IsolationForest.score_samples() → -0.45 (anomaly score)
              ↓
If -1: Max Z-score deviation → Feature name (root cause)
       Example: tp_fl_psi = 15 (very low) → "tp_fl"
```

---

### **Transformation 3: Physical Thresholds → Safety Violations**

```
Check rules in order:
│
├─ Rule A: maf < 5 && rpm > 1000?
│          → Trigger: "maf_sensor_dead"
│
├─ Rule B: speed > 100 && rpm < 1000 && throttle > 20?
│          → Trigger: "transmission_disconnect"
│
├─ Rule C: engine_temp > 115?
│          → Trigger: "engine_overheat"
│
├─ Rule D: oil_pressure < 10 && rpm > 0?
│          → Trigger: "critical_oil_loss"
│
└─ Rule E: ANY tire < 20 PSI?
           → Trigger: "tire_blowout" (one per tire)

Result: List of triggered rules → layer_1_triggered = bool
```

---

### **Transformation 4: Gateway Decision**

```
Input: (layer_1_triggered, is_ml_anomaly)

Logic Tree:
    │
    ├─ layer_1_triggered = True?
    │  → EMERGENCY (0.0)
    │
    ├─ layer_1_triggered = False && is_ml_anomaly = True?
    │  → WARNING (87.5)
    │
    └─ ELSE?
       → HEALTHY (97.5)
```

---

## 🔌 WebSocket Message Flow Timeline

```
Time: 0s
├─ Browser opens /analysis page
├─ WebSocket connects to /ws/data-analysis
└─ Frontend sends: {"action": "get_summary"}

Time: 1s (Broadcaster runs)
├─ Server generates snapshot
├─ Runs ML Scout → ml_prediction, ml_anomaly_score, ml_root_cause
├─ Checks physical rules → layer_1_triggered, safety_violations
├─ Applies gateway logic → final_status, final_health_score
├─ Runs rule engine → analysis_result with health_score, trends, alerts
├─ Optionally calls Gemini API → ai_diagnosis
├─ Broadcasts to analysis_clients
└─ Frontend receives analysis message
    └─ Parses, updates dashboard, renders

Time: 2s
├─ Same as 1s (repeats every 1 second)
└─ Frontend updates all displays with new data

...repeat until user closes browser or stops application
```

---

## 🎛️ Manual Slider Input Flow

```
User Changes Slider
        ↓
Frontend triggers:
  ws.send(JSON.stringify({
    action: "bulk_update",
    data: {
      speed_kmh: 150,
      engine_temp_c: 120,
      tire_pressure_psi: 15
    }
  }))
        ↓
WebSocket Handler: /ws/telemetry (bulk_update action)
        ↓
1. Update SimulationState:
   for param, value in data.items():
      state.update(param, float(value))
        ↓
2. Get current baselines:
   current_baselines = await state.get_baselines()
        ↓
3. Evaluate through gateway:
   gateway_result = evaluate_telemetry(current_baselines)
   ├─ ML Scout: Check anomaly → ml_prediction = -1 (anomaly found!)
   ├─ Physical Rules: Check thresholds → tire < 20 PSI! → layer_1_triggered = True
   ├─ Gateway Decision: layer_1_triggered = True → EMERGENCY status
   └─ Return: {"status": "EMERGENCY", "health_score": 0.0, ...}
        ↓
4. Send Response:
   ws.send(JSON.stringify({
     type: "ack",
     baselines: {...updated values...},
     gateway_status: "EMERGENCY",
     gateway_health_score: 0.0,
     gateway_decision: "PHYSICAL_DANGER_DETECTED",
     is_physically_dangerous: true,
     safety_violations: ["CRITICAL: Tire FL pressure 15 PSI..."]
   }))
        ↓
Frontend receives ACK response
        ↓
**CRITICAL**: Frontend must extract gateway_status field and update UI
  ├─ Change health score to 0
  ├─ Change status badge color to red
  ├─ Display EMERGENCY indicator
  └─ Show safety violations

Expected Result: User enters extreme values → UI immediately shows EMERGENCY
```

---

## ⚠️ Where Manual Anomalies Currently Break

Looking at the code path:

```
Manual slider → WebSocket handler ✓ (receives data)
               → state.update() ✓ (updates simulation state)
               → evaluate_telemetry() ✓ (evaluates through gateway)
               → gateway_result has correct status ✓
               → ws.send() sends response ✓
               ↓
**QUESTION**: Does Frontend listen to ACK response?
              Or only listen to broadcast messages?

Current Frontend Code (analysis.js):
  ws.onmessage = (e) => {
    if (msg.type === "analysis") → from broadcast
    if (msg.type === "summary") → from client action
    if (msg.type === "ai_diagnosis") → from client action
    // NO handler for "ack" type!
  }

PROBLEM IDENTIFIED:
The ACK response from manual slider updates is being sent,
but Frontend is NOT processing it!

Frontend only updates when broadcast message arrives (every 1 second).
Between slider update and next broadcast, no visual feedback!
```

---

## ✅ The Fix Needed

**Frontend: static/analysis.js**

```javascript
// Add ACK handler:
ws.onmessage = (e) => {
    msg = JSON.parse(e.data)
    
    if (msg.type === "ack") {
        // NEW: Handle manual update acknowledgment
        if (msg.gateway_status) {
            // Extract gateway fields
            const gatewayStatus = msg.gateway_status
            const healthScore = msg.gateway_health_score
            const violations = msg.safety_violations || []
            
            // Immediately update UI
            updateHealthScore({
                score: healthScore,
                status: gatewayStatus,
                emergency: gatewayStatus === "EMERGENCY",
                contradictions: violations,
                component_scores: {...}
            })
            
            // Show violations if any
            if (violations.length > 0) {
                displayContradictions(violations)
            }
        }
        return
    }
    
    // ... rest of handlers (analysis, summary, ai_diagnosis)
}
```

This way, when user adjusts sliders:
1. Backend evaluates through gateway ✓
2. Backend sends ACK with gateway status ✓
3. Frontend receives ACK and immediately updates display ✓
4. User sees status change right away ✓

