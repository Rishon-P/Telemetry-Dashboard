# 🔧 Troubleshooting Guide

## Issue: Analysis Dashboard Shows Empty Values (—)

### Root Cause
The analysis dashboard wasn't receiving data because the broadcaster wasn't running continuously.

### Solution Applied ✅
Updated `main.py` to:
1. **Always generate telemetry data** (not just when clients are connected)
2. **Always run analysis** (even if no analysis clients are connected)
3. **Send data to analysis clients** when they connect

### What Changed
```python
# BEFORE: Only generated data if clients were connected
if connected_clients or analysis_clients:
    snapshot = await state.get_snapshot()

# AFTER: Always generate data for continuous analysis
snapshot = await state.get_snapshot()

# And always run analysis
if analysis_clients:
    # Send to connected clients
else:
    # Keep analyzer running for when clients connect
    await analyzer.add_reading(snapshot)
```

---

## How to Use After Fix

### Step 1: Restart the Application
```bash
# Stop the current server (Ctrl+C)
# Then restart:
uvicorn main:app --reload
```

### Step 2: Open Analysis Dashboard
- Go to: http://localhost:8000/analysis
- You should now see data appearing immediately

### Step 3: Verify Data is Flowing
1. Open browser console (F12)
2. Look for messages like: `Analysis message received: analysis`
3. Check that values are updating (not showing "—")

---

## Debugging Steps

### If Still Empty:

#### 1. Check Backend is Running
```bash
# In another terminal, test the health endpoint:
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

#### 2. Check Browser Console
- Press F12 to open developer tools
- Go to Console tab
- Look for any error messages
- Should see: `Analysis WebSocket connected`

#### 3. Check Network Tab
- Press F12 → Network tab
- Look for WebSocket connection to `/ws/data-analysis`
- Should show status: `101 Switching Protocols`

#### 4. Check Server Logs
- Look at the terminal where you ran `uvicorn`
- Should see messages like:
  ```
  Analysis client XXX connected. Total: 1
  ```

---

## Common Issues & Solutions

### Issue 1: "DISCONNECTED" Status
**Problem**: WebSocket shows disconnected  
**Solution**:
1. Check firewall isn't blocking WebSocket
2. Verify backend is running
3. Try refreshing the page
4. Check browser console for errors

### Issue 2: Values Still Show "—"
**Problem**: Data not updating  
**Solution**:
1. Wait 5-10 seconds for data to accumulate
2. Check browser console for errors
3. Verify WebSocket is connected (green dot)
4. Restart the application

### Issue 3: High CPU Usage
**Problem**: Server using too much CPU  
**Solution**:
1. This is normal during startup (building 60-second window)
2. Should stabilize after 60 seconds
3. If persists, check for browser memory leaks

### Issue 4: CSV File Not Created
**Problem**: No CSV files in `data/` directory  
**Solution**:
1. Check `data/` directory exists
2. Verify write permissions: `ls -la data/`
3. Check disk space: `df -h`
4. Restart application

---

## What Should Happen Now

### On Analysis Dashboard Load:
1. ✅ WebSocket connects (green dot appears)
2. ✅ Health score gauge shows value (not "—")
3. ✅ Metric cards show current values
4. ✅ Values update every second
5. ✅ Alerts appear if conditions warrant
6. ✅ Charts populate with data

### In Browser Console:
```
Analysis WebSocket connected
Analysis message received: analysis
Analysis message received: analysis
...
```

### In Server Terminal:
```
Analysis client 12345 connected. Total: 1
```

---

## Testing the Fix

### Quick Test:
1. Open http://localhost:8000/analysis
2. Wait 5 seconds
3. Check if values appear (not "—")
4. Open browser console (F12)
5. Should see: `Analysis message received: analysis`

### Full Test:
1. Open analysis dashboard
2. Adjust telemetry values on main dashboard
3. Watch analysis dashboard update in real-time
4. Check alerts trigger appropriately
5. Export CSV and verify data

---

## Performance After Fix

| Metric | Expected |
|--------|----------|
| Data appears | Immediately |
| Updates | Every 1 second |
| Latency | < 50ms |
| CPU | < 5% |
| Memory | ~5KB per client |

---

## If Issues Persist

### 1. Check Logs
```bash
# Look for errors in server output
# Should see: "Analysis client X connected"
```

### 2. Verify Backend
```bash
# Test health endpoint
curl http://localhost:8000/health

# Should return:
# {"status":"ok"}
```

### 3. Check WebSocket
- Open browser DevTools (F12)
- Go to Network tab
- Filter by "WS"
- Should see `/ws/data-analysis` connection

### 4. Restart Everything
```bash
# Stop server (Ctrl+C)
# Close all browser tabs
# Restart server
# Open fresh browser window
# Go to http://localhost:8000/analysis
```

---

## Summary of Changes

✅ **Fixed**: Broadcaster now runs continuously  
✅ **Fixed**: Analysis engine always processes data  
✅ **Fixed**: Data available immediately on dashboard load  
✅ **Added**: Console logging for debugging  
✅ **Verified**: Syntax and functionality  

**Status**: Ready to use! 🎉

---

**If you still have issues, check:**
1. Browser console (F12)
2. Server terminal output
3. Network tab (F12 → Network)
4. Verify backend is running

**Happy analyzing!** 🚗📊
