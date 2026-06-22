# Vehicle Assumptions and Health Score Formulas

## Date: May 24, 2026

---

## Part 1: Vehicle Type Assumptions

### Vehicle Class Assumed: **Generic Sedan (Mid-Size)**

The current system is designed for a **generic mid-size sedan** with the following characteristics:

#### Engine Specifications
- **Engine Type**: 4-cylinder gasoline engine
- **Displacement**: 1.6-2.0L
- **Power**: 100-150 HP
- **Torque**: 120-180 Nm

#### Tire Specifications
- **Tire Size**: 205/55R16 (typical sedan)
- **Optimal Pressure**: 30-35 PSI (2.1-2.4 bar)
- **Speed Rating**: H-rated (up to 130 mph / 210 km/h)
- **Load Index**: 91 (615 kg per tire)

#### Performance Characteristics
- **Max Speed**: 180-200 km/h
- **0-100 km/h**: 8-10 seconds
- **Fuel Tank**: 50-60 liters
- **Curb Weight**: 1200-1400 kg

#### Operating Conditions
- **Normal City Speed**: 40-60 km/h
- **Highway Speed**: 100-120 km/h
- **Idle Speed**: 600-800 RPM
- **Redline**: 6500-7000 RPM

---

## Part 2: Why This Vehicle Type?

### Reasoning
1. **Most Common**: Mid-size sedans represent ~40% of global vehicle market
2. **Standardized Data**: OBD-II standards are based on typical sedans
3. **Balanced Thresholds**: Not too aggressive (sports car) or too conservative (truck)
4. **Real-World Relevance**: Most drivers operate sedans

### How Different Vehicle Types Would Differ

#### SUV (Sport Utility Vehicle)
- **Tire Pressure**: 32-36 PSI (higher due to weight)
- **Max Speed**: 180-220 km/h
- **Engine Temp**: 85-110°C (similar)
- **Weight**: 1600-2200 kg
- **Adjustment**: +5-10% on tire pressure thresholds

#### Sports Car
- **Tire Pressure**: 28-32 PSI (lower for grip)
- **Max Speed**: 250+ km/h
- **Engine Temp**: 90-115°C (runs hotter)
- **Weight**: 1200-1400 kg
- **Adjustment**: -5% on tire pressure, +10°C on temp thresholds

#### Hypercar
- **Tire Pressure**: 25-30 PSI (very low for performance)
- **Max Speed**: 300+ km/h
- **Engine Temp**: 100-120°C (runs very hot)
- **Weight**: 1300-1500 kg
- **Adjustment**: -10% on tire pressure, +15°C on temp thresholds

#### Truck/Commercial
- **Tire Pressure**: 80-100 PSI (dual wheels, much higher)
- **Max Speed**: 160 km/h (governed)
- **Engine Temp**: 80-105°C (similar)
- **Weight**: 3000-5000 kg
- **Adjustment**: +100% on tire pressure thresholds

---

## Part 3: Health Score Calculation Formula

### Overall Formula

```
HEALTH_SCORE = Base_Score - Penalties + Bonuses

Where:

Base_Score = (Speed_Score × 0.25) + (Temp_Score × 0.35) + (PSI_Score × 0.40)

Penalties:
  - Tire-Speed Risk Penalty = Base_Score × (1 - Tire_Speed_Risk)
  - Temperature Correlation Penalty = 0-30 points
  - Contradiction Penalty = Contradictions_Count × 15 points

Final_Score = Clamp(Base_Score - Penalties, 0, 100)
```

### Component Scores

#### 1. Speed Score (Weight: 25%)
```
if speed <= 120 km/h:
    speed_score = 100  (Safe, optimal)
elif speed <= 160 km/h:
    speed_score = 80   (Moderate, acceptable)
elif speed <= 200 km/h:
    speed_score = 60   (High, caution)
elif speed <= 250 km/h:
    speed_score = 40   (Very high, warning)
else:
    speed_score = 20   (Extreme, danger)
```

**Rationale**: Speed affects tire wear, braking distance, and fuel consumption. Higher speeds increase risk.

#### 2. Temperature Score (Weight: 35%)
```
if temp < 50°C:
    temp_score = 30    (Engine not warmed up)
elif 60°C <= temp <= 105°C:
    temp_score = 100   (Optimal operating range)
elif 105°C < temp <= 115°C:
    temp_score = 70    (Warning range)
else:
    temp_score = 20    (Danger range - overheating)
```

**Rationale**: Engine temperature indicates cooling system health and combustion efficiency. Optimal range is 90-105°C for modern engines.

