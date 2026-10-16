
import folium
import pandas as pd

df = pd.read_csv("data/bins.csv")

SIZE = {
    "small": 5,
    "medium": 8,
    "large": 11,
    "bulk": 14
}

m = folium.Map(
    location=[df["lat"].mean(), df["lng"].mean()],
    zoom_start=16,
    tiles="OpenTopoMap"
)

for _, r in df.iterrows():
    folium.CircleMarker(
        location=[r["lat"], r["lng"]],
        radius=SIZE[r["size"]],
        color="#222222",
        weight=1,
        fill=True,
        fill_color="#2e9e5b",
        fill_opacity=0.85,
        tooltip=(
            f'{r["bin_id"]} | {r["name"]} | '
            f'{r["type"]} | {r["size"]} | {r["usage"]}'
        )
    ).add_to(m)

m.save("preview.html")

print("Map saved to preview.html")
