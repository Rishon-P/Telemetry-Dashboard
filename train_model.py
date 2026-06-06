"""
Vehicle Anomaly Detection Model Training Script
================================================
Reads vehicle_training_data.csv, normalizes the telemetry data using StandardScaler,
and trains an IsolationForest model to detect anomalies in vehicle behavior.

Exports:
- vehicle_scaler.pkl: Fitted StandardScaler for feature normalization
- vehicle_anomaly_model.pkl: Trained IsolationForest anomaly detection model
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import joblib
from pathlib import Path

print("=" * 80)
print("Vehicle Anomaly Detection Model Training")
print("=" * 80)

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Load the training data
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 1] Loading vehicle training data...")

csv_path = Path(__file__).parent / "data" / "vehicle_training_data.csv"

try:
    df = pd.read_csv(csv_path)
    print(f"✓ Successfully loaded {csv_path}")
    print(f"  • Dataset shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  • Columns: {', '.join(df.columns.tolist())}")
except FileNotFoundError:
    print(f"✗ Error: File not found at {csv_path}")
    exit(1)
except Exception as e:
    print(f"✗ Error loading CSV: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Remove timestamp column if it exists
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 2] Cleaning data - removing timestamp column if present...")

if 'timestamp' in df.columns:
    df = df.drop('timestamp', axis=1)
    print(f"✓ Dropped 'timestamp' column")
    print(f"  • Remaining columns: {df.shape[1]}")
else:
    print(f"ℹ No 'timestamp' column found - proceeding with existing columns")

print(f"  • Final columns for training: {', '.join(df.columns.tolist())}")

# Check for empty dataframe
if df.empty:
    print("✗ Error: DataFrame is empty after removing timestamp")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Handle missing values
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 3] Handling missing values...")

missing_count = df.isnull().sum().sum()
if missing_count > 0:
    print(f"✓ Found {missing_count} missing values - filling with 0")
    df = df.fillna(0)
else:
    print(f"✓ No missing values found")

print(f"  • Data statistics:")
print(f"    - Min: {df.min().min():.2f}")
print(f"    - Max: {df.max().max():.2f}")
print(f"    - Mean: {df.mean().mean():.2f}")

# ==========================================
# DATA AUGMENTATION (Realistic Engineering Tolerances)
# ==========================================
print("\n[Data Augmentation] Injecting real-world mechanical noise...")

# We hard-code realistic standard deviations so the AI doesn't panic over normal vibrations
engineering_tolerances = {
    'battery_voltage': 0.5,   # +/- 0.5V normal driving fluctuation
    'oil_pressure': 2.0,      # +/- 2.0 PSI normal vibration
    'engine_temp': 2.0,       # +/- 2.0 Degrees
    'rpm': 100.0,
    'speed': 2.0,
    'throttle': 2.0,
    'engine_load': 2.0,
    'maf': 2.0,
    'fuel_level': 1.0,
    'tp_fl': 1.0, 'tp_fr': 1.0, 'tp_rl': 1.0, 'tp_rr': 1.0
}

FEATURE_NAMES = ['speed', 'rpm', 'throttle', 'engine_load', 'maf', 'engine_temp', 'oil_pressure', 'battery_voltage', 'fuel_level', 'tp_fl', 'tp_fr', 'tp_rl', 'tp_rr']

for col in FEATURE_NAMES:
    if col in df.columns:
        std_dev = engineering_tolerances.get(col, 1.0)
        # Inject realistic Gaussian noise
        noise = np.random.normal(0, std_dev, size=len(df))
        df[col] = df[col] + noise

print("✓ Applied realistic mechanical noise to training data.")

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Normalize features using StandardScaler
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 4] Normalizing features using StandardScaler...")

scaler = StandardScaler()

try:
    X_scaled = scaler.fit_transform(df)
    print(f"✓ Successfully fitted and transformed data")
    print(f"  • Scaler fitted on {len(df.columns)} features")
    print(f"  • Scaled data shape: {X_scaled.shape}")
    print(f"  • Scaled data statistics:")
    print(f"    - Mean: {X_scaled.mean():.6f} (should be ~0)")
    print(f"    - Std Dev: {X_scaled.std():.6f} (should be ~1)")
except Exception as e:
    print(f"✗ Error during scaling: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Train IsolationForest model
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 5] Training IsolationForest anomaly detection model...")

try:
    iso_forest = IsolationForest(
        contamination=0.01,
        random_state=42,
        n_estimators=100,
        n_jobs=-1
    )
    
    iso_forest.fit(X_scaled)
    print(f"✓ Successfully trained IsolationForest model")
    print(f"  • Contamination: 0.01 (1% expected anomalies)")
    print(f"  • Number of estimators: 100")
    print(f"  • Random state: 42")
    
    # Get anomaly predictions and statistics
    predictions = iso_forest.predict(X_scaled)
    anomalies = (predictions == -1).sum()
    normals = (predictions == 1).sum()
    
    print(f"  • Model predictions on training data:")
    print(f"    - Normal samples: {normals} ({normals/len(predictions)*100:.2f}%)")
    print(f"    - Anomalous samples: {anomalies} ({anomalies/len(predictions)*100:.2f}%)")
    
except Exception as e:
    print(f"✗ Error training model: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Export scaler to joblib
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 6] Exporting StandardScaler to vehicle_scaler.pkl...")

scaler_path = Path(__file__).parent / "vehicle_scaler.pkl"

try:
    joblib.dump(scaler, scaler_path)
    print(f"✓ Successfully saved scaler")
    print(f"  • File: {scaler_path}")
    print(f"  • File size: {scaler_path.stat().st_size / 1024:.2f} KB")
except Exception as e:
    print(f"✗ Error saving scaler: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Export model to joblib
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 7] Exporting IsolationForest model to vehicle_anomaly_model.pkl...")

model_path = Path(__file__).parent / "vehicle_anomaly_model.pkl"

try:
    joblib.dump(iso_forest, model_path)
    print(f"✓ Successfully saved anomaly detection model")
    print(f"  • File: {model_path}")
    print(f"  • File size: {model_path.stat().st_size / 1024:.2f} KB")
except Exception as e:
    print(f"✗ Error saving model: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 8: Verification
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 8] Verifying exported files...")

try:
    # Load and verify scaler
    loaded_scaler = joblib.load(scaler_path)
    print(f"✓ Scaler verification:")
    print(f"  • Loaded successfully from {scaler_path}")
    print(f"  • Feature names: {loaded_scaler.get_feature_names_out(df.columns).tolist()}")
    
    # Load and verify model
    loaded_model = joblib.load(model_path)
    print(f"✓ Model verification:")
    print(f"  • Loaded successfully from {model_path}")
    print(f"  • Model type: {type(loaded_model).__name__}")
    print(f"  • Number of estimators: {loaded_model.n_estimators}")
    print(f"  • Contamination: {loaded_model.contamination}")
    
except Exception as e:
    print(f"✗ Error during verification: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Complete
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("✓ Training Complete!")
print("=" * 80)
print(f"\nGenerated Files:")
print(f"  1. {scaler_path.name} - StandardScaler for feature normalization")
print(f"  2. {model_path.name} - IsolationForest anomaly detection model")
print(f"\nTraining Summary:")
print(f"  • Training samples: {len(df)}")
print(f"  • Feature dimensions: {len(df.columns)}")
print(f"  • Features used: {', '.join(df.columns.tolist())}")
print(f"  • Model contamination rate: 5%")
print(f"  • Expected anomalies detected: ~{int(len(df) * 0.05)} samples")
print("\nNext Steps:")
print(f"  • Load the scaler and model in your prediction script using joblib")
print(f"  • Use scaler.transform() to normalize new telemetry data")
print(f"  • Use model.predict() to detect anomalies (-1 = anomaly, 1 = normal)")
print("\n")
