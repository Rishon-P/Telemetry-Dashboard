import pickle
import numpy as np
from pathlib import Path

scaler_path = Path("/home/rishon-pravin/Desktop/telemetry-dashboard/vehicle_scaler.pkl")
model_path = Path("/home/rishon-pravin/Desktop/telemetry-dashboard/vehicle_anomaly_model.pkl")

with open(scaler_path, "rb") as f:
    scaler = pickle.load(f)
with open(model_path, "rb") as f:
    model = pickle.load(f)

baselines = {
    "speed_kmh": 80.0,
    "engine_rpm": 1500.0,
    "throttle_pct": 20.0,
    "engine_load_pct": 35.0,
    "maf_g_sec": 2.0,  # User input
    "engine_temp_c": 90.0,
    "oil_pressure_psi": 45.0,
    "battery_voltage_v": 13.8,
    "fuel_level_pct": 85.0,
    "tire_pressure_fl_psi": 32.0,
    "tire_pressure_fr_psi": 32.0,
    "tire_pressure_rl_psi": 32.0,
    "tire_pressure_rr_psi": 32.0,
}

feature_names = [
    "speed", "rpm", "throttle", "engine_load", "maf", 
    "engine_temp", "oil_pressure", "battery_voltage", "fuel_level", 
    "tp_fl", "tp_fr", "tp_rl", "tp_rr"
]

feature_mapping = {
    "speed_kmh": "speed",
    "engine_rpm": "rpm",
    "throttle_pct": "throttle",
    "engine_load_pct": "engine_load",
    "maf_g_sec": "maf",
    "engine_temp_c": "engine_temp",
    "oil_pressure_psi": "oil_pressure",
    "battery_voltage_v": "battery_voltage",
    "fuel_level_pct": "fuel_level",
    "tire_pressure_fl_psi": "tp_fl",
    "tire_pressure_fr_psi": "tp_fr",
    "tire_pressure_rl_psi": "tp_rl",
    "tire_pressure_rr_psi": "tp_rr",
}

feature_values = []
for feature_name in feature_names:
    telemetry_key = None
    for tel_key, feat_name in feature_mapping.items():
        if feat_name == feature_name:
            telemetry_key = tel_key
            break
    feature_values.append(baselines.get(telemetry_key, 0))

X = np.array(feature_values).reshape(1, -1)
X_scaled = scaler.transform(X)

prediction = int(model.predict(X_scaled)[0])
print(f"Prediction: {prediction}")
if prediction == -1:
    abs_scaled = np.abs(X_scaled[0])
    max_dev_index = np.argmax(abs_scaled)
    print(f"Root cause: {feature_names[max_dev_index]}")
    for i, name in enumerate(feature_names):
        print(f"  {name}: value={X[0][i]}, scaled={X_scaled[0][i]:.2f}")
