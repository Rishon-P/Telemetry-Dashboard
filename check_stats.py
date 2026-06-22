import pandas as pd

df = pd.read_csv("data/vehicle_training_data.csv")
print("Battery Voltage Stats:")
print(df["battery_voltage"].describe())
print("\nOil Pressure Stats:")
print(df["oil_pressure"].describe())