#### 3. Tire Pressure Score (Weight: 40%)
```
if psi < 5:
    psi_score = 0      (Flat tire)
elif psi < 20:
    if speed > 100:
        psi_score = 10 (Dangerous at high speed)
    else:
        psi_score = 30 (Dangerous at any speed)
elif psi < 25:
    psi_score = 50     (Below optimal)
elif 30 <= psi <= 35:
    psi_score = 100    (Optimal)
elif psi <= 40:
    psi_score = 80     (Slightly over)
else:
    psi_score = 40     (Over-inflated)
```

**Rationale**: Tire pressure is the most critical factor (40% weight) because:
- Affects braking distance
- Affects fuel consumption
- Affects tire lifespan
- Directly impacts safety

### Tire-Speed Risk Calculation

```
Formula: Risk = (1 - PSI/35) × (Speed/300) × 1.5 + Critical_Penalties

Where:
  - PSI/35: Normalizes pressure (35 PSI is optimal)
  - Speed/300: Normalizes speed (300 km/h is extreme)
  - 1.5: Interaction amplification factor (nonlinear)

Critical Penalties:
  - If PSI < 15: Add 0.5 (blowout risk extreme)
  - If Speed > 40 AND PSI < 20: Add 0.3 (high-speed low-pressure)

Result: Risk score 0.0 (safe) to 1.0 (critical failure)
```

**Example Calculations**:
```
Scenario 1: Speed 100 km/h, PSI 32
  psi_factor = 1 - (32/35) = 0.086
  speed_factor = 100/300 = 0.333
  risk = 0.086 × 0.333 × 1.5 = 0.043 (4.3% - SAFE)

Scenario 2: Speed 200 km/h, PSI 20
  psi_factor = 1 - (20/35) = 0.429
  speed_factor = 200/300 = 0.667
  risk = 0.429 × 0.667 × 1.5 = 0.429 (42.9% - WARNING)
  + penalty for speed > 40 and PSI < 20: +0.3
  final_risk = 0.729 (72.9% - CRITICAL)

Scenario 3: Speed 300 km/h, PSI 0
  psi_factor = 1 - (0/35) = 1.0
  speed_factor = 300/300 = 1.0
  risk = 1.0 × 1.0 × 1.5 = 1.5 (capped at 1.0)
  + penalty for PSI < 15: +0.5
  final_risk = 1.0 (100% - BLOWOUT IMMINENT)
```

### Temperature-Speed Correlation Penalty

```
Expected Temperature Ranges:
  - Idle (0-20 km/h): 70-95°C
  - Moderate (20-100 km/h): 85-105°C
  - High Speed (>100 km/h): 90-110°C

Penalty Calculation:
  if temp < expected_min:
    deviation = expected_min - temp
    penalty = min(30, deviation × 1.5)
  elif temp > expected_max:
    deviation = temp - expected_max
    penalty = min(30, deviation × 1.2)
  else:
    penalty = 0

Example:
  Speed = 0 km/h, Temp = 85°C
  Expected: 70-95°C
  Deviation = 0 (within range)
  Penalty = 0

  Speed = 0 km/h, Temp = 50°C
  Expected: 70-95°C
  Deviation = 70 - 50 = 20°C
  Penalty = min(30, 20 × 1.5) = 30
```

### Contradiction Detection

```
CRITICAL Contradictions:
  1. Speed > 200 AND PSI < 20
     → CRITICAL_TIRE_FAILURE_RISK
  
  2. Speed > 150 AND Temp < 60
     → CRITICAL_ENGINE_SENSOR_FAILURE
  
  3. Speed > 180 AND PSI < 25
     → TIRE_PUNCTURE_RISK
  
  4. PSI < 5
     → TIRE_FLAT_OR_SENSOR_FAILURE
  
  5. Speed < 30 AND Temp > 115
     → COOLING_SYSTEM_FAILURE
  
  6. Temp increase > 10°C in 5 seconds
     → RAPID_TEMP_SPIKE
  
  7. PSI decrease > 2 PSI in 5 seconds
     → RAPID_PRESSURE_DROP

Emergency Status:
  is_emergency = (contradictions_count > 0) OR (tire_speed_risk > 0.5)
```

### Final Health Status Determination

```
if is_emergency OR contradictions > 0:
    status = "🚨 EMERGENCY"
elif score < 30:
    status = "🔴 CRITICAL"
elif score < 60:
    status = "🟡 FAIR"
elif score < 80:
    status = "🟢 GOOD"
else:
    status = "✅ EXCELLENT"
```

---

## Part 4: Complete Example Calculation

### Scenario: Speed 0 km/h, Temp 90°C, PSI 32 PSI

