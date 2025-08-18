import bz2, duckdb, pandas as pd
from lxml import etree
from tqdm import tqdm

#The infile is the changeset data downloaded
INFILE = "changesets-latest.osm.bz2"
# Set DB to our database
DB = "osm_changesets.duckdb"
# Load in batches of 50000 to avoid overwhelming RAM
BATCH = 50_000
# Only take the first 10 million entires from the dataset (remove this variable and its corresponding logic to take the full changeset data)
MAX_COUNT = 10_000_000  

#Connect toe the database
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
  imagery_used TEXT
);
""")

# Flush the batch from our batch variable into the database
def flush(batch):
    if not batch:
        return
    df = pd.DataFrame.from_records(batch)
    con.register("batch", df)
    con.execute("INSERT INTO changesets SELECT * FROM batch")
    con.unregister("batch")

def parse():
    batch = []
    count = 0

    #Open the changeset data
    with bz2.open(INFILE, "rb") as fh:
        #Set the context
        context = etree.iterparse(fh, events=("end",), tag="changeset")
        #Iterate through all elements of the data
        for _, elem in tqdm(context, desc="Parsing changesets", unit="changeset"):

            #Stops after the first 10 million entries (remove if you want the full changeset data)
            if count >= MAX_COUNT: 
                break
            
            #Get all the attributes from the data element
            a = elem.attrib

            #Make a new record by extracting the data in each field 
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
            }

            #Ensure each record is in its correct location
            for t in elem.iter("tag"):
                k = t.get("k")
                v = t.get("v")
                if k == "created_by":
                    rec["created_by"] = v
                elif k == "comment":
                    rec["comment"] = v
                elif k == "source":
                    rec["source"] = v
                elif k == "imagery_used":
                    rec["imagery_used"] = v

            #Append the record to our temporary batch
            batch.append(rec)
            count += 1

            #Enter the batch into our database if it exceeds 50,000 entries
            if len(batch) >= BATCH:
                flush(batch)
                batch.clear()

            #Reset our element variable
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        #Enter the remaining rows into our database
        flush(batch)

    print(f"Finished. Inserted {count} changesets.")

if __name__ == "__main__":
    parse()
    con.execute("CREATE INDEX IF NOT EXISTS idx_changesets_created ON changesets(created)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_changesets_uid ON changesets(uid)")
    con.close()
