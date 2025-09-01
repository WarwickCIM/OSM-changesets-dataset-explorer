#map_hotspots.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path

#Mitigation for cartopy library errors
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except Exception:
    HAS_CARTOPY = False

#Paths to save hotspot images
CSV_PATH = "QueryResults/hotspots.csv"
OUT_POINTS = "QueryResults/hotspots_points.png"
OUT_CARTOPY = "QueryResults/hotspots_cartopy.png"

#Convert pandas series to numeric values
def coerce_float(series, name):
    try:
        return pd.to_numeric(series, errors="coerce")
    except Exception:
        raise ValueError(f"Column {name} cannot be converted to numeric.")

#The function below does the following: 
# Read the latitudes and longitudes from the CSV file, ensure each of them are numbers,
#drop any null values from the rows, fix the inverted boxes where minimum and maximum lat/long are swapped,
#Compute the centroids of the lat/long bounding boxes, filter out impossible ranges,
#drop cells that will not be visible on the cartopy image to avoid noise, 
#chose another column for the .csv file for colour coding the cartopy map,
#plot the centroids
def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Read {len(df)} rows from {CSV_PATH}")
    required = ["min_lat","max_lat","min_lon","max_lon"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"CSV missing required column: {c}")

    # Ensure numeric
    for c in required:
        df[c] = coerce_float(df[c], c)

    #Drop rows with NaNs
    before = len(df)
    df = df.dropna(subset=required).copy()
    print(f"Dropped {before - len(df)} rows with NaNs in bbox columns; remaining: {len(df)}")

    #Fix inverted boxes by swapping
    inv_lat = df["min_lat"] > df["max_lat"]
    inv_lon = df["min_lon"] > df["max_lon"]
    if inv_lat.any():
        print(f"Fixing {inv_lat.sum()} rows with inverted lat bounds")
        tmp = df.loc[inv_lat, "min_lat"].copy()
        df.loc[inv_lat, "min_lat"] = df.loc[inv_lat, "max_lat"]
        df.loc[inv_lat, "max_lat"] = tmp
    if inv_lon.any():
        print(f"Fixing {inv_lon.sum()} rows with inverted lon bounds")
        tmp = df.loc[inv_lon, "min_lon"].copy()
        df.loc[inv_lon, "min_lon"] = df.loc[inv_lon, "max_lon"]
        df.loc[inv_lon, "max_lon"] = tmp

    #compute centroid and area (deg^2)
    df["cent_lat"] = (df["min_lat"] + df["max_lat"]) / 2.0
    df["cent_lon"] = (df["min_lon"] + df["max_lon"]) / 2.0
    df["width_deg"] = (df["max_lon"] - df["min_lon"]).abs()
    df["height_deg"] = (df["max_lat"] - df["min_lat"]).abs()
    df["area_deg2"] = df["width_deg"] * df["height_deg"]

    #Filter out impossible ranges
    bad_range = (
        (df["min_lat"] < -90) | (df["max_lat"] > 90) |
        (df["min_lon"] < -180) | (df["max_lon"] > 180)
    )
    if bad_range.any():
        print(f"Dropping {bad_range.sum()} rows with out-of-range coordinates")
        df = df.loc[~bad_range].copy()

    # Drop zero-area boxes
    zero_area = df["area_deg2"] == 0
    if zero_area.any():
        print(f"Dropping {zero_area.sum()} rows with zero-area bboxes")
        df = df.loc[~zero_area].copy()

    if df.empty:
        raise RuntimeError("No valid rows to plot after cleaning.")

    #Optionally chose a Score column for colour coding the produced map
    score_col = None
    for c in ["raw_score","users_n","changesets_n","keyword_hits"]:
        if c in df.columns:
            score_col = c
            break
    if score_col is None:
        df["raw_score"] = 1.0
        score_col = "raw_score"

    print("Summary after cleaning:")
    print(df[[ "min_lon","max_lon","min_lat","max_lat","cent_lon","cent_lat","width_deg","height_deg","area_deg2" ]].describe())
    print(f"Using {score_col} for colouring. "
          f"Score range: {df[score_col].min()} .. {df[score_col].max()}")

    # Produce one plot that contains just the centroid points
    Path(OUT_POINTS).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    ax.scatter(df["cent_lon"], df["cent_lat"], s=6, alpha=0.9)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    #Set the extend with padding
    lon_min, lon_max = df["cent_lon"].min(), df["cent_lon"].max()
    lat_min, lat_max = df["cent_lat"].min(), df["cent_lat"].max()
    lon_pad = max(0.1, (lon_max - lon_min) * 0.1)
    lat_pad = max(0.1, (lat_max - lat_min) * 0.1)
    ax.set_xlim(lon_min - lon_pad, lon_max + lon_pad)
    ax.set_ylim(lat_min - lat_pad, lat_max + lat_pad)
    ax.set_title("Hotspot centroids (quick check)")
    plt.tight_layout()
    plt.savefig(OUT_POINTS, bbox_inches="tight")
    print(f"Saved points plot → {Path(OUT_POINTS).resolve()}")

    # Produce a cartopy map with the redtangle bounding boxes
    if not HAS_CARTOPY:
        print("Cartopy not available; skipping basemap plot.")
        return

    import matplotlib.colors as mcolors
    import matplotlib.cm as cm

    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax = plt.axes(projection=proj)

    #Extent with padding
    lon_min, lon_max = df["min_lon"].min(), df["max_lon"].max()
    lat_min, lat_max = df["min_lat"].min(), df["max_lat"].max()
    lon_pad = max(0.5, (lon_max - lon_min) * 0.05)
    lat_pad = max(0.5, (lat_max - lat_min) * 0.05)
    ax.set_extent([lon_min - lon_pad, lon_max + lon_pad, lat_min - lat_pad, lat_max + lat_pad], crs=proj)

    #Add Basemap features
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f6f6f6", zorder=0)
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#eaf3ff", zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6, zorder=2)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4, linestyle=":", zorder=2)

    #Define colour scale
    vals = df[score_col].astype(float).values
    vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
    if vmax == vmin:
        vmax = vmin + 1.0
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap("viridis")

    #Draw rectangles of bounding boxes with thick edges
    for _, r in df.iterrows():
        color = cmap(norm(float(r[score_col])))
        rect = Rectangle(
            (r["min_lon"], r["min_lat"]),
            r["width_deg"], r["height_deg"],
            facecolor=color, edgecolor="k",
            linewidth=0.7, alpha=0.55,
            transform=proj, zorder=3
        )
        ax.add_patch(rect)

    #Draw bbox centroids on the same map
    ax.scatter(df["cent_lon"], df["cent_lat"], s=4, color="k", alpha=0.7, transform=proj, zorder=4)

    #Add a colourbar for the map
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation="vertical", pad=0.02, shrink=0.8)
    cbar.set_label(f"Hotspot intensity ({score_col})")

    ax.set_title("OSM Changeset Hotspots")
    plt.tight_layout()
    plt.savefig(OUT_CARTOPY, bbox_inches="tight")
    print(f"Saved cartopy map → {Path(OUT_CARTOPY).resolve()}")

if __name__ == "__main__":
    main()
