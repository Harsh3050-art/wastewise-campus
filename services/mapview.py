import folium

STATUS_COLOR = {"green": "#2e9e5b", "yellow": "#f2b01e", "red": "#d64545"}
TYPE_COLOR = {"wet": "#8B5A2B", "dry": "#1F3FBF", "recyclable": "#17BECF",
              "ewaste": "#7B3FE4", "hazardous": "#111111"}
TYPE_LETTER = {"wet": "W", "dry": "D", "recyclable": "R", "ewaste": "E", "hazardous": "H"}
TYPE_LABEL = {"wet": "Wet", "dry": "Dry", "recyclable": "Recyclable",
              "ewaste": "E-waste", "hazardous": "Hazardous"}
SIZE_PX = {"small": 18, "medium": 24, "large": 30, "bulk": 38}
FONT_PX = {"small": 9, "medium": 11, "large": 13, "bulk": 15}

LEGEND = """
<div style="position:fixed;bottom:18px;left:12px;z-index:9999;background:rgba(255,255,255,.95);
padding:8px 10px;border:1px solid #999;border-radius:8px;font:12px Arial,sans-serif;line-height:1.5">
<b>Fill level</b><br>
<span style="color:#2e9e5b">&#9679;</span> under 50% &nbsp;
<span style="color:#f2b01e">&#9679;</span> 50-80% &nbsp;
<span style="color:#d64545">&#9679;</span> 80%+<br>
<b>Bin type</b> (ring + letter)<br>
W wet (brown) | D dry (blue) | R recyclable (cyan)<br>
E e-waste (purple) | H hazardous (black)<br>
<b>Red badge</b> = open reports<br>
<b>Size</b> = bin capacity
</div>
"""


def marker_html(r):
    d = SIZE_PX[r["size"]]
    text = "#111" if r["status"] == "yellow" else "#fff"
    circle = (
        f'<div style="box-sizing:border-box;width:{d}px;height:{d}px;border-radius:50%;'
        f'background:{STATUS_COLOR[r["status"]]};border:3px solid {TYPE_COLOR[r["type"]]};'
        f'display:flex;align-items:center;justify-content:center;color:{text};'
        f'font:700 {FONT_PX[r["size"]]}px Arial,sans-serif;box-shadow:0 0 4px rgba(0,0,0,.5);">'
        f'{TYPE_LETTER[r["type"]]}</div>'
    )
    n = int(r.get("open_reports", 0) or 0)
    badge = ""
    if n > 0:
        badge = (
            f'<div style="position:absolute;top:-7px;right:-7px;min-width:16px;height:16px;'
            f'padding:0 3px;box-sizing:border-box;border-radius:8px;background:#d64545;color:#fff;'
            f'border:1px solid #fff;font:700 10px Arial,sans-serif;display:flex;'
            f'align-items:center;justify-content:center;">{n}</div>'
        )
    return f'<div style="position:relative;width:{d}px;height:{d}px;">{circle}{badge}</div>'

def build_map(df, center, zoom, selected=None):
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap", control_scale=True)
    for _, r in df.iterrows():
        d = SIZE_PX[r["size"]]
        folium.Marker(
            [r["lat"], r["lng"]],
            icon=folium.DivIcon(html=marker_html(r), icon_size=(d, d),
                                icon_anchor=(d // 2, d // 2)),
            tooltip=f'{r["name"]} | {TYPE_LABEL[r["type"]]} | '
                    f'{r["fill_pct"]:.0f}% full | {r["eta_text"]}',
        ).add_to(m)
    if selected:
        row = df[df["bin_id"] == selected]
        if not row.empty:
            r = row.iloc[0]
            folium.CircleMarker([r["lat"], r["lng"]], radius=SIZE_PX[r["size"]] // 2 + 9,
                                color="#000000", weight=3, fill=False).add_to(m)
    m.get_root().html.add_child(folium.Element(LEGEND))
    return m


def nearest_bin(df, lat, lng, max_deg=0.00015):
    if df.empty:
        return None
    d = (df["lat"] - lat) ** 2 + (df["lng"] - lng) ** 2
    i = d.idxmin()
    return df.loc[i, "bin_id"] if d[i] <= max_deg ** 2 else None