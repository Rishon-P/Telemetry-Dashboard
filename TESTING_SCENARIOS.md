# Physics-Based Analysis Testing Scenarios

## Quick Test Guide

### How to Test the New Physics-Based System

1. **Start the Dashboard**:
   ```bash
   # Terminal 1: Start the server
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   
   # Terminal 2: Open browser
   # Telemetry: http://localhost:8000
   # Analysis: http://localhost:8000/analysis
   ```

2. **Set Extreme Values** (via telemetry dashboard):
   - Use the WebSocket interface to set baseline values
   - Or modify values in the telemetry dashboard UI

---

## Test Scenarios

### Scenario 1: CRITICAL - High Speed + Zero Tire Pressure
**Expected Behavior**: EMERGENCY status with blowout warning

```
Set Values:
- Speed: 300 km/h
- Tire Pressure: 0 PSI
- Engine Temp: 90°C

Expected Results:
✓ Health Score: 0 (CRITICAL)
✓ Status: 🚨 EMERGENCY (red pulsing)
✓ Contradictions: CRITICAL_TIRE_FAILURE_RISK
✓ Tire-Speed Risk: 100%
✓ Alerts:
  - 🚨 EMERGENCY: TIRE BLOWOUT IMMINENT - Reduce speed immediately!
  - 🛞 CRITICAL_PRESSURE: Tire flat or severely under-inflated
  - 🚨 EXCESSIVE_SPEED: Vehicle speed exceeds safe limits
```

---

### Scenario 2: CRITICAL - High Speed + Cold Engine
**Expected Behavior**: EMERGENCY status with sensor failure warning

```
Set Values:
- Speed: 200 km/h
- Tire Pressure: 32 PSI
- Engine Temp: 45°C

Expected Results:
✓ Health Score: 15-25 (CRITICAL)
✓ Status: 🚨 EMERGENCY (red pulsing)
✓ Contradictions: CRITICAL_ENGINE_SENSOR_FAILURE
✓ Temp Correlation Penalty: 30 points
✓ Alerts:
  - 🚨 EMERGENCY: Engine sensor malfunction or engine failure detected
  - ❄️ COLD_ENGINE: Engine not warmed up - Check ignition
  - ⚠️ EXCESSIVE_SPEED: Vehicle speed exceeds safe limits
```

---

### Scenario 3: CRITICAL - Low Speed + Engine Overheating
**Expected Behavior**: CRITICAL status with cooling system failure

```
Set Values:
- Speed: 20 km/h
- Tire Pressure: 32 PSI
- Engine Temp: 120°C

Expected Results:
✓ Health Score: 30-40 (CRITICAL)
✓ Status: 🔴 CRITICAL
✓ Contradictions: COOLING_SYSTEM_FAILURE
✓ Alerts:
  - 🔥 CRITICAL: Cooling system failure - Engine overheating at low speed
  - 🔥 OVERHEATING: Engine temperature critical - Pull over safely
```

---

### Scenario 4: WARNING - High Speed + Low Pressure
**Expected Behavior**: FAIR status with tire-speed mismatch warning

```
Set Values:
- Speed: 180 km/h
- Tire Pressure: 22 PSI
- Engine Temp: 95°C

Expected Results:
✓ Health Score: 40-50 (FAIR)
✓ Status: 🟡 FAIR
✓ Contradictions: TIRE_PUNCTURE_RISK
✓ Tire-Speed Risk: 45-55%
✓ Alerts:
  - ⚠️ CRITICAL: Tire puncture risk - Pressure dropping at high speed
  - ⚠️ TIRE_SPEED_WARNING: Reduce speed or increase tire pressure
  - ⚠️ UNDER_INFLATED: Tire pressure below optimal
```

---

### Scenario 5: NORMAL - Safe Highway Driving
**Expected Behavior**: EXCELLENT status with no alerts

```
Set Values:
- Speed: 100 km/h
- Tire Pressure: 32 PSI
- Engine Temp: 95°C

Expected Results:
✓ Health Score: 85-95 (EXCELLENT)
✓ Status: ✅ EXCELLENT
✓ Contradictions: None
✓ Tire-Speed Risk: 5%
✓ Alerts: None
```

---

### Scenario 6: GOOD - Moderate Speed + Slightly Low Pressure
**Expected Behavior**: GOOD status with under-inflation warning

