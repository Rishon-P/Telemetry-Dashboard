# Auto-Drive Data Recording Modification

## Summary
Modified the telemetry dashboard to only record vehicle data to `vehicle_training_data.csv` when the **Auto-Drive toggle is turned ON**. When Auto-Drive is OFF, no data is recorded to the CSV file.

## Changes Made

### 1. Backend (main.py)

#### Added auto_drive_enabled flag to SimulationState class
- Added `self.auto_drive_enabled = False` to the `__init__` method
- This flag tracks whether auto-drive mode is currently active

#### Modified _log_to_csv() method in VehicleHealthAnalyzer class
- Added check: `if not state.auto_drive_enabled: return`
- Data is only written to CSV when auto-drive is enabled
- This prevents recording during manual mode

#### Added toggle_auto_drive action handler in WebSocket endpoint
- New action: `"toggle_auto_drive"`
- Toggles the `state.auto_drive_enabled` flag
- Sends acknowledgment back to client with current auto-drive status

#### Modified CSV writing in WebSocket handler
- Added condition: `if state.auto_drive_enabled:` before writing to CSV
- Ensures bulk_update data is only recorded when auto-drive is active

### 2. Frontend (static/app.js)

#### Modified Auto-Drive button click handler
- Added WebSocket message: `ws.send(JSON.stringify({ action: "toggle_auto_drive" }))`
- When user clicks the toggle button, it now sends the action to the backend
- Backend updates the auto_drive_enabled flag and starts/stops recording

## How It Works

1. **User clicks "Toggle Auto-Drive" button**
   - Frontend sends `{ action: "toggle_auto_drive" }` to backend
   - Button UI updates to show ON/OFF status
   - Sliders are disabled/enabled accordingly

2. **Backend receives toggle action**
   - Toggles `state.auto_drive_enabled` flag
   - Sends acknowledgment to frontend

3. **Data Recording**
   - When auto-drive is ON: All telemetry data is recorded to `vehicle_training_data.csv`
   - When auto-drive is OFF: No data is written to the CSV file
   - This applies to both:
     - Analysis data (from VehicleHealthAnalyzer)
     - Bulk update data (from WebSocket messages)

## Testing

To verify the changes:

1. Start the application
2. Click "Toggle Auto-Drive: OFF" to turn it ON
3. Observe that data starts being recorded to `data/vehicle_training_data.csv`
4. Click "Toggle Auto-Drive: ON" to turn it OFF
5. Verify that no new data is being written to the CSV file
6. Check the CSV file to confirm only data from when auto-drive was ON is present

## Files Modified

- `/home/rishon-pravin/Desktop/telemetry-dashboard/main.py`
- `/home/rishon-pravin/Desktop/telemetry-dashboard/static/app.js`

## Backward Compatibility

- The changes are fully backward compatible
- Existing CSV files are not affected
- The auto-drive toggle defaults to OFF, so no data is recorded until explicitly enabled
