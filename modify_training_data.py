import pandas as pd
import numpy as np

csv_path = "data/vehicle_training_data.csv"
print(f"Loading {csv_path}...")
df = pd.read_csv(csv_path)

# Generate uniformly random fuel levels between 0.0 and 100.0
# We round to 1 decimal place to match the existing data format
print("Applying uniform random variance to fuel_level column...")
df['fuel_level'] = np.round(np.random.uniform(0.0, 100.0, size=len(df)), 1)

print("Injecting battery voltage anomalies into battery_voltage column...")
# Battery voltage is normally around 13.8V. We'll add some anomalies (10V to 16V).
anomaly_indices = np.random.choice(df.index, size=int(len(df) * 0.02), replace=False)
df.loc[anomaly_indices, 'battery_voltage'] = np.round(np.random.uniform(9.0, 16.0, size=len(anomaly_indices)), 1)

print("Saving modified dataset...")
df.to_csv(csv_path, index=False)
print("Done! You can now run train_model.py to retrain the IsolationForest.")
