
import pandas as pd

df = pd.read_csv("data/bins.csv")

print(df.shape, "bins")
print(df.isna().sum())

cols = [
    "bin_id", "name", "lat", "lng",
    "type", "size", "capacity_litres", "usage"
]

assert df.columns.tolist() == cols, "wrong columns"
assert df["bin_id"].is_unique, "duplicate bin_id"

assert df["type"].isin(
    ["wet", "dry", "recyclable", "ewaste", "hazardous"]
).all(), "bad type"

assert df["size"].isin(
    ["small", "medium", "large", "bulk"]
).all(), "bad size"

assert df["usage"].isin(
    ["low", "medium", "high", "very high"]
).all(), "bad usage"

assert df["lat"].between(29.8, 29.95).all(), "lat looks wrong"
assert df["lng"].between(77.85, 77.95).all(), "lng looks wrong"

size_cap = {
    "small": 40,
    "medium": 120,
    "large": 240,
    "bulk": 1100
}

assert (
    df["size"].map(size_cap) == df["capacity_litres"]
).all(), "size and capacity do not match"

print(df["type"].value_counts(), "\n")
print(df["size"].value_counts(), "\n")

print("bins.csv looks good")
