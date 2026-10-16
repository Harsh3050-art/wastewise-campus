
import pandas as pd

df = pd.read_csv("data/bins.csv")

df = df.drop(columns=["data_source"], errors="ignore")
df = df.drop(columns=["zone"], errors="ignore")

cols = [
    "bin_id",
    "name",
    "lat",
    "lng",
    "type",
    "size",
    "capacity_litres",
    "usage"
]

df = df[cols]

df.to_csv("data/bins.csv", index=False)

print(df.shape, "bins saved to data/bins.csv")
print(df.columns.tolist())
