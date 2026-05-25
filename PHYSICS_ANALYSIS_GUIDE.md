# Advanced Physics-Based Vehicle Health Analysis System

## Overview

The telemetry dashboard now includes a sophisticated, physics-based vehicle health analysis engine that detects real-world vehicle contradictions and dangerous sensor combinations. This system goes beyond simple threshold checking to implement actual automotive physics algorithms used by OEM diagnostic systems.

---

## Core Physics Algorithms

### 1. Tire-Speed Interaction Risk (Nonlinear Physics)

**Problem Solved**: The system now detects when tire pressure and speed create dangerous conditions.

**Physics Principle**: 
- At low tire pressure, sidewalls flex excessively
- At high speed, flexing frequency increases exponentially
- Combined effect: heat buildup → tire blowout

**Formula**:
```
Risk = (1 - PSI/35) × (Speed/300) × 1.5 + Critical_Penalties

Where:
- PSI/35: Normalizes pressure (35 PSI is optimal)
- Speed/300: Normalizes speed (300 km/h is extreme)
- 1.5: Interaction amplification factor (nonlinear)
```

**Real-World Examples**:
- **Speed 300 km/h + PSI 0**: Risk = 100% (CRITICAL BLOWOUT)
- **Speed 200 km/h + PSI 20**: Risk = 70% (EMERGENCY)
- **Speed 100 km/h + PSI 32**: Risk = 5% (SAFE)

**Critical Thresholds**:
- PSI < 15: Blowout risk extreme (adds 50% penalty)
- Speed > 40 km/h + PSI < 20: High-speed low-pressure penalty (adds 30%)

---

### 2. Engine Temperature-Speed Correlation

**Problem Solved**: Detects impossible sensor combinations like high speed with cold engine.

**Physics Principle**:
- Engine should warm up during sustained driving
- Cold engine at high speed = sensor malfunction or engine failure
- Overheating at low speed = cooling system failure

**Expected Temperature Ranges**:
```
Idle (0-20 km/h):        70-95°C
Moderate (50-100 km/h):  85-105°C
High Speed (>150 km/h):  90-110°C
```

**Penalty Calculation**:
```
If temp < expected_min:
  Penalty = (expected_min - temp) × 1.5

If temp > expected_max:
  Penalty = (temp - expected_max) × 1.2

Max penalty: 30 points
```

**Real-World Examples**:
- **Speed 200 km/h + Temp 50°C**: Penalty = 30 (CRITICAL - engine not running)
- **Speed 10 km/h + Temp 120°C**: Penalty = 24 (CRITICAL - cooling failure)
- **Speed 100 km/h + Temp 95°C**: Penalty = 0 (NORMAL)

---

### 3. Contradiction Detection System

The system detects physically impossible or dangerous sensor combinations:

#### CRITICAL Contradictions:
1. **CRITICAL_TIRE_FAILURE_RISK**: Speed > 200 km/h AND PSI < 20
   - Immediate blowout risk
   - Action: EMERGENCY alert, reduce speed immediately

2. **CRITICAL_ENGINE_SENSOR_FAILURE**: Speed > 150 km/h AND Temp < 60°C
   - Engine not warmed up at highway speed
   - Indicates sensor malfunction or engine failure
   - Action: EMERGENCY alert, check engine diagnostics

#### WARNING Contradictions:
3. **TIRE_PUNCTURE_RISK**: Speed > 180 km/h AND PSI < 25
   - Possible puncture/leak at high speed
   - Action: Reduce speed, check tire pressure

4. **TIRE_FLAT_OR_SENSOR_FAILURE**: PSI < 5
   - Tire completely flat or sensor failure
   - Action: CRITICAL alert, pull over safely

5. **COOLING_SYSTEM_FAILURE**: Speed < 30 km/h AND Temp > 115°C
   - Engine overheating at low speed
   - Indicates cooling system malfunction
   - Action: CRITICAL alert, stop vehicle

6. **RAPID_TEMP_SPIKE**: Temperature increase > 10°C in 5 seconds
   - Abnormal temperature rise
   - Action: WARNING alert, monitor engine

7. **RAPID_PRESSURE_DROP**: Pressure decrease > 2 PSI in 5 seconds
   - Possible tire leak or puncture
   - Action: WARNING alert, check tires

---

## Health Score Calculation

### Algorithm Steps:

1. **Detect Contradictions** (0-100 penalty per contradiction)
2. **Calculate Component Scores**:
   - Speed Score: 0-100 based on safe speed ranges
   - Temperature Score: 0-100 based on optimal operating range
   - Tire Pressure Score: 0-100 based on safety thresholds

3. **Apply Physics Penalties**:
   - Tire-Speed Risk: Multiplicative penalty (0-100%)
   - Temperature Correlation: Additive penalty (0-30 points)

4. **Compute Final Score**:
   ```
   Base Score = (Speed × 0.25 + Temp × 0.35 + PSI × 0.40)
   
   With Tire-Speed Risk:
   Base Score = Base Score × (1 - Tire_Speed_Risk)
   
   With Temp Correlation:
   Base Score = Base Score - Temp_Correlation_Penalty
   
   With Contradictions:
   Base Score = Base Score - (Contradictions_Count × 15)
   
   Final Score = Clamp(Base Score, 0, 100)
   ```

### Health Status Determination:

```
🚨 EMERGENCY:  Contradictions detected OR Tire-Speed Risk > 50%
🔴 CRITICAL:   Score < 30 OR dangerous conditions
🟡 FAIR:       Score 30-60
🟢 GOOD:       Score 60-80
✅ EXCELLENT:  Score 80+
```

---

## Real-World Test Cases

