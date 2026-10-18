
from services.mapview import marker_html, nearest_bin
from services.bins import get_all_bins

df = get_all_bins()

print("Total active bins:", len(df))

if not df.empty:
    print("\nFirst bin marker HTML:")
    print(marker_html(df.iloc[0]))

    first = df.iloc[0]
    nearest = nearest_bin(df, first["lat"], first["lng"])
    print("\nNearest bin:", nearest)
