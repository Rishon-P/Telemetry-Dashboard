import pickle
import numpy as np
import joblib

scaler = joblib.load("vehicle_scaler.pkl")
model = joblib.load("vehicle_anomaly_model.pkl")

# baseline feature order:
# ["speed", "rpm", "throttle", "engine_load", "maf", "engine_temp", "oil_pressure", "battery_voltage", "fuel_level", "tp_fl", "tp_fr", "tp_rl", "tp_rr"]

features = [80.0, 1500.0, 20.0, 35.0, 45.0, 90.0, 45.0, 10.0, 85.0, 32.0, 32.0, 32.0, 32.0]
X = np.array(features).reshape(1, -1)
X_scaled = scaler.transform(X)

pred = model.predict(X_scaled)[0]
score = model.score_samples(X_scaled)[0]
print(f"Prediction for 10V battery: {pred} (score: {score})")
