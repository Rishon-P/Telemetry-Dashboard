# 📊 Understanding the 60-Second Window

## What Does "60-Second Window" Mean?

The **60-second window** is a **rolling buffer** that keeps the last 60 data points (readings) from the vehicle telemetry.

### Visual Explanation

```
Time: 0s    10s   20s   30s   40s   50s   60s   70s   80s   90s
      |-----|-----|-----|-----|-----|-----|-----|-----|-----|
Data: [1]   [2]   [3]   [4]   [5]   [6]   [7]   [8]   [9]   [10]

At 60 seconds:
Window contains: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ..., 60]
(60 data points)

At 70 seconds:
Window contains: [2, 3, 4, 5, 6, 7, 8, 9, 10, ..., 60, 61]
(oldest point [1] is removed, newest point [61] is added)
```

## How It Works

### 1. Data Collection
- **Update Frequency**: 1 reading per second (1 Hz)
- **Window Size**: 60 readings
- **Total Time**: 60 seconds of data

### 2. Rolling Buffer (FIFO)
```python
# Python deque with maxlen=60
speed_window = deque(maxlen=60)

# When new data arrives:
speed_window.append(85.5)  # Add new reading

# When buffer is full (60 items):
# Oldest item automatically removed
# New item added
# Always maintains exactly 60 items
```

### 3. Analysis on Window
```
For each new reading:
1. Add reading to window
2. Calculate statistics on all 60 readings:
   - Average
   - Min/Max
   - Trend (direction, rate of change)
   - Stability (standard deviation)
3. Generate alerts based on current + trend
4. Calculate health score
5. Send to dashboard
```

## Why 60 Seconds?

### Industry Standard
- **Tesla Fleet API**: 500ms intervals (120 readings/minute)
- **Predictive Maintenance**: 30-120 reading windows
- **Vehicle Diagnostics**: Real-time analysis on rolling windows

### Optimal Balance
- **Too Short** (< 30s): Not enough data for trend detection
- **Too Long** (> 120s): Delayed response to changes
- **Just Right** (60s): Perfect for real-time diagnostics

## What You See in Dashboard

### Health Score
```
Calculated from last 60 readings:
- Speed average over 60 seconds
- Temperature average over 60 seconds
- Tire pressure average over 60 seconds
```

### Trends
```
Calculated from last 60 readings:
- Direction: Is it increasing/decreasing/stable?
- Rate: How fast is it changing?
- Stability: How consistent is it?
```

### Charts
```
Display all 60 data points:
- X-axis: Time (0-60 seconds)
- Y-axis: Value (speed/temp/pressure)
- Shows complete history of last minute
```

## Real-World Example

### Scenario: Engine Temperature Rising

```
Time    Temp    Status      Trend           Action
0s      90°C    OPTIMAL     → stable        None
10s     91°C    OPTIMAL     ↑ increasing    Monitor
20s     92°C    OPTIMAL     ↑ increasing    Monitor
30s     93°C    OPTIMAL     ↑ increasing    Monitor
40s     94°C    OPTIMAL     ↑ increasing    Monitor
50s     95°C    OPTIMAL     ↑ increasing    Monitor
60s     96°C    OPTIMAL     ↑ increasing    Monitor
70s     97°C    OPTIMAL     ↑ increasing    Monitor
80s     98°C    OPTIMAL     ↑ increasing    Monitor
90s     99°C    OPTIMAL     ↑ increasing    Monitor
100s    100°C   OPTIMAL     ↑ increasing    Monitor
110s    105°C   WARNING     ↑ rapid rise    ALERT!
```

The 60-second window allows the system to:
1. Detect the trend early (increasing)
2. Calculate rate of change (0.5°C per 10 seconds)
3. Predict when it will reach warning threshold
4. Alert before critical condition

---

## The Real Problem (Now Fixed)

### What Was Wrong
The analysis WebSocket endpoint was **blocking on `receive_text()`**:

```python
# WRONG - Blocks waiting for client message
while True:
    raw = await ws.receive_text()  # ← BLOCKS HERE
    # ... process message
```

This meant:
- ❌ Server waited for client to send a message
- ❌ Broadcaster couldn't send data to the client
- ❌ Dashboard received nothing
- ❌ All values showed "—"

### The Fix
Changed to use **timeout** so connection stays open:

```python
# CORRECT - Uses timeout, allows broadcaster to send data
while True:
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
        # ... process message
    except asyncio.TimeoutError:
        # Timeout is normal - broadcaster sends data anyway
        continue
```

This means:
- ✅ Connection stays open
- ✅ Broadcaster can send data anytime
- ✅ Client receives data every second
- ✅ Dashboard shows real values

---

## How Data Flows Now

```
1. Broadcaster generates snapshot every 1 second
   ↓
2. Broadcaster calls analyzer.add_reading(snapshot)
   ↓
3. Analyzer adds to 60-second window
   ↓
4. Analyzer calculates analysis (status, trends, alerts, health)
   ↓
5. Broadcaster sends to all analysis_clients
   ↓
6. Dashboard receives and updates display
   ↓
7. User sees real-time data
```

---

## After the Fix

### What You Should See

**Immediately on load:**
- ✅ WebSocket connects (green dot)
- ✅ Health score shows value (not "—")
- ✅ Metric cards show current values

**After 10 seconds:**
- ✅ Trends start showing
- ✅ Charts begin populating

**After 60 seconds:**
- ✅ Full 60-second history in charts
- ✅ Accurate trend analysis
- ✅ Stable health score

---

## Summary

| Aspect | Details |
|--------|---------|
| **Window Size** | 60 data points |
| **Update Rate** | 1 reading per second |
| **Total Time** | 60 seconds of history |
| **Type** | Rolling FIFO buffer |
| **Purpose** | Trend detection & analysis |
| **Industry Standard** | Yes (30-120 reading windows) |

The 60-second window is the **perfect balance** between having enough data for accurate analysis while maintaining real-time responsiveness.

---

**Status**: ✅ Fixed - Data should now flow correctly!
