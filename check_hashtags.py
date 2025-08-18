# Analysis of the hashtags
import duckdb, pandas as pd
import folium
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import numpy as np

#Open a connection to our database
con = duckdb.connect("osm_changesets.duckdb")

#Get the most common hashtags in the database
top = con.execute("""
SELECT hashtag, COUNT(*) AS n
FROM changeset_hashtags
GROUP BY 1
ORDER BY n DESC
LIMIT 50
""").df()

#Get all the hashtags organised by month in descending order
by_month = con.execute("""
SELECT hashtag,
       strftime(created, '%Y-%m') AS ym,
       COUNT(*) AS n
FROM changeset_hashtags
GROUP BY 1,2
ORDER BY ym, n DESC
""").df()
con.close()
print(top.head())
print(by_month.head())

#Search the users who have used a specific hashtag between certain dates and order them in descending order
tag = "mapcork".lower()
users = con.execute("""
SELECT uid, user, COUNT(*) AS n,
       MIN(created) AS first_seen, MAX(created) AS last_seen
FROM changeset_hashtags
WHERE hashtag = ?
GROUP BY 1,2
ORDER BY n DESC
""",[tag]).df()
con.close()
print(users.head(20))

# Searching for hashtags that typically occur in tags (frequency greater than 20) and order them in descending order of use frequency
import duckdb
co = con.execute("""
SELECT a.hashtag AS h1, b.hashtag AS h2, COUNT(*) AS n
FROM changeset_hashtags a
JOIN changeset_hashtags b
  ON a.changeset_id = b.changeset_id
 AND a.hashtag < b.hashtag      -- avoid duplicates and self-pairs
GROUP BY 1,2
HAVING n >= 20                  -- threshold to reduce noise
ORDER BY n DESC
LIMIT 2000
""").df()
con.close()
print(co.head())

# Mapping all hashtags onto a latitude/longitude map
con.execute("""
CREATE OR REPLACE VIEW hashtag_points AS
SELECT h.hashtag,
       h.created,
       h.changeset_id,
       h.uid, h.user,
       (c.min_lat + c.max_lat)/2.0 AS lat,
       (c.min_lon + c.max_lon)/2.0 AS lon
FROM changeset_hashtags h
JOIN changesets c USING (changeset_id)
WHERE c.min_lat IS NOT NULL AND c.min_lon IS NOT NULL
""")
points = con.execute("""
SELECT hashtag, created, lat, lon
FROM hashtag_points
WHERE hashtag = 'mapcork'
""").df()
con.close()

# Adding a heatmap to plot spatial occurence of hashtags
m = folium.Map(location=[20,0], zoom_start=2, tiles="OpenStreetMap")
HeatMap(points[['lat','lon']].values.tolist(), radius=6, blur=10).add_to(m)
m.save("mapcork_heatmap.html")
print("Saved mapcork_heatmap.html")

# Adding trend visualisations to plot hashtags over time
tag_trend = by_month[by_month['hashtag']=='mapcork'].copy()
tag_trend['ym'] = pd.to_datetime(tag_trend['ym'] + "-01")
plt.figure()
plt.plot(tag_trend['ym'], tag_trend['n'])
plt.title("#mapcork by month")
plt.tight_layout()
plt.savefig("mapcork_trend.png")

#Gini analysis on dominance of hashtags
counts = users['n'].to_numpy()
counts = np.sort(counts)
gini = (np.sum((2*np.arange(1,len(counts)+1)-len(counts)-1)*counts) /
        (len(counts)*np.sum(counts)))
print("Approx Gini:", gini)

#Analysing diversity of hashtag vocabularies  
grid = con.execute("""
SELECT round(lat*2)/2.0 AS lat_bin,
       round(lon*2)/2.0 AS lon_bin,
       hashtag, COUNT(*) n
FROM hashtag_points
GROUP BY 1,2,3
""").df()
con.close()

#Producing an entropy index of hastags
ent = (grid.groupby(['lat_bin','lon_bin'])
           .apply(lambda g: -np.sum((g['n']/g['n'].sum())*np.log2(g['n']/g['n'].sum())))
           .reset_index(name='entropy'))
print(ent.head())
