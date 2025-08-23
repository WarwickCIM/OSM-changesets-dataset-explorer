# update_database.py
# Incrementally update the DuckDB with new changesets, hashtags and user tables.
#
# What this script does:
# 1) Parse a .osm.bz2 changesets dump, batched, and append ONLY unseen changesets into 'changesets'.
#    Populates a comma-separated 'hashtags' column from the comment tag (like "#mapathon, #foo").
# 2) Populate/append 'hangeset_hashtags' ONLY for changesets we just inserted,
#    splitting the comma list, decoding odd encodings, and normalising.
# 3) Rebuild user tables/views ('users', 'user_hashtag_stats', 'user_points') and indexes.
#
# Running again on the same rows will not duplicate windows
# Compatible with DuckDB 1.3.2 (They version has a bug on certain indexes. Indexes are not necessary, they simply speed up querying
# If the code doesn't run due to a problem with a line beginning with 'CREATE INDEX', this line can be commented out)
#
# Usage:
#   Change the INFILE and DB variables at the top of the code. 
#   Then run update_database.py
#

import argparse, bz2, duckdb, pandas as pd, regex as re, unicodedata
from urllib.parse import unquote
from lxml import etree
from tqdm import tqdm

INFILE = "changesets-latest.osm.bz2"
DB     = "osm_changesets.duckdb"
BATCH  = 50_000
#Max count can be set to None, it is not mandatory
MAX_COUNT = 1_000_000

# Regex helpers
COMMENT_HASHTAGS_RE = re.compile(r"#\w+")
DOT_HEX_PAIR = re.compile(r"\.([0-9A-Fa-f]{2})(?=\.|$)")
SEP_SPLIT    = re.compile(r"[,;/|]+")
TRIM_PUNCT   = re.compile(r"^[\s\p{P}\p{S}]+|[\s\p{P}\p{S}]+$", re.UNICODE)
MIN_LEN      = 3
DROP_NUMERIC = True

#Extracts only hashtags (if there are any) from the comment (if there is one) on a change
def extract_hashtags_from_comment(comment: str):
    """Returns a comma-separated string of raw hashtags found in a comment, or None."""
    if not comment:
        return None
    tags = COMMENT_HASHTAGS_RE.findall(comment)
    return ", ".join(tags) if tags else None

def decode_dotted_hex(s: str) -> str:
    s2 = DOT_HEX_PAIR.sub(lambda m: "%" + m.group(1), s)
    s2 = re.sub(r"\.([0-9A-Fa-f]{2})", r"%\1", s2)
    try:
        return unquote(s2)
    except Exception:
        return s

def normalise_piece(piece_with_hash: str):
    """
    Input: a single raw hashtag token like #Tag1 (from comma-split list).
    Output: (raw_token_with_hash, [normalised tokens])
    May yield multiple normalised tokens if the piece encodes a/b etc.
    """
    raw_token = (piece_with_hash or "").strip()
    if not raw_token:
        return None, []
    if not raw_token.startswith("#"):
        raw_token = "#" + raw_token.lstrip(" #")
    core = unicodedata.normalize("NFC", decode_dotted_hex(raw_token.lstrip("#"))).lower()
    out = []
    for p in SEP_SPLIT.split(core):
        p = TRIM_PUNCT.sub("", p)
        if not p:
            continue
        if DROP_NUMERIC and p.isdigit():
            continue
        if len(re.findall(r"[0-9a-zA-Z]", p)) < MIN_LEN:
            continue
        out.append(p)
    return raw_token, out

# Here we setup the database:
con = duckdb.connect(DB)

# If the table doesn't already exist, we create it: 
con.execute("""
CREATE TABLE IF NOT EXISTS changesets (
  changeset_id BIGINT,
  created TIMESTAMP,
  closed TIMESTAMP,
  uid BIGINT,
  user TEXT,
  open BOOLEAN,
  num_changes INTEGER,
  comments_count INTEGER,
  min_lat DOUBLE, min_lon DOUBLE, max_lat DOUBLE, max_lon DOUBLE,
  created_by TEXT,
  comment TEXT,
  source TEXT,
  imagery_used TEXT,
  hashtags TEXT
);
""")

