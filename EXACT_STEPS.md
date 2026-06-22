# 🎯 EXACT STEPS TO GET DATA - FOLLOW PRECISELY

## ✅ Backend is Working
The analysis engine is confirmed working. The issue is likely the browser not receiving data.

---

## 📋 EXACT STEPS (Do These in Order)

### Step 1: Stop the Current Server
```
In the terminal where the server is running:
Press: Ctrl+C

Wait for it to stop completely.
```

### Step 2: Navigate to Project Directory
```bash
cd /home/rishon-pravin/Desktop/telemetry-dashboard
```

### Step 3: Start Fresh Server
```bash
uvicorn main:app --reload
```

**Wait for this message:**
```
Uvicorn running on http://127.0.0.1:8000
```

### Step 4: Open Browser - IMPORTANT
```
Open a FRESH browser window (not a tab)
Go to: http://localhost:8000/analysis
```

### Step 5: Open Browser Console
```
Press: F12 (or right-click → Inspect)
Click: Console tab
```

### Step 6: Look for These Messages
You should see in the console:
```
🔌 Connecting to: ws://localhost:8000/ws/data-analysis
✅ WebSocket OPEN
📨 Message #1: {"type": "analysis", "timestamp": ...
📊 Message type: analysis
✅ Processing analysis data
📈 Current values: {speed_kmh: 85.5, engine_temp_c: 92.3, ...}
📊 Health score: {score: 100, status: "EXCELLENT", ...}
✅ Dashboard updated successfully
```

### Step 7: Check Dashboard
The dashboard should now show:
- ✅ Health score: 100% (not "—")
- ✅ Speed: ~80 km/h (not "—")
- ✅ Temperature: ~90°C (not "—")
- ✅ Tire Pressure: ~32 PSI (not "—")

---

## 🔍 If Still Empty - Troubleshooting

### Check 1: Is Server Running?
In console, run:
```javascript
fetch('http://localhost:8000/health').then(r => r.json()).then(console.log)
```
Should show: `{status: "ok"}`

### Check 2: Is WebSocket Connecting?
Look in browser console for:
```
✅ WebSocket OPEN
```

If you see:
```
❌ WebSocket CLOSED
```
Then the connection is failing. Check:
- Is server running?
- Is port 8000 available?
- Any firewall blocking?

### Check 3: Is Data Being Sent?
Look for:
```
📨 Message #1:
📨 Message #2:
...
```

If you don't see these, the broadcaster isn't sending data.

### Check 4: Browser Cache
Sometimes old code is cached:
```
Press: Ctrl+Shift+R (hard refresh)
```

---

## 🚨 If STILL Not Working

### Option 1: Check Server Terminal
Look at the terminal where the server is running. You should see:
```
Analysis client 12345 connected. Total: 1
```

If you don't see this, the WebSocket isn't connecting.

### Option 2: Check Network Tab
In browser DevTools:
1. Click: Network tab
2. Filter: WS (WebSocket)
3. Look for: `/ws/data-analysis`
4. Should show: Status 101 (Switching Protocols)

If it shows red or 404, the WebSocket connection failed.

### Option 3: Restart Everything
```bash
# 1. Stop server (Ctrl+C)
# 2. Close all browser tabs
# 3. Close browser completely
# 4. Restart server:
uvicorn main:app --reload
# 5. Open fresh browser window
# 6. Go to: http://localhost:8000/analysis
```

---

## ✅ Expected Timeline

| Time | What Happens |
|------|--------------|
| 0s | Page loads, WebSocket connects |
| 1s | First data arrives, health score shows |
| 2-5s | Metric cards populate |
| 10s | Trends appear, charts start |
| 60s | Full 60-second history visible |

---

## 📝 What Each Console Message Means

| Message | Meaning |
|---------|---------|
| `🔌 Connecting to:` | Browser trying to connect to WebSocket |
| `✅ WebSocket OPEN` | Connection successful |
| `📨 Message #1:` | Data received from server |
| `📊 Message type: analysis` | Correct message type |
| `✅ Processing analysis data` | Data being processed |
| `📈 Current values:` | Actual telemetry values |
| `✅ Dashboard updated` | Display updated |

---

## 🎯 Quick Checklist

- [ ] Server stopped
- [ ] Fresh server started with `uvicorn main:app --reload`
- [ ] Fresh browser window opened
- [ ] Went to `http://localhost:8000/analysis`
- [ ] Opened browser console (F12)
- [ ] See `✅ WebSocket OPEN` message
- [ ] See `📨 Message #1:` message
- [ ] Dashboard shows values (not "—")

---

## 💡 Pro Tips

1. **Keep console open** while testing - you'll see all messages
2. **Don't use old tabs** - open fresh browser window
3. **Hard refresh** if nothing changes: `Ctrl+Shift+R`
4. **Check server terminal** for connection messages
5. **Look for errors** in console (red text)

---

## 🆘 Still Not Working?

If you've done all these steps and still see empty values:

1. **Copy the console output** (all the messages)
2. **Copy the server terminal output** (all the logs)
3. **Tell me exactly what you see**

This will help me diagnose the exact issue.

---

**Follow these steps exactly and data should appear!** 🚗📊
