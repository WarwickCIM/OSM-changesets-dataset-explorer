#extract_hashtags.py

import time
import duckdb
import pandas as pd
import numpy as np
import regex as re
import unicodedata
from urllib.parse import unquote
from tqdm import tqdm

DB = "osm_changesets.duckdb"

# How many changesets to fetch per batch of IDs
BATCH_IDS = 200_000

# True = drop and rebuild 'changeset_hashtags'; False = append only new changesets
DROP_AND_REBUILD = True

# Setting normalisation rules for the hashtags
DOT_HEX_PAIR = re.compile(r"\.([0-9A-Fa-f]{2})(?=\.|$)")
SEP_SPLIT    = re.compile(r"[,;/|]+") 
TRIM_PUNCT   = re.compile(r"^[\s\p{P}\p{S}]+|[\s\p{P}\p{S}]+$", re.UNICODE)
MIN_LEN      = 3   # require at least 3 alpha/digit chars somewhere
DROP_NUMERIC = True   #drop tokens that are digits-only

def decode_dotted_hex(s: str) -> str:
    # Turn .XX.YY into %XX%YY then perform a URL decode
    s2 = DOT_HEX_PAIR.sub(lambda m: "%" + m.group(1), s)
    s2 = re.sub(r"\.([0-9A-Fa-f]{2})", r"%\1", s2)  
    try:
        return unquote(s2)
    except Exception:
        return s

def norm_one(raw_like: str):
    #Takes one raw hashtag and returns as list of normalized hashtags. A single piece may encode multiple hashtags otherwise.
    if raw_like is None:
        return []

    # Keep a raw version with leading '#'
    raw_token = raw_like.strip()

    # If the piece doesn't start with '#', try to find it 
    if not raw_token.startswith("#"):
        #strip leading punctuation/spaces and add '#'
        raw_token = "#" + raw_token.lstrip(" #")

    #Remove the leading '#' for normalization
    token_wo_hash = raw_token.lstrip("#")

    #decode dotted hex character, unicode characters, and normalise the hashtags
    tok = unicodedata.normalize("NFC", decode_dotted_hex(token_wo_hash)).lower()

    out = []
    for p in SEP_SPLIT.split(tok):
        p = TRIM_PUNCT.sub("", p)      # trim punctuation around
        p = " ".join(p.split())        #collapse whitespaces
        if not p:
            continue
        if DROP_NUMERIC and p.isdigit():
            continue
        if len(re.findall(r"[0-9a-zA-Z]", p)) < MIN_LEN:
            continue
        out.append(p)
    return raw_token, out  #return original raw hashtag with a list of tokens

#Connect to the database
con = duckdb.connect(DB)

# Prepare destination table
if DROP_AND_REBUILD:
    con.execute("DROP TABLE IF EXISTS changeset_hashtags")
    con.execute("""
        CREATE TABLE changeset_hashtags (
          changeset_id BIGINT,
          created TIMESTAMP,
          uid BIGINT,
          user TEXT,
          hashtag_raw TEXT,
          hashtag TEXT
        );
    """)
else:
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

#Perform a baseline count for tqdm
try:
    n_before = con.execute("SELECT COUNT(*) FROM changeset_hashtags").fetchone()[0]
except duckdb.Error:
    n_before = 0

#determine candidate pool and starting id
if DROP_AND_REBUILD:
    total_candidates = con.execute(
        "SELECT COUNT(*) FROM changesets WHERE hashtags IS NOT NULL;"
    ).fetchone()[0]
    min_id = con.execute(
        "SELECT COALESCE(MIN(changeset_id), 0) FROM changesets WHERE hashtags IS NOT NULL;"
    ).fetchone()[0]
else:
    total_candidates = con.execute("""
        SELECT COUNT(*)
        FROM changesets c
        LEFT JOIN (SELECT DISTINCT changeset_id FROM changeset_hashtags) h USING (changeset_id)
        WHERE c.hashtags IS NOT NULL AND h.changeset_id IS NULL;
    """).fetchone()[0]
    min_id = con.execute("""
        SELECT COALESCE(MIN(c.changeset_id), 0)
        FROM changesets c
        LEFT JOIN (SELECT DISTINCT changeset_id FROM changeset_hashtags) h USING (changeset_id)
        WHERE c.hashtags IS NOT NULL AND h.changeset_id IS NULL;
    """).fetchone()[0]

if total_candidates == 0:
    print("No candidate changesets with non-null hashtags. Nothing to do.")
    con.close()
    raise SystemExit

print(f"Candidate changesets with non-null hashtags: {total_candidates:,}")

processed = 0
pbar = tqdm(total=total_candidates, unit="changesets",
            desc="Building from `changesets.hashtags`", smoothing=0.1)
last_id = int(min_id) - 1
t0 = time.time()

while True:
    # Fetch next window of candidate IDs
    ids_df = con.execute("""
        SELECT changeset_id
        FROM changesets
        WHERE hashtags IS NOT NULL AND changeset_id > ?
        ORDER BY changeset_id
        LIMIT ?
    """, [last_id, BATCH_IDS]).df()

    if ids_df.empty:
        break

    last_id = int(ids_df["changeset_id"].iloc[-1])
    con.register("batch_ids", ids_df)

    #Pull base rows for those specific IDs
    base = con.execute("""
        SELECT c.changeset_id, c.created, c.uid, c.user, c.hashtags
        FROM changesets c
        JOIN batch_ids b USING (changeset_id)
    """).df()
    con.unregister("batch_ids")

    #explode comma-separated list in Python
    rows = []
    for _, r in base.iterrows():
        hashtags_field = r["hashtags"]
        if not isinstance(hashtags_field, str) or not hashtags_field.strip():
            continue

        #split one comma, keep one raw piece and one normalized piece
        for piece in hashtags_field.split(","):
            piece = piece.strip()
            if not piece:
                continue
            raw_token, norm_list = norm_one(piece)
            seen_norm = set()
            for norm in norm_list:
                if norm not in seen_norm:
                    rows.append((
                        int(r["changeset_id"]),
                        r["created"],
                        int(r["uid"]) if pd.notnull(r["uid"]) else None,
                        r["user"],
                        raw_token,   # hashtag_raw (keeps '#')
                        norm         #normalised hashtag
                    ))
                    seen_norm.add(norm)

    if rows:
        tmp = pd.DataFrame(
            rows,
            columns=["changeset_id","created","uid","user","hashtag_raw","hashtag"]
        )
        con.register("ex", tmp)
        con.execute("INSERT INTO changeset_hashtags SELECT * FROM ex")
        con.unregister("ex")

    processed += len(ids_df)
    pbar.update(len(ids_df))

pbar.close()
elapsed = time.time() - t0
print(f"Done. Scanned {processed:,} candidate changesets in {elapsed/60:.1f} min.")

n_after = con.execute("SELECT COUNT(*) FROM changeset_hashtags").fetchone()[0]
print("Inserted rows this run:", n_after - n_before)

print("Creating index on normalized hashtag")
con.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_norm ON changeset_hashtags(hashtag)")

#This code can be uncommented if it works. With some versions of DuckDB it will throw an error.
# con.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_uid  ON changeset_hashtags(uid)")

con.close()
print("Done")