#### Step 1: Calculate Component Scores
```
Speed Score:
  speed = 0 km/h
  0 <= 120 → speed_score = 100

Temperature Score:
  temp = 90°C
  60 <= 90 <= 105 → temp_score = 100

Tire Pressure Score:
  psi = 32 PSI
  30 <= 32 <= 35 → psi_score = 100
```

#### Step 2: Calculate Base Score
```
base_score = (100 × 0.25) + (100 × 0.35) + (100 × 0.40)
           = 25 + 35 + 40
           = 100
```

#### Step 3: Calculate Tire-Speed Risk
```
psi_factor = 1 - (32/35) = 0.086
speed_factor = 0/300 = 0
risk = 0.086 × 0 × 1.5 = 0
tire_speed_risk_penalty = 100 × (1 - 0) = 0
```

#### Step 4: Calculate Temperature Correlation Penalty
```
speed = 0 km/h → expected range: 70-95°C
temp = 90°C
90 is within 70-95 → penalty = 0
```

#### Step 5: Check Contradictions
```
No contradictions detected
contradiction_penalty = 0
```

#### Step 6: Calculate Final Score
```
final_score = base_score - tire_speed_risk_penalty - temp_penalty - contradiction_penalty
            = 100 - 0 - 0 - 0
            = 100

Status: ✅ EXCELLENT (score >= 80)
```

---

## Part 5: Why Speed = 0 Causes Instability

### The Problem

When speed is set to 0, the simulated temperature fluctuates around 90°C with ±1.5°C noise:
- Sometimes: 88.5°C (within 70-95°C range) → penalty = 0
- Sometimes: 91.5°C (within 70-95°C range) → penalty = 0
- But occasionally: 95.5°C (above 95°C max) → penalty = 0.6

This causes the health score to fluctuate between 100 and 99.4, which appears as "EXCELLENT" to "GOOD" transitions.

### Root Cause

The temperature correlation penalty is too sensitive to small fluctuations at idle speed. The expected range (70-95°C) is narrow, and the noise (±1.5°C) can push the temperature outside this range.

### Solution

Implement **hysteresis** and **smoothing** to prevent rapid state changes:

1. **Hysteresis**: Only change status when score crosses threshold by 5+ points
2. **Smoothing**: Average health score over last 3 readings
3. **Idle Tolerance**: Increase temperature tolerance at idle speed

---

## Part 6: Recommendations for Different Vehicle Types

### To Adapt for Your Vehicle Type

If you want to use this system for a different vehicle, modify these values:

#### For SUV
```python
# In main.py, modify VehicleHealthAnalyzer.__init__():
self.TIRE_OPTIMAL_PSI = 33  # (was 32)
self.TIRE_CRITICAL_SPEED_LOW_PSI = 50  # (was 40)
self.ENGINE_TEMP_OPTIMAL_MIN = 85  # (was 80)
self.ENGINE_TEMP_OPTIMAL_MAX = 110  # (was 105)
```

#### For Sports Car
```python
self.TIRE_OPTIMAL_PSI = 30  # (was 32)
self.TIRE_CRITICAL_SPEED_LOW_PSI = 60  # (was 40)
self.ENGINE_TEMP_OPTIMAL_MIN = 90  # (was 80)
self.ENGINE_TEMP_OPTIMAL_MAX = 115  # (was 105)
```

#### For Truck
```python
self.TIRE_OPTIMAL_PSI = 90  # (was 32) - dual wheels
self.TIRE_CRITICAL_SPEED_LOW_PSI = 30  # (was 40)
self.ENGINE_TEMP_OPTIMAL_MIN = 80  # (was 80)
self.ENGINE_TEMP_OPTIMAL_MAX = 105  # (was 105)
```

---

## Summary

### Vehicle Type: Generic Mid-Size Sedan
- Tire Pressure: 30-35 PSI
- Engine Temp: 90-105°C optimal
- Max Speed: 180-200 km/h
- Weight: 1200-1400 kg

### Health Score Formula
```
Base = (Speed × 0.25) + (Temp × 0.35) + (PSI × 0.40)
Final = Base - Tire_Speed_Risk - Temp_Penalty - Contradiction_Penalty
```

### Why Speed = 0 is Unstable
- Temperature fluctuates around 90°C with ±1.5°C noise
- Expected range at idle is 70-95°C (narrow)
- Noise occasionally pushes temp outside range
- Causes health score to fluctuate

### Fix
- Implement hysteresis (5+ point threshold)
- Add smoothing (3-reading average)
- Increase idle temperature tolerance

---

**Document Version**: 1.0
**Date**: May 24, 2026