# Make sure we can anti-join on IDs efficiently (the indexes are not mandatory)
con.execute("CREATE INDEX IF NOT EXISTS idx_changesets_id ON changesets(changeset_id);")

# Ensure hashtag table exists (append-only)
con.execute("""
CREATE TABLE IF NOT EXISTS changeset_hashtags (
  changeset_id BIGINT,
  created TIMESTAMP,
  uid BIGINT,
  user TEXT,
  hashtag_raw TEXT,
  hashtag TEXT
);
""")
con.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_norm ON changeset_hashtags(hashtag);")

#This code can be uncommented if it works
# con.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_uid ON changeset_hashtags(uid);")

# Append only new changesets to the database below
def flush_changesets(batch):
    if not batch:
        return []
    df = pd.DataFrame.from_records(batch)
    # Anti-join against existing IDs inside DuckDB for faster insert
    con.register("batch", df)
    con.execute("""
        INSERT INTO changesets
        SELECT b.*
        FROM batch b
        LEFT JOIN changesets c ON c.changeset_id = b.changeset_id
        WHERE c.changeset_id IS NULL
    """)
    # Return the list of new IDs that were inserted
    new_ids = con.execute("""
        SELECT b.changeset_id
        FROM batch b
        LEFT JOIN changesets c ON c.changeset_id = b.changeset_id
        WHERE c.created = b.created AND c.user IS NOT NULL OR c.user IS NULL
    """).df()["changeset_id"].tolist()
    con.unregister("batch")
    return new_ids

print("Parsing new changesets & appending")
new_changeset_ids = []
count = 0
batch = []

#Iterate through the bz2 file, inserting each line that has not been seen before
with bz2.open(INFILE, "rb") as fh:
    context = etree.iterparse(fh, events=("end",), tag="changeset")
    for _, elem in tqdm(context, desc="Parsing .osm.bz2", unit="changeset"):
        a = elem.attrib

        rec = {
            "changeset_id": int(a.get("id")),
            "created": a.get("created_at"),
            "closed": a.get("closed_at"),
            "uid": int(a["uid"]) if "uid" in a else None,
            "user": a.get("user"),
            "open": a.get("open") == "true",
            "num_changes": int(a["num_changes"]) if "num_changes" in a else None,
            "comments_count": int(a["comments_count"]) if "comments_count" in a else None,
            "min_lat": float(a["min_lat"]) if "min_lat" in a else None,
            "min_lon": float(a["min_lon"]) if "min_lon" in a else None,
            "max_lat": float(a["max_lat"]) if "max_lat" in a else None,
            "max_lon": float(a["max_lon"]) if "max_lon" in a else None,
            "created_by": None,
            "comment": None,
            "source": None,
            "imagery_used": None,
            "hashtags": None
        }

        #Read all tags in the XML
        for t in elem.iter("tag"):
            k, v = t.get("k"), t.get("v")
            if k == "created_by":
                rec["created_by"] = v
            elif k == "comment":
                rec["comment"] = v
                #Extract hashtags from the comments
                rec["hashtags"] = extract_hashtags_from_comment(v)
            elif k == "source":
                rec["source"] = v
            elif k == "imagery_used":
                rec["imagery_used"] = v

        batch.append(rec)
        count += 1

        #Perform the database insertion in batches to avoid overwhelming RAM.
        if len(batch) >= BATCH:
            new_ids = flush_changesets(batch)
            if new_ids:
                new_changeset_ids.extend(new_ids)
            batch.clear()

        elem.clear()
        # free siblings
        while elem.getprevious() is not None:
            del elem.getparent()[0]

        #Will stop on MAX_COUNT if it has been provided
        if MAX_COUNT is not None and count >= MAX_COUNT:
            break

#Load the remaining entires into the database
if batch:
    new_ids = flush_changesets(batch)
    if new_ids:
        new_changeset_ids.extend(new_ids)
    batch.clear()

print(f">> Parsed {count:,} changesets from file.")
print(f">> Newly inserted changesets this run: {len(new_changeset_ids):,}")

