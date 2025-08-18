import duckdb, pandas as pd, regex as re, unicodedata
from urllib.parse import unquote

DB = "osm_changesets.duckdb"
#Set the batch size to 200,000 to avoid overloading RAM
BATCH = 200_000

# Grab anything non-space after '#'
RAW_HASHTAG_RE = re.compile(r"#(\S+)", re.UNICODE)

#Decode the unicode cahracters
DOT_HEX_PAIR = re.compile(r"\.([0-9A-Fa-f]{2})(?=\.|$)")
# split on common separators that may be inside the hashtags
SEP_SPLIT = re.compile(r"[,;/|]+")
# trim leading/trailing punctuation and symbols
TRIM_PUNCT = re.compile(r"^[\s\p{P}\p{S}]+|[\s\p{P}\p{S}]+$", re.UNICODE)

MIN_LEN = 3         # Require at least 3 chars after normalisation

##### CHANGE THE MIN LENGTH TO INCLUDE ALL HASHTAGS #####

DROP_NUMERIC = True  # drop tags that are digits-only 

###### IF YOU WANT HASHTAGS THAT ARE PURELY NUMERIC CHARACTERS OR CONTAIN NUMBERIC CHARACTERS, SIMPLY TURN THIS TO FALSE #####

def decode_dotted_hex(s: str) -> str:
    # Turn '.XX.YY' into '%XX%YY' then unquote
    s2 = DOT_HEX_PAIR.sub(lambda m: "%" + m.group(1), s)
    # Also handle cases mid-string without trailing dot groups
    #Second pass to catch any remaining single '.XX'
    s2 = re.sub(r"\.([0-9A-Fa-f]{2})", r"%\1", s2)
    try:
        return unquote(s2)
    except Exception:
        return s  # fallback

def normalise_token(tok: str) -> str:
    # Url-decode weird encodings
    tok = decode_dotted_hex(tok)
    # Unicode normalise & lowercase
    tok = unicodedata.normalize("NFC", tok).lower()
    # Split on internal separators like ',', ';', '/', '|'
    parts = SEP_SPLIT.split(tok)
    out = []
    for p in parts:
        # Trim surrounding punctuation/symbols
        p = TRIM_PUNCT.sub("", p)
        # Collapse whitespace (should be rare in hashtags)
        p = " ".join(p.split())
        if not p:
            continue
        # optional filters
        if DROP_NUMERIC and p.isdigit():
            continue
        # at least MIN_LEN alphanumerics anywhere in the token
        if len(re.findall(r"[0-9a-zA-Z]", p)) < MIN_LEN:
            continue
        out.append(p)
    # Return multiple if split produced >1 caller will handle
    return out

def extract_pairs(txt: str):
    """
    Return list of (raw, norm) pairs from a comment string.
    De-dup by normalised value (keep first raw form).
    """
    if not isinstance(txt, str):
        return []
    raws = RAW_HASHTAG_RE.findall(txt)
    seen = set()
    pairs = []
    for raw in raws:
        norms = normalise_token(raw)
        for n in norms:
            if n and n not in seen:
                pairs.append((raw, n))
                seen.add(n)
    return pairs

# Two connections with same config to avoid DuckDB config clash
con_ro = duckdb.connect(DB)
con_w  = duckdb.connect(DB)

# Reset table 

###### GET RID OF THIS TABLE RESET IF YOU WANT TO CONINUOUSLY ADD HASHTAGS TO THE DATABASE ##### 

con_w.execute("DROP TABLE IF EXISTS changeset_hashtags")
con_w.execute("""
CREATE TABLE changeset_hashtags (
  changeset_id BIGINT,
  created TIMESTAMP,
  uid BIGINT,
  user TEXT,
  hashtag_raw TEXT,
  hashtag TEXT
);
""")

#Select all the hashtags in the database
reader = con_ro.execute("""
  SELECT changeset_id, created, uid, user, comment
  FROM changesets
  WHERE comment LIKE '%#%'
""").fetch_record_batch(BATCH)

total_seen = total_inserted = 0

while True:
    try:
        #Read each batch iteratively
        batch = reader.read_next_batch()
    except StopIteration:
        #Fallback
        break
    if batch is None or batch.num_rows == 0:
        #Fallback
        break

    #Transfer the batch to a pandas dataframe
    df = batch.to_pandas()
    total_seen += len(df)

    # Extract list of (raw, norm) pairs per row
    pairs_list = df["comment"].map(extract_pairs)

    # Explode into rows
    rows = []
    for (cs_id, created, uid, user), pairs in zip(
        df[["changeset_id","created","uid","user"]].itertuples(index=False, name=None),
        pairs_list
    ):
        for raw, norm in pairs:
            rows.append((cs_id, created, uid, user, raw, norm))

    # If we have a rows list, make the contents into a dataframe and insert into the hashtags table of the database
    if rows:
        tmp = pd.DataFrame(rows, columns=["changeset_id","created","uid","user","hashtag_raw","hashtag"])
        con_w.register("ex", tmp)
        con_w.execute("INSERT INTO changeset_hashtags SELECT * FROM ex")
        con_w.unregister("ex")
        total_inserted += len(tmp)

# Indexes
con_w.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_norm ON changeset_hashtags(hashtag)")
con_w.execute("CREATE INDEX IF NOT EXISTS idx_hashtag_uid ON changeset_hashtags(uid)")

con_ro.close()
con_w.close()

print(f"Processed rows: {total_seen:,}")
print(f"Inserted hashtag rows: {total_inserted:,}")
