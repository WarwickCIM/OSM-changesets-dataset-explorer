
#hotspots_finder.py

#
# This script identifies potential "hotspots" of controversial mapping activity in an OpenStreetMap changesets database using 
# clustering.
#
# 1. Connects to a DuckDB database containing a changesets table.
#    The required columns of the table are: changeset_id, uid, created, min_lat, max_lat, min_lon, max_lon, comment.
#
# 2. Computes the centroid (midpoint latitude/longitude) of each changeset’s bbox.
#
# 3. Bins those centroids into a regular latitude/longitude grid of size 'cell_deg' which is defined here as 0.01 degrees
# and then groups by weekly creation
#
# 4. For each grid cell + week, calculates: changesets_n: number of changesets in that cell during that week, 
# users_n: number of distinct users contributing changesets, keyword_hits: how many changeset comments contain controversy-related keywords
# (by default: revert, vandal, undo, dispute, wrong)
#
# 5. Assigns a simple "raw_score" that weights number of changesets, users, and keyword hits. Filters out cells with fewer than 
# 'min_changesets' or 'min_users'
#
# 6. Returns the top N hotspots ranked by raw_score (we set this to 10,000)
#
# 7. For each hotspot cell, also appends the geographic bounding box coordinates and saves the results to a CSV file (default path includes a timestamp).
#
# To use: 
# - Import and call 'find_hotspots()' in your own code, or run the script directly.
# - Adjust parameters such as grid size, thresholds, keyword regex, and date range.
# - Example: find_hotspots("osm_changesets.duckdb", "QueryResults/hotspots.csv")
#
# Output:
# - A CSV with hotspot rows, each containing: grid cell coordinates, week_start, counts of changesets/users/keyword hits, raw_score, 
# and bounding box string.
# ---------------------------------------------------------------------------


import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime

def find_hotspots(
    db_path: str,
    out_csv: str | None = None,
    cell_deg: float = 0.01,             # Around 1.1 km at equator
    min_changesets: int = 10,
    min_users: int = 3,
    limit: int = 10000,
    date_from: str | None = None,       # 'Hotspots' can be restricted by start and end date
    date_to: str | None = None,         
    keyword_regex: str = r"revert|vandal|undo|dispute|wrong", #Words used in comments to identify controversies 
):
    

    #This function runs clustering on the 'changesets' table of the database and saves hotspots to a CSV file.
    #The expected columns for the 'changesets' table are: changeset_id, uid, created, min_lat, max_lat, min_lon, max_lon, comment
    conn = duckdb.connect(db_path, read_only=True)
    conn.execute("SET TimeZone='UTC';")

    # Optional date filter
    date_filter = []
    if date_from:
        date_filter.append(f"created >= TIMESTAMP '{date_from} 00:00:00'")
    if date_to:
        date_filter.append(f"created < TIMESTAMP '{date_to} 00:00:00'")
    date_where = " AND " + " AND ".join(date_filter) if date_filter else ""

    # Use REGEXP_MATCH (boolean) + COUNT_IF or SUM for portability
    sql = f"""
    WITH params AS (SELECT {cell_deg}::DOUBLE AS cell_deg),

    centroids AS (
      SELECT
        changeset_id,
        uid,
        CAST(created AS TIMESTAMP) AS ts,
        (min_lat + max_lat)/2.0 AS lat,
        (min_lon + max_lon)/2.0 AS lon,
        comment
      FROM changesets
      WHERE min_lat IS NOT NULL AND max_lat IS NOT NULL
        AND min_lon IS NOT NULL AND max_lon IS NOT NULL
        {date_where}
    ),

    binned AS (
      SELECT
        changeset_id, uid, ts, comment, lat, lon,
        CAST(FLOOR(lat / p.cell_deg) * p.cell_deg AS DOUBLE) AS grid_lat,
        CAST(FLOOR(lon / p.cell_deg) * p.cell_deg AS DOUBLE) AS grid_lon,
        DATE_TRUNC('week', ts) AS week_start
      FROM centroids, params p
    ),

    cell_stats AS (
      SELECT
        grid_lat, grid_lon, week_start,
        COUNT(*)                                        AS changesets_n,
        COUNT(DISTINCT uid)                         AS users_n,
        SUM(CASE WHEN REGEXP_MATCHES(LOWER(COALESCE(comment, '')), '{keyword_regex}') THEN 1 ELSE 0 END) AS keyword_hits
      FROM binned
      GROUP BY 1,2,3
    ),

    scored AS (
      SELECT
        grid_lat, grid_lon, week_start,
        changesets_n, users_n, keyword_hits,
        (changesets_n * 1.0) + (users_n * 1.5) + (keyword_hits * 3.0) AS raw_score
      FROM cell_stats
    )

    SELECT
      grid_lat, grid_lon, week_start,
      changesets_n, users_n, keyword_hits, raw_score
    FROM scored
    WHERE changesets_n >= {min_changesets} AND users_n >= {min_users}
    ORDER BY raw_score DESC
    LIMIT {limit};
    """

    df = conn.execute(sql).fetch_df()

    # Adds bounding box columns for each cell, using the same cell size defined above
    df["min_lat"] = df["grid_lat"]
    df["max_lat"] = df["grid_lat"] + cell_deg
    df["min_lon"] = df["grid_lon"]
    df["max_lon"] = df["grid_lon"] + cell_deg
    df["bbox"] = df.apply(lambda r: f"{r['min_lon']},{r['min_lat']},{r['max_lon']},{r['max_lat']}", axis=1)

    # Creates an output CSV name
    if out_csv is None:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_csv = f"hotspots_{stamp}.csv"

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} hotspots → {out_path.resolve()}")
    return df

if __name__ == "__main__":
    # Edit the parameters for use
    find_hotspots(
        db_path="osm_changesets.duckdb",
        out_csv="QueryResults/hotspots.csv",
        cell_deg=0.01,
        min_changesets=10,
        min_users=3,
        limit=10000,
        date_from=None,  # Written as "2024-01-01"
        date_to=None,    # Written as "2024-01-01"
    )
