# Quick Start Guide

## Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the application**:
```bash
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

## Accessing the Dashboards

### 1. Telemetry Dashboard (Main)
- **URL**: http://localhost:8000/
- **Purpose**: View and control vehicle telemetry simulation
- **Features**:
  - Real-time gauges (Speed, Engine Temp, Tire Pressure)
  - Interactive sliders to adjust baseline values
  - Live telemetry feed
  - Connection status indicator

### 2. Vehicle Health Analysis Dashboard (New)
- **URL**: http://localhost:8000/analysis
- **Purpose**: Real-time vehicle health diagnostics
- **Features**:
  - Overall health score (0-100%)
  - Component-level analysis
  - Real-time metric cards
  - Diagnostic alerts
  - 60-second trend charts
  - Session statistics
  - CSV export

## How It Works

### Data Flow
```
Telemetry Simulator (main.py)
    ↓ (every 1 second)
Broadcast to all clients
    ├→ Telemetry Dashboard (visualization)
    └→ Analysis Engine (diagnostics)
        ↓
    Analysis Results
        ↓
    Analysis Dashboard (real-time display)
        ↓
    CSV Logging (data/analysis_*.csv)
```

### Analysis Window
- **Size**: 60 seconds of data
- **Update Rate**: 1 reading per second
- **Total Points**: 60 data points per metric

## Key Features

### 1. Real-time Health Scoring
- Calculates overall vehicle health (0-100%)
- Component scores for each metric
- Status: EXCELLENT, GOOD, FAIR, or CRITICAL

### 2. Trend Detection
- Identifies increasing/decreasing/stable trends
- Calculates rate of change
- Measures stability (0-100%)

### 3. Predictive Alerts
- Temperature: Rapid rise detection, overheating warnings
- Tire Pressure: Leak detection
- Speed: Excessive speed warnings
- Severity levels: INFO, WARNING, DANGER

### 4. Diagnostic Standards
- **Engine Temp**: SAE J1349 standards (80-110°C optimal)
- **Tire Pressure**: DOT TPMS standards (30-35 PSI optimal)
- **Speed**: OBD-II standards (0-120 km/h optimal)

## Using the Analysis Dashboard

### 1. Monitor Health Score
- Large gauge shows overall health percentage
- Color changes based on status
- Component bars show individual metric scores

### 2. View Real-time Metrics
- Three metric cards (Speed, Temperature, Tire Pressure)
- Shows current value, average, and trend
- Color-coded status indicators

### 3. Check Alerts
- Alerts appear in real-time
- Severity levels: INFO (blue), WARNING (amber), DANGER (red)
- Auto-scrolls to latest alerts
- Shows alert count

### 4. Analyze Trends
- Three charts show 60-second history
- Line graphs with data points
- Grid lines for reference
- Updates every second

### 5. Export Data
- Click "Download" button in Session Statistics
- Generates CSV file with complete analysis history
- File saved to `data/` directory
- Includes all metrics, status, trends, and alerts

## Adjusting Telemetry Values

1. Go to **Telemetry Dashboard** (http://localhost:8000/)
2. Use sliders to adjust baseline values:
   - Speed: 0-300 km/h
   - Engine Temp: 0-150°C
   - Tire Pressure: 0-60 PSI
3. Click "APPLY" to update
4. Analysis dashboard updates automatically

## Understanding the Analysis

### Health Score Calculation
```
Health Score = (Speed Score + Temp Score + PSI Score) / 3

Each component scores:
- 100 if in optimal range
- 70 if in warning range
- 30 if in danger range
```

### Status Indicators
- 🟢 **OPTIMAL**: Within safe operating range
- 🟡 **WARNING**: Approaching limits
- 🔴 **DANGER**: Critical condition
- 🔵 **COLD**: Engine not warmed up

### Trend Symbols
- ↑ **Increasing**: Value rising
- ↓ **Decreasing**: Value falling
- → **Stable**: Value stable

## CSV Data Format

Exported CSV includes:
- Timestamp
- Current values (speed, temp, pressure)
- Status for each metric
- Trend direction for each metric
- Overall health status
- Active alerts

Example row:
```
1234567890.123,85.5,92.3,32.1,optimal,optimal,optimal,→ stable,↑ increasing,→ stable,GOOD,NONE
```

## Troubleshooting

### Dashboard Not Loading
- Check if server is running: `http://localhost:8000/health`
- Try refreshing the page
- Check browser console for errors

### No Data Appearing
- Ensure telemetry dashboard is open (generates data)
- Check WebSocket connection status (green dot)
- Wait 5-10 seconds for data to accumulate

### Analysis WebSocket Disconnected
- Check network connection
- Verify firewall isn't blocking WebSocket
- Restart the application

### CSV Export Not Working
- Check `data/` directory exists
- Verify write permissions
- Check available disk space

## Performance Tips

- Keep analysis window at 60 seconds for optimal performance
- Close unused browser tabs to reduce memory usage
- Use Chrome/Firefox for best performance
- Monitor CSV file size (grows ~2KB per minute)

## Next Steps

1. **Explore the dashboards**: Spend time understanding the metrics
2. **Adjust values**: Use sliders to see how analysis responds
3. **Monitor alerts**: Observe when alerts trigger
4. **Export data**: Download CSV and analyze offline
5. **Customize thresholds**: Modify analysis.py for custom ranges

## Support

For issues or questions:
1. Check ANALYSIS_README.md for detailed documentation
2. Review the code comments in main.py
3. Check browser console for error messages
4. Verify all dependencies are installed

---

**Happy analyzing!** 🚗📊