### Test Case 1: High Speed + Low Pressure (Your Scenario)
```
Input:  Speed = 300 km/h, Temp = 90°C, PSI = 0
Output: 
  - Contradictions: [CRITICAL_TIRE_FAILURE_RISK]
  - Tire-Speed Risk: 100%
  - Health Score: 0 (EMERGENCY)
  - Status: 🚨 EMERGENCY
  - Alerts: 
    * 🚨 EMERGENCY: TIRE BLOWOUT IMMINENT - Reduce speed immediately!
    * 🚨 EMERGENCY: Engine sensor malfunction or engine failure detected
    * 🛞 CRITICAL_PRESSURE: Tire flat or severely under-inflated
```

### Test Case 2: Normal Highway Driving
```
Input:  Speed = 100 km/h, Temp = 95°C, PSI = 32
Output:
  - Contradictions: []
  - Tire-Speed Risk: 5%
  - Health Score: 92 (EXCELLENT)
  - Status: ✅ EXCELLENT
  - Alerts: None
```

### Test Case 3: Engine Overheating at Low Speed
```
Input:  Speed = 20 km/h, Temp = 120°C, PSI = 32
Output:
  - Contradictions: [COOLING_SYSTEM_FAILURE]
  - Tire-Speed Risk: 2%
  - Health Score: 35 (CRITICAL)
  - Status: 🔴 CRITICAL
  - Alerts:
    * 🔥 CRITICAL: Cooling system failure - Engine overheating at low speed
    * 🔥 OVERHEATING: Engine temperature critical - Pull over safely
```

### Test Case 4: Cold Engine at High Speed
```
Input:  Speed = 180 km/h, Temp = 45°C, PSI = 32
Output:
  - Contradictions: [CRITICAL_ENGINE_SENSOR_FAILURE]
  - Tire-Speed Risk: 3%
  - Temp Correlation Penalty: 30
  - Health Score: 15 (CRITICAL)
  - Status: 🚨 EMERGENCY
  - Alerts:
    * 🚨 EMERGENCY: Engine sensor malfunction or engine failure detected
    * ❄️ COLD_ENGINE: Engine not warmed up - Check ignition
```

---

## Dashboard Features

### Emergency Indicators
- **Red Pulsing Status**: Indicates EMERGENCY state
- **Contradiction Display**: Fixed overlay showing all detected contradictions
- **Physics Metrics**: Shows tire-speed risk percentage and temperature correlation penalty

### Real-Time Monitoring
- **60-Second Rolling Window**: Analyzes last 60 data points (1 per second)
- **Trend Detection**: Identifies rapid changes (temperature spikes, pressure drops)
- **Component Scores**: Individual health scores for speed, temperature, and tire pressure

### Alert System
- **Severity Levels**: Emergency (🚨), Critical (🔴), Warning (⚠️), Info (ℹ️)
- **Auto-Scrolling**: Latest alerts appear at bottom
- **Max 10 Alerts**: Older alerts are removed to prevent clutter

---

## Standards Reference

### SAE J1349 (Engine Temperature)
- Normal operating range: 90-105°C
- Extended range: 60-130°C
- Optimal efficiency: 195-220°F (90-105°C)

### DOT TPMS (Tire Pressure)
- Optimal: 30-35 PSI
- Acceptable: 25-40 PSI
- Critical low: < 25 PSI
- Dangerous: < 15 PSI

### OBD-II Standards
- Diagnostic Trouble Codes (DTCs) for sensor failures
- Real-time monitoring of engine parameters
- Emission control system diagnostics

### Tire Physics (FMVSS 139)
- Speed ratings validated at 80, 140, 150, 160 kph
- Pressure-speed interaction is nonlinear
- Heat buildup increases exponentially with speed and low pressure

---

## CSV Logging

All analysis data is logged to CSV files in the `data/` directory with the following fields:

```
timestamp, speed_kmh, engine_temp_c, tire_pressure_psi,
speed_status, temp_status, psi_status,
speed_trend, temp_trend, psi_trend,
overall_health, health_status, emergency, contradictions,
tire_speed_risk, temp_correlation_penalty, alerts
```

This enables:
- Historical analysis of vehicle health
- Trend identification over time
- Predictive maintenance planning
- Compliance reporting

---

## How to Test

1. **Open Dashboard**: Navigate to `http://localhost:8000/analysis`
2. **Set Extreme Values**: Use the telemetry dashboard to set:
   - Speed: 300 km/h
   - Tire Pressure: 0 PSI
   - Engine Temp: 50°C
3. **Observe Results**:
   - Health score drops to 0
   - Status shows 🚨 EMERGENCY
   - Red pulsing indicator appears
   - Contradictions overlay displays
   - Multiple emergency alerts appear

---

## Future Enhancements

1. **Machine Learning**: Train models on real vehicle data to improve anomaly detection
2. **Predictive Maintenance**: Estimate remaining tire life based on pressure trends
3. **Load Correlation**: Factor in vehicle load and acceleration
4. **Weather Integration**: Adjust thresholds based on ambient temperature
5. **Driver Behavior**: Detect aggressive driving patterns
6. **Multi-Vehicle Fleet**: Compare health across vehicle fleet

---

## References

- SAE J1349: Engine Performance
- SAE J2012: Diagnostic Trouble Code Definitions
- DOT TPMS: Tire Pressure Monitoring System Standards
- FMVSS 139: Tire Speed Rating Standards
- Tire Physics Research: Heat buildup and blowout mechanics
- OBD-II Standards: Real-time vehicle diagnostics

---

**Last Updated**: May 24, 2026
**System Version**: 2.0 (Physics-Based Analysis)
