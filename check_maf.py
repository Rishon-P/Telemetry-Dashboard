import pandas as pd

df = pd.read_csv("data/vehicle_training_data.csv")
print("MAF Stats:")
print(df["maf"].describe())
