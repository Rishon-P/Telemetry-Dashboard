"""
Vehicle Anomaly Detection Prediction Script
=============================================
Demonstrates how to load the trained models and detect anomalies
in new telemetry data.

Usage:
    python3 predict_anomalies.py
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

print("=" * 80)
print("Vehicle Anomaly Detection - Prediction Pipeline")
print("=" * 80)

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Load the pre-trained models
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 1] Loading pre-trained models...")

scaler_path = Path(__file__).parent / "vehicle_scaler.pkl"
model_path = Path(__file__).parent / "vehicle_anomaly_model.pkl"

try:
    scaler = joblib.load(scaler_path)
    print(f"✓ Loaded StandardScaler from {scaler_path.name}")
    
    anomaly_model = joblib.load(model_path)
    print(f"✓ Loaded IsolationForest model from {model_path.name}")
except FileNotFoundError as e:
    print(f"✗ Error: Model files not found. Please run train_model.py first.")
    print(f"  Missing: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Load new telemetry data
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 2] Loading test telemetry data...")

csv_path = Path(__file__).parent / "data" / "vehicle_training_data.csv"

try:
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {csv_path.name}")
    print(f"  • Dataset shape: {df.shape[0]} rows × {df.shape[1]} columns")
except FileNotFoundError:
    print(f"✗ Error: Test data file not found at {csv_path}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Clean and prepare data
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 3] Preparing data for prediction...")

# Remove timestamp if exists
if 'timestamp' in df.columns:
    df = df.drop('timestamp', axis=1)
    print(f"✓ Removed timestamp column")

# Handle missing values
missing = df.isnull().sum().sum()
if missing > 0:
    df = df.fillna(0)
    print(f"✓ Filled {missing} missing values with 0")
else:
    print(f"✓ No missing values found")

print(f"  • Final data shape: {df.shape}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Normalize features using the fitted scaler
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 4] Normalizing features with StandardScaler...")

X_scaled = scaler.transform(df)
print(f"✓ Scaled {X_scaled.shape[0]} samples × {X_scaled.shape[1]} features")
print(f"  • Mean: {X_scaled.mean():.6f}")
print(f"  • Std Dev: {X_scaled.std():.6f}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Make predictions
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 5] Running anomaly detection...")

# Get binary predictions
predictions = anomaly_model.predict(X_scaled)

# Get anomaly scores
anomaly_scores = anomaly_model.score_samples(X_scaled)

print(f"✓ Predictions complete")

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Analyze results
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 6] Analyzing results...")

# Count predictions
normal_count = (predictions == 1).sum()
anomaly_count = (predictions == -1).sum()
normal_pct = (normal_count / len(predictions)) * 100
anomaly_pct = (anomaly_count / len(predictions)) * 100

print(f"✓ Prediction Summary:")
print(f"  • Normal samples: {normal_count} ({normal_pct:.2f}%)")
print(f"  • Anomalous samples: {anomaly_count} ({anomaly_pct:.2f}%)")

# Anomaly score statistics
print(f"\n✓ Anomaly Score Statistics:")
print(f"  • Mean score: {anomaly_scores.mean():.6f}")
print(f"  • Std Dev: {anomaly_scores.std():.6f}")
print(f"  • Min score: {anomaly_scores.min():.6f} (most anomalous)")
print(f"  • Max score: {anomaly_scores.max():.6f} (most normal)")

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Extract and display anomalies
# ─────────────────────────────────────────────────────────────────────────────
print("\n[Step 7] Extracting anomalous samples...")

# Create results dataframe
results_df = df.copy()
results_df['prediction'] = predictions
results_df['anomaly_score'] = anomaly_scores
results_df['is_anomaly'] = (predictions == -1)

# Get anomalies
anomalies = results_df[results_df['is_anomaly']].copy()
anomalies = anomalies.sort_values('anomaly_score')  # Most anomalous first

print(f"✓ Found {len(anomalies)} anomalies")

# Display top 10 most anomalous samples
if len(anomalies) > 0:
    print(f"\n  Top 10 Most Anomalous Samples:")
    print(f"  {'-' * 75}")
    
    for idx, (i, row) in enumerate(anomalies.head(10).iterrows(), 1):
        print(f"  {idx}. Index {i} | Score: {row['anomaly_score']:.6f}")
        # Show feature values
        feature_str = " | ".join([
            f"{col}: {row[col]:.2f}" 
            for col in ['speed', 'rpm', 'throttle', 'engine_load', 'engine_temp']
        ])
        print(f"     {feature_str}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 8: Save results to CSV
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[Step 8] Saving prediction results...")

results_path = Path(__file__).parent / "anomaly_predictions.csv"
results_df.to_csv(results_path, index=False)
print(f"✓ Saved all predictions to {results_path.name}")

anomalies_path = Path(__file__).parent / "detected_anomalies.csv"
anomalies.to_csv(anomalies_path, index=False)
print(f"✓ Saved anomalies to {anomalies_path.name}")

# ─────────────────────────────────────────────────────────────────────────────
# Complete
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("✓ Prediction Pipeline Complete!")
print("=" * 80)

print(f"\nGenerated Files:")
print(f"  1. anomaly_predictions.csv - All predictions with scores")
print(f"  2. detected_anomalies.csv - Only anomalous samples")

print(f"\nKey Findings:")
print(f"  • {normal_pct:.2f}% of samples are normal")
print(f"  • {anomaly_pct:.2f}% of samples are anomalous")
print(f"  • Most anomalous score: {anomaly_scores.min():.6f}")
print(f"  • Least anomalous score: {anomaly_scores.max():.6f}")

print(f"\nHow to Interpret Results:")
print(f"  • Prediction = 1: Normal vehicle behavior")
print(f"  • Prediction = -1: Unusual/anomalous behavior")
print(f"  • Lower scores: More likely to be anomalous")
print(f"  • Higher scores: More likely to be normal")

print(f"\nNext Steps:")
print(f"  1. Review detected_anomalies.csv for unusual patterns")
print(f"  2. Investigate root causes of detected anomalies")
print(f"  3. Retrain model if anomalies are legitimate patterns")
print(f"  4. Integrate this prediction pipeline into main.py")

print("\n")
