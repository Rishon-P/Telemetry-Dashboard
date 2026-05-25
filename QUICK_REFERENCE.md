# Quick Reference Guide - Dashboard Modifications

## 1. Session Statistics ✅

**What Changed**: Statistics now display real-time data

**Where**: Session Statistics section (middle of dashboard)

**What You See**:
- **Session Duration**: Real-time elapsed time (e.g., "2m 45s")
- **Data Points Collected**: Number of readings (0-60)
- **Analysis Window**: Always 60 seconds

**Example**:
```
Session Duration: 2m 45s
Data Points Collected: 60
Analysis Window: 60 seconds
```

---

## 2. Contradiction Alerts ✅

**What Changed**: Alerts now appear ONLY during live events and disappear when normal

**Where**: Top-right corner of screen

**Behavior**:
- ✅ Appears when dangerous conditions detected
- ✅ Disappears automatically when conditions normalize
- ✅ Red color with pulsing animation for visibility
- ✅ Shows list of detected contradictions

**Example Scenarios**:

**Scenario A: High Speed + Low Pressure**
```
Speed: 200 km/h
Tire Pressure: 15 PSI
Result: 🚨 ALERT APPEARS
        • CRITICAL_TIRE_FAILURE_RISK
        • TIRE_PUNCTURE_RISK
```

**Scenario B: Conditions Normalize**
```
Speed: 100 km/h
Tire Pressure: 32 PSI
Result: 🚨 ALERT DISAPPEARS (smooth animation)
```

---

## 3. Service Center Recommendation ✅

**What Changed**: New section tells you whether to continue or visit service center

**Where**: New section between Alerts and Session Statistics

**Status Levels**:

| Status | Icon | Meaning | Action |
|--------|------|---------|--------|
| EMERGENCY | 🚨 | Critical failure | STOP - Go to service center immediately |
| CRITICAL | 🔴 | Serious issues | Reduce speed, go to service center soon |
| WARNING | 🟡 | Issues detected | Schedule service within 24 hours |
| GOOD | 🟢 | Minor issues | Continue, schedule routine maintenance |
| EXCELLENT | ✅ | All systems OK | Continue journey safely |

**What It Shows**:
- Overall Health Score (0-100)
- Number of Critical Issues
- Specific Recommendation

**Example**:
```
🚨 IMMEDIATE SERVICE REQUIRED
Overall Health: 5/100 (🚨 EMERGENCY)
Critical Issues: 2 issues
Recommendation: ⚠️ STOP VEHICLE - Take to service center immediately
```

---

## 4. CSV Download Information ✅

**What Changed**: Download button now shows where files are saved

**Where**: Session Statistics section, "Download" button

**What Happens When You Click**:
1. Button shows "EXPORTING..."
2. Green notification appears (bottom-right)
3. Shows file location and access methods
4. Auto-dismisses after 8 seconds

**File Information**:
```
File: analysis_[timestamp].csv
Location: /data/ directory
Server Path: /home/rishon-pravin/Desktop/telemetry-dashboard/data/

Access via:
• Browser: Download folder
• Terminal: cd data/ && ls -la
```

**Example File Names**:
- `analysis_20260524_190945.csv`
- `analysis_20260524_191023.csv`
- `analysis_20260524_191101.csv`

---

## How to Test All Features

### Test 1: Session Statistics
1. Open dashboard
2. Watch Session Duration increase every second
3. Watch Data Points increase (up to 60)
4. ✅ Both should update in real-time

### Test 2: Contradiction Alerts
1. Set Speed: 250 km/h
2. Set Tire Pressure: 10 PSI
3. ✅ Red alert appears in top-right
4. Set Speed: 80 km/h
5. Set Tire Pressure: 32 PSI
6. ✅ Red alert disappears smoothly

### Test 3: Service Recommendation
1. Set extreme values (Speed 300, PSI 0)
2. ✅ Recommendation shows "IMMEDIATE SERVICE REQUIRED"
3. Set normal values (Speed 100, PSI 32)
4. ✅ Recommendation shows "EXCELLENT - Vehicle is safe"

### Test 4: CSV Download
1. Click "Download" button
2. ✅ Button shows "EXPORTING..."
3. ✅ Green notification appears with file location
4. ✅ Notification auto-dismisses after 8 seconds

