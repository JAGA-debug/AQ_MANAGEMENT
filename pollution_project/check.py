import pandas as pd

df = pd.read_csv("data.csv")

print("COLUMNS IN DATASET:")
print(df.columns)

print("\nFIRST 5 ROWS:")
print(df.head())