#Append the hashtags to the database only for the newly inserted entries
if new_changeset_ids:
    print(">> Extracting hashtags for newly inserted changesets")
    # Register the list of new IDs into DuckDB
    id_df = pd.DataFrame({"changeset_id": new_changeset_ids})
    con.register("new_ids", id_df)

    # Pull rows for just those ids, but skip ones already in hashtag table
    base = con.execute("""
        SELECT c.changeset_id, c.created, c.uid, c.user, c.hashtags
        FROM changesets c
        JOIN new_ids n USING (changeset_id)
        LEFT JOIN (SELECT DISTINCT changeset_id FROM changeset_hashtags) h USING (changeset_id)
        WHERE h.changeset_id IS NULL   -- only changesets without hashtag rows yet
          AND c.hashtags IS NOT NULL   -- and only those that actually have hashtags
    """).df()
    con.unregister("new_ids")

    #Normalises all the hashtags row-by-row
    rows = []
    for _, r in tqdm(base.iterrows(), total=len(base), desc="Normalising hashtags", unit="row"):
        hfield = r["hashtags"]
        if not isinstance(hfield, str) or not hfield.strip():
            continue
        for piece in hfield.split(","):
            piece = piece.strip()
            if not piece:
                continue
            raw_token, norm_list = normalise_piece(piece)
            if raw_token is None:
                continue
            seen_norm = set()
            for norm in norm_list:
                if norm not in seen_norm:
                    rows.append((
                        int(r["changeset_id"]),
                        r["created"],
                        int(r["uid"]) if pd.notnull(r["uid"]) else None,
                        r["user"],
                        raw_token,
                        norm
                    ))
                    seen_norm.add(norm)

    if rows:
        tmp = pd.DataFrame(rows, columns=[
            "changeset_id","created","uid","user","hashtag_raw","hashtag"
        ])
        con.register("ex", tmp)
        con.execute("INSERT INTO changeset_hashtags SELECT * FROM ex")
        con.unregister("ex")
        print(f">> Inserted hashtag rows: {len(tmp):,}")
    else:
        print(">> No hashtag rows to insert for this batch.")
else:
    print(">> No new changesets inserted; skipping hashtag extraction.")

#Refresh the user tables with the new entries
print(">> Rebuilding user tables")
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
         COUNT(*)                AS hashtags_rows,
         COUNT(DISTINCT hashtag) AS distinct_hashtags
  FROM changeset_hashtags
  GROUP BY uid
),
name_latest AS (
  SELECT uid, user, created,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY created DESC) AS rn
  FROM (
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
  COALESCE(ht.hashtags_rows, 0)     AS hashtags_rows,
  COALESCE(ht.distinct_hashtags, 0) AS distinct_hashtags
FROM cs
LEFT JOIN ht USING (uid)
LEFT JOIN (SELECT uid, user FROM name_latest WHERE rn = 1) nl USING (uid);
""")

#These may cause an error. They are optional, they simply make querying faster. If they throw an error, simply comment them out.
con.execute("CREATE INDEX IF NOT EXISTS idx_users_uid  ON users(uid);")
con.execute("CREATE INDEX IF NOT EXISTS idx_users_name ON users(latest_username);")

con.execute("""
CREATE OR REPLACE TABLE user_hashtag_stats AS
SELECT
  uid,
  hashtag,
  COUNT(*)       AS n,
  MIN(created)   AS first_seen,
  MAX(created)   AS last_seen
FROM changeset_hashtags
GROUP BY uid, hashtag;
""")

# This below line can be uncommented if it works
# con.execute("CREATE INDEX IF NOT EXISTS idx_uht_uid ON user_hashtag_stats(uid);")
con.execute("CREATE INDEX IF NOT EXISTS idx_uht_hashtag ON user_hashtag_stats(hashtag);")

con.execute("""
CREATE OR REPLACE VIEW user_points AS
SELECT
  uid,
  user,
  created,
  (min_lat + max_lat)/2.0 AS lat,
  (min_lon + max_lon)/2.0 AS lon
FROM changesets
WHERE uid IS NOT NULL AND min_lat IS NOT NULL AND min_lon IS NOT NULL;
""")

print(">> Done. Database updated.")
con.close()
