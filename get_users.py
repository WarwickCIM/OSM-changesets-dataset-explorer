#get_users.py

import duckdb

con = duckdb.connect("osm_changesets.duckdb")

#Here, we build user-level tables and views from the OSM changesets and hashtag tables.
#1. Create the users table:
#FirstSeen: For each user, find the earliest timestamp of any changeset they created.
##LastSeen: Find the latest timestamp of their changesets.
##ChangesetsCount: Count the total number of changesets they created.
#Filter: Ignore any rows that have no user id.
#HashtagsRows: Count the total number of hashtag occurrences across all changesets by this user.
#DistinctHashtags: Count how many unique hashtasg the user has used.
#NameLatest: Determine the most recent username for each uid by ranking usernames by timestamp.
#Union: Prefer usernames from the hashtag table, but fall back to changesets if missing.
#FinalSelect: Combine everything into a single usesr table with one row per user.

#2. Create the user_hashtag_stats table:
# For each user–hashtag pair, store how many times the user used the hashtag, and when it was first and last seen.

#3. Create the user_points view:
#For each changeset with a valid user id and coordinates, compute the central lat/lon of the bounding box.
#This allows mapping the spatial distribution of a user’s edits.
#
#Indexes are added to the users and user_hashtag_stats tables to speed up queries by uid, username, or hashtag.


print("Executing the first statements")

con.execute("""
CREATE OR REPLACE TABLE users AS
WITH cs AS (
  SELECT uid,
         MIN(created) AS first_seen,
         MAX(created) AS last_seen,
         COUNT(*)     AS changesets_count
  FROM changesets
  WHERE uid IS NOT NULL
  GROUP BY uid
),
ht AS (
  SELECT uid,
         COUNT(*)               AS hashtags_rows,
         COUNT(DISTINCT hashtag) AS distinct_hashtags
  FROM changeset_hashtags
  GROUP BY uid
),
name_latest AS (
  SELECT uid, user, created,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY created DESC) AS rn
  FROM (
    -- prefer names seen in hashtag table first (usually more recent),
    -- fall back to changesets if needed
    SELECT uid, user, created FROM changeset_hashtags
    UNION ALL
    SELECT uid, user, created FROM changesets WHERE uid IS NOT NULL
  )
)
SELECT
  cs.uid,
  nl.user                         AS latest_username,
  cs.first_seen,
  cs.last_seen,
  cs.changesets_count,
  COALESCE(ht.hashtags_rows, 0)   AS hashtags_rows,
  COALESCE(ht.distinct_hashtags, 0) AS distinct_hashtags
FROM cs
LEFT JOIN ht USING (uid)
LEFT JOIN (SELECT uid, user FROM name_latest WHERE rn = 1) nl USING (uid)
;
""")

print("Executing user-hashtag statistics")

#User-hashtag statistics
con.execute("""
CREATE OR REPLACE TABLE user_hashtag_stats AS
SELECT
  uid,
  hashtag,
  COUNT(*)       AS n,
  MIN(created)   AS first_seen,
  MAX(created)   AS last_seen
FROM changeset_hashtags
GROUP BY uid, hashtag
;
""")

print("Executing user points")

#User points
con.execute("""
CREATE OR REPLACE VIEW user_points AS
SELECT
  uid,
  user,
  created,
  (min_lat + max_lat)/2.0 AS lat,
  (min_lon + max_lon)/2.0 AS lon
FROM changesets
WHERE uid IS NOT NULL AND min_lat IS NOT NULL AND min_lon IS NOT NULL
;
""")

print("Making the indexes")

#Indexes to speed up lookups by uid and username
con.execute("CREATE INDEX IF NOT EXISTS idx_users_uid ON users(uid);")
con.execute("CREATE INDEX IF NOT EXISTS idx_users_name ON users(latest_username);")

#More indixes to speed up lookupts by user-hashtag statistics
# con.execute("CREATE INDEX IF NOT EXISTS idx_uht_uid ON user_hashtag_stats(uid);")
con.execute("CREATE INDEX IF NOT EXISTS idx_uht_hashtag ON user_hashtag_stats(hashtag);")

#Close the database connection
con.close()
print("User tables/materialized views created.")

