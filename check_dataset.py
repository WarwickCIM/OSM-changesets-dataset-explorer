#Sanity checking the database

import duckdb

# Setting DB to our database
DB = "osm_changesets.duckdb"

# Starting the connection to the database
con = duckdb.connect(DB)

# Count how many rows in the changeset table in the database
count = con.execute("SELECT COUNT(*) FROM changesets").fetchone()[0]
print(f"Total rows in changesets: {count}")

# Show the first 10 rows
print("\nFirst 10 rows:")
rows = con.execute("""
    SELECT changeset_id, created, user, comment, num_changes
    FROM changesets
    LIMIT 10
""").fetchall()

for r in rows:
    print(r)

# Show min/max created date in the changeset table in the database
min_max = con.execute("""
    SELECT MIN(created), MAX(created) FROM changesets
""").fetchone()
print(f"\nDate range in DB: {min_max[0]} → {min_max[1]}")

#Always close the connection
con.close()