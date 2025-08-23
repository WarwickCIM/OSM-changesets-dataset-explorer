#make_database.py

import bz2, duckdb, pandas as pd, re
from lxml import etree
from tqdm import tqdm

INFILE = "changesets-latest.osm.bz2"
DB = "osm_changesets.duckdb"
BATCH = 50_000
MAX_COUNT = 30_000_000

# Connect to the database and add a 'hashtags' column
con = duckdb.connect(DB)
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
  hashtags TEXT  -- <== new column
);
""")

def flush(batch):
    if not batch:
        return
    df = pd.DataFrame.from_records(batch)
    con.register("batch", df)
    con.execute("INSERT INTO changesets SELECT * FROM batch")
    con.unregister("batch")

def extract_hashtags(comment):
    return re.findall(r"#\w+", comment) if comment else []

#Iterate through all of the rows in the bz2 file, extract the relevant fields from the XML format and insert into the database
def parse():
    batch = []
    count = 0

    with bz2.open(INFILE, "rb") as fh:
        context = etree.iterparse(fh, events=("end",), tag="changeset")

        for _, elem in tqdm(context, desc="Parsing changesets", unit="changeset"):

            if count % 1000000 == 0:
                print("This is where we are:", elem.attrib.get("created_at"))

            # if count > MAX_COUNT:
            #     break

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

            for t in elem.iter("tag"):
                k, v = t.get("k"), t.get("v")
                if k == "created_by":
                    rec["created_by"] = v
                elif k == "comment":
                    rec["comment"] = v
                    #Extract any hashtags from the comment field of the XML if they exist
                    hashtags = extract_hashtags(v)
                    if hashtags:
                        rec["hashtags"] = ", ".join(hashtags)
                        # print("This is the hashtag found:", hashtags)
                elif k == "source":
                    rec["source"] = v
                elif k == "imagery_used":
                    rec["imagery_used"] = v

            batch.append(rec)
            count += 1

            if len(batch) >= BATCH:
                flush(batch)
                batch.clear()

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        flush(batch)

    print(f"Finished. Inserted {count} changesets.")

if __name__ == "__main__":
    parse()
    #Making these indices may not work. They are only to speed up querying. If they throw an error, you can comment the problematic one.
    con.execute("CREATE INDEX IF NOT EXISTS idx_changesets_created ON changesets(created)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_changesets_uid ON changesets(uid)")
    con.close()