```
Set Values:
- Speed: 80 km/h
- Tire Pressure: 28 PSI
- Engine Temp: 92°C

Expected Results:
✓ Health Score: 70-80 (GOOD)
✓ Status: 🟢 GOOD
✓ Contradictions: None
✓ Tire-Speed Risk: 8%
✓ Alerts:
  - ⚠️ UNDER_INFLATED: Tire pressure below optimal
```

---

### Scenario 7: CRITICAL - Flat Tire Detection
**Expected Behavior**: CRITICAL status with flat tire alert

```
Set Values:
- Speed: 50 km/h
- Tire Pressure: 3 PSI
- Engine Temp: 90°C

Expected Results:
✓ Health Score: 5-15 (CRITICAL)
✓ Status: 🔴 CRITICAL
✓ Contradictions: TIRE_FLAT_OR_SENSOR_FAILURE
✓ Alerts:
  - 🛞 CRITICAL_PRESSURE: Tire flat or severely under-inflated
  - 🛞 LOW_PRESSURE: Tire pressure dangerously low
```

---

### Scenario 8: EMERGENCY - Multiple Contradictions
**Expected Behavior**: EMERGENCY status with multiple system failures

```
Set Values:
- Speed: 250 km/h
- Tire Pressure: 15 PSI
- Engine Temp: 55°C

Expected Results:
✓ Health Score: 0-10 (CRITICAL)
✓ Status: 🚨 EMERGENCY (red pulsing)
✓ Contradictions: 
  - CRITICAL_TIRE_FAILURE_RISK
  - CRITICAL_ENGINE_SENSOR_FAILURE
  - TIRE_PUNCTURE_RISK
✓ Tire-Speed Risk: 85%+
✓ Temp Correlation Penalty: 30
✓ Multiple emergency alerts
```

---

## Verification Checklist

### Visual Indicators
- [ ] Emergency status shows red pulsing animation
- [ ] Contradictions appear in fixed overlay (top-right)
- [ ] Health score updates smoothly with animation
- [ ] Component bars update in real-time
- [ ] Alerts appear with correct severity colors

### Physics Calculations
- [ ] Tire-speed risk increases nonlinearly with speed and low pressure
- [ ] Temperature correlation penalty applies correctly
- [ ] Contradictions detected for all impossible combinations
- [ ] Health score reflects all penalties correctly

### Alert System
- [ ] Emergency alerts appear for critical contradictions
- [ ] Alerts are sorted by severity
- [ ] Max 10 alerts displayed (older ones removed)
- [ ] Alert text is clear and actionable

### CSV Logging
- [ ] New CSV file created with all fields
- [ ] All analysis data logged correctly
- [ ] Contradictions and physics metrics recorded

---

## Performance Notes

- **Update Frequency**: 1 reading per second
- **Rolling Window**: 60 seconds of data
- **Calculation Time**: < 10ms per analysis
- **Memory Usage**: ~2MB per session
- **CSV File Size**: ~50KB per hour of data

---

## Known Limitations

1. **Sensor Accuracy**: System assumes sensors are accurate. Real vehicles may have sensor drift.
2. **Load Factor**: Current system doesn't account for vehicle load (affects tire pressure and engine temp).
3. **Ambient Temperature**: Doesn't adjust thresholds for ambient temperature changes.
4. **Vehicle Type**: Thresholds are generic; real vehicles have manufacturer-specific ranges.
5. **Acceleration**: Doesn't factor in acceleration/deceleration effects on engine temp.

---

## Troubleshooting

### Issue: Health score not updating
- Check WebSocket connection (should show "CONNECTED")
- Verify data is being sent from telemetry dashboard
- Check browser console for errors

### Issue: No contradictions detected
- Verify values are extreme enough to trigger thresholds
- Check the contradiction detection logic in main.py
- Review the thresholds in PHYSICS_ANALYSIS_GUIDE.md

### Issue: Alerts not appearing
- Check alert generation logic in _generate_alerts()
- Verify alert container is visible in HTML
- Check CSS for alert styling

### Issue: CSV file not created
- Verify data/ directory exists
- Check file permissions
- Review CSV logging error messages in server logs

---

## Next Steps

1. **Test all scenarios** listed above
2. **Verify physics calculations** match expected results
3. **Check visual indicators** for emergency states
4. **Review CSV logs** for data accuracy
5. **Adjust thresholds** if needed for your vehicle type
6. **Document any issues** for future improvements

---

**Last Updated**: May 24, 2026
**System Version**: 2.0 (Physics-Based Analysis)