---

## Troubleshooting

### Issue: Statistics still blank
**Solution**: 
- Refresh the page
- Check WebSocket connection (should show "CONNECTED")
- Check browser console for errors

### Issue: Contradictions not disappearing
**Solution**:
- Ensure values are within normal ranges
- Check that health score is above 80
- Refresh page if stuck

### Issue: Service recommendation not updating
**Solution**:
- Verify WebSocket is connected
- Check that analysis data is being received
- Refresh page

### Issue: Download notification not showing
**Solution**:
- Check that WebSocket is connected
- Verify browser allows notifications
- Check browser console for errors

---

## CSV File Location

**Server Path**: 
```
/home/rishon-pravin/Desktop/telemetry-dashboard/data/
```

**Access Methods**:

**Method 1: Terminal**
```bash
cd /home/rishon-pravin/Desktop/telemetry-dashboard/data/
ls -la                    # List all CSV files
cat analysis_*.csv        # View file contents
```

**Method 2: File Manager**
```
Navigate to: /home/rishon-pravin/Desktop/telemetry-dashboard/data/
```

**Method 3: Browser Download**
- Files are automatically saved to your Downloads folder
- File name format: `analysis_[YYYYMMDD_HHMMSS].csv`

---

## CSV File Contents

Each CSV file contains:
- Timestamp
- Speed (km/h)
- Engine Temperature (°C)
- Tire Pressure (PSI)
- Status for each metric
- Trends for each metric
- Overall health score
- Health status
- Emergency flag
- Contradictions detected
- Tire-speed risk percentage
- Temperature correlation penalty
- All alerts

**Example Row**:
```
2026-05-24 19:09:45.123, 89.2, 95.3, 32.1, optimal, optimal, optimal, 
→ stable, stable, stable, 92.5, EXCELLENT, False, NONE, 5.2, 0.0, NONE
```

---

## Key Metrics Explained

### Health Score (0-100)
- **80-100**: Excellent - Vehicle is safe
- **60-80**: Good - Minor issues, routine maintenance
- **30-60**: Fair - Schedule service soon
- **0-30**: Critical - Immediate service needed

### Tire-Speed Risk (0-100%)
- **0-20%**: Safe
- **20-40%**: Caution
- **40-70%**: Warning
- **70-100%**: Critical

### Temperature Correlation Penalty (0-30)
- **0**: Perfect correlation
- **5-10**: Minor deviation
- **10-20**: Significant deviation
- **20-30**: Critical deviation

---

## Common Scenarios

### Scenario 1: Normal Highway Driving
```
Speed: 100 km/h
Temp: 95°C
PSI: 32 PSI

Result:
✅ Health: EXCELLENT (92/100)
✅ Recommendation: Continue journey safely
✅ No alerts
✅ No contradictions
```

### Scenario 2: Tire Pressure Warning
```
Speed: 120 km/h
Temp: 98°C
PSI: 26 PSI

Result:
🟡 Health: GOOD (75/100)
🟡 Recommendation: Schedule service within 24 hours
⚠️ Alert: UNDER_INFLATED
✅ No contradictions
```

### Scenario 3: Emergency Condition
```
Speed: 250 km/h
Temp: 50°C
PSI: 12 PSI

Result:
🚨 Health: EMERGENCY (5/100)
🚨 Recommendation: STOP VEHICLE - Take to service center immediately
🚨 Alerts: Multiple emergency alerts
🚨 Contradictions: CRITICAL_TIRE_FAILURE_RISK, CRITICAL_ENGINE_SENSOR_FAILURE
```

---

## Performance Notes

- Session statistics update every 1 second
- Contradictions check every 1 second
- Service recommendation updates every 1 second
- CSV export is instant
- No performance impact on dashboard

---

## Support

For detailed information, see:
- `MODIFICATIONS_SUMMARY.md` - Technical details
- `PHYSICS_ANALYSIS_GUIDE.md` - Physics algorithms
- `TESTING_SCENARIOS.md` - Test cases

---

**Last Updated**: May 24, 2026
**Dashboard Version**: 2.1 (With Modifications)
