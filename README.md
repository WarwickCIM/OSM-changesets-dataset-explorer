# OSM DATASET

- This project aims to make OpenStreetMap (OSM) changeset data easier to query and explore by researchers.  
- The Overpass API does not allow direct queries for usernames or hashtags, yet this information is contained in OSM changesets.  
- Working with raw `.osm` or `.csv` dumps is inefficient for large-scale analysis: filtering and aggregating across hundreds of millions of rows is extremely slow.  

This tool addresses that problem by:  
- Extracting changeset data into a DuckDB database. This allows interoperability and portability of the system's functionality across all Operating Systems.
- Using SQL queries that return results in seconds, even over hundreds of millions of entries.  
- Providing structured tables for changesets, hashtags, and users, so queries such as “Which users used a given hashtag between 2015–2020?” are straightforward.  
- Offering a Streamlit-based interface for interactive visualisation of hashtag use, 
error-checking, query-result validation.  

---

## Acknowledgements

This is an output of the research project _["Can digital goods be neutral? Evaluating OpenStreetMap’s equity through participatory data visualisation"](https://warwick.ac.uk/fac/cross_fac/cim/research/digital-good-neutrality-osm)_ led by Carlos Cámara-Menoyo and Timothy Monteath and funded by the [ESRC Digital Good Network](https://digitalgood.net/) through their Digital Good Research Fund 2024-25. 

The `OSM DATASET` has been developed by Lilly Horvath-Makkos.

---

### Citing

You are free to use and reuse this tool under the licence conditions.  
If you use this dataset in your work, please cite it as below:

> Horvath-Makkos, L., Cámara-Menoyo, C., Monteath, T. (2025). OSM Changeset Database Explorer (Version 0.0.1) [Software]. https://github.com/WarwickCIM/OSM-hashtag-explorer

---

## Installation

Clone this repository and install requirements:

In Bash:

git clone https://github.com/WarwickCIM/OSM-hashtag-explorer
cd OSM-hashtag-explorer
pip install -r requirements.txt

## Usage

Examples of the output you should see in your terminal when running our 
files can be found in 'Documentation_ExamplesExecution. The code can either be run on the command line using the dev files, or run directly using the files. 

## CLI Guide, Running from dev files

dev.py orchestrates database creation and updates (parses changestes, extracts/normalizes hashtags, builds user tables)
queries_dev.py is a CLI wrapper around queries.py to run common analysis and export CSVs. 

## Making a new database in the command line

Using dev.py, make a fresh database build from scratch. Use this when you do not already have a database, and have a changesets file to parse: 

Then initialise the database and parse changesets: 

python dev.py make --infile changesets-latest.osm.bz2 --db osm_changesets.duckdb

Then extract and normalize hashtags into the changesets hashtags table of the database:

python dev.py extract-hashtags --db osm_changesets.duckdb --drop-and-rebuild

Then build users and materialized views in the database:

python dev.py users -db osm_changesets.duckdb

Then check the basic status of the database:
python dev.py status --db osm_changesets.duckdb

## Updating an existing database in the command line 

Update the database using a changeset file in the same directory: 

python dev.py update --infile changesets-latest.osm.bz2 --db osm_changesets.duckdb

Then check the database status: 

python dev.py status -db osm_changesets.duckdb

## Perform analysis and data retrieval on the database in the command line 

The CLI function queries_dev allows you to perform data retrieval on the database from the command line. Each command executed correctly will print a preview to your command line.

The arguments you need to know are: 
--db : Allows you to set the path to the DuckDB file
--start, --end : Allows you to set a date window for your query (YYYY-MM-DD format)
--bbox : Allows you to set a centroids filter (min_lat,min_lon,max_lat,max_lon)
--limit : Allows you to enter a maximum number of rows to return 
--order-by : Orders your query by some metric 

Hashtags in the database are normalized, pass them without the leading '#' symbol.

--like, --commend-like accept SQL like patterns. The format would be '--like %keyword%'

For example, say you want to the first 100 users who used some hashtag between a certain date: 

python queries_dev.py users-for-hashtag \
  --hashtag geochicas educategirls \
  --start 2024-01-01 --end 2024-12-31 \
  --limit 100 -o QueryResults/users_geochicas_2024.csv

For example, say you want to return the first 100 hashtags used by a certain user within some time limit: 

python queries_dev.py hashtags-for-users \
  --user exampleuser \
  --start 2023-01-01 --end 2023-06-30 \
  --order-by "n DESC" --limit 100 \
  -o QueryResults/hashtags_for_users_JanJun2023.csv

For example, say you want to count the total number of hashtags in the database ordered in descending alphabetical order between some dates: 

python queries_dev.py all-hashtags --start 2021-01-01 --end 2021-12-31 \
  --order-by "n DESC" \
  -o QueryResults/hashtags_2021.csv

For example, say you want to return all the points that some user has mapped on: 

python queries_dev.py user-points --user exampleuser --start 2023-05-01 --end 2023-06-01 \
  -o QueryResults/user_points_exampleuser.csv

For example say you want to return the top N hashtags between a certain date: 

python queries_dev.py top-hashtags \
  --start 2024-01-01 --end 2024-12-31 \
  --limit 100 -o QueryResults/top_hashtags_2024.csv

For the full list of possible pre-made queries from the database, please see the bottom of this README file.


## Interacting with the database without the command line: 
## Running basic queries in the database:

1. To retrieve the results of basic queries such as: 

Top Hashtags,
Top Users,
Hashtags by User,
Hashtags by Year,
Users by Hashtag,
Users by Year

Edit the database_queries.py file. At the bottom, chose the function that you would like to run. Alternatively, write or use one of the examples
in the execute_database_queries.py file. 
The result of the query inside the function will be saved to your computer as a .csv file.

Some examples of laready-executed database queries in the form of .csv
files can be found in the QueryResultsExamples folder.

## Uploading recent changeset data to the database: 

When new OSM changesets are released: 

1. Download the new .osm.bz2 file
2. Run the update pipeline to append new changesets, extract new hashtags and update the user table. 
Enter into the update_database.py file. Edit the first four variables for your infile, your database file, your batch size and optionally your max entry count.
Then run:
python update_database.py

![Alt text](/Documentation_ExecutionExamples/documentation_updatedatabaserunning.png)

## Creating the database from scratch: 

1. Download the latest OSM changeset dump:
curl -O https://planet.openstreetmap.org/planet/changesets-latest.osm.bz2

2. Run python make_database.py 
This will take approximately 3 hours. This extracts all changesets into a DuckDB database
(osm_changesets.duckdb)

![Alt text](/Documentation_ExecutionExamples/documentation_makedatabaserunning.png)

3. Check whether the dataset has been correctly loaded into the database:
python check_database.py

4. Extract the hashtags from the changeset comments into a new table in the database:
python extract_hashtags.py
This will take approximately 50 minutes.

![Alt text](/Documentation_ExecutionExamples/documentation_extracthashtagsrunning.png)

5. Check whether the hashtags have been correctly loaded into the database:
python check_hashtags.py

6. Create a user table with summary statistics for each user ID in the database:
python get_users.py

![Alt text](/Documentation_ExecutionExamples/documentation_getusersrunning.png)

7. Visualise the results of the database queries by running the Streamlit app (OPTIONAL):
streamlit run streamlit_app.py

![Alt text](/Documentation_ExecutionExamples/documentation_streamlitapprunning.png)

## Finding changeset 'hotspots'

Changeset hotspots are defined in the code as bounding boxes were multiple changes have been made by multiple users, and comments of these changes include indications that the changes are controversial. 

Run the hostpots_finder.py, ensuring that the duckdb database is in the same directory. This will produce a .csv file in the the folder 'QueryResults' in the current directory.

To view of the hotspots, you can run plot_hotspots.py which will map the found hospots on a Cartopy map and save these maps in the 'Query Results' folder as .png files.

Currently, you can view the top 10,000 hotspots defined by the following criteria in the 'QueryResultsExamples' directory. The hotspots listed are defined by:
10 or more changes by 3 or more users, within a 0.01 x 0.01 degree area, scored by use of contentious comments including 'vandal', 'wrong', 'undo', 'dispute', 'revert'. Areas with more changes by more users containing more contentious comments are scored higher. The final list is ordered by score and the top 10,000 are taken.

## Comprehensive explanation of all queries in database_queries.py file

- Hashtags in table `changeset_hashtags.hashtag` are normalised (lowercase, no leading `#`).  
- Most functions support `order_by`, `limit`, and optional `to_csv="path.csv"`.

Helper functions: 

### `connect(db_path=DB_PATH_DEFAULT)`
Returns a read-only DuckDB connection to the database. Use when you need to compose custom SQL on top of these helpers.

### `_ensure_list(x)`
Internal. Normalizes `None`/scalar/iterable into a Python `list` (or `None` if input is `None`).

### `_add_in_clause(sql_parts, params, col, values, cast=None)`
Internal. Appends an `AND <col> IN (?,?,...)` to a SQL `WHERE` fragment and extends `params`. Optional `cast="BIGINT"` etc.

### `_add_date_range(sql_parts, params, col, start_date, end_date)`
Internal. Adds `AND <col> >= ?` / `AND <col> <= ?` with parsed datetimes.

### `_add_bbox(sql_parts, params, lat_col, lon_col, bbox)`
Internal. Adds `AND <lat_col> BETWEEN ? AND ?` and `AND <lon_col> BETWEEN ? AND ?` for `(min_lat,min_lon,max_lat,max_lon)`.

### `_order_and_limit(order_by, limit)`
Internal. Builds trailing `ORDER BY ... LIMIT ...`.

### `make_filename(prefix, start_date=None, end_date=None, bbox=None)`
Utility to standardize CSV filenames under `QueryResults/`.

Core query functions:

### `get_users_for_hashtag(hashtag, *, start_date=None, end_date=None, bbox=None, order_by="n DESC", limit=None, db_path=..., to_csv=None)`
Returns **users who used the given hashtag(s)** (normalized), with counts and first/last usage timestamps.

**Returns columns:**  
`uid, user, n, first_seen, last_seen`

**Filters:**  
- `hashtag`: single or list (normalized; “#” stripped if present)  
- `start_date`, `end_date` (filter on hashtag usage time)  
- `bbox` (filters by changeset **centroid** using `changesets`)  


### `get_hashtags_for_users(*, usernames=None, uids=None, start_date=None, end_date=None, bbox=None, order_by="n DESC", limit=None, db_path=..., to_csv=None)`
For a set of users (by **username** and/or **uid**), returns **hashtags they used**, aggregated.

**Returns columns:**  
`hashtag, n, first_seen, last_seen`

**Filters:** user(s), date range, centroid bbox.

### `get_all_users(*, order_by="changesets_count DESC", limit=1000, db_path=..., to_csv=None)`
Lists users from the materialized `users` table.

**Returns columns (from `users`):**  
`uid, latest_username, first_seen, last_seen, changesets_count, hashtags_rows, distinct_hashtags`

### `get_all_hashtags(*, start_date=None, end_date=None, bbox=None, order_by="n DESC", limit=1000, db_path=..., to_csv=None)`
Global **hashtag counts** with optional date/bbox filters.

**Returns columns:**  
`hashtag, n, first_seen, last_seen`

### `get_hashtags_between_dates(start_date, end_date, *, order_by="n DESC", limit=1000, db_path=..., to_csv=None)`
Alias for `get_all_hashtags()` with only date filters.

### `get_users_in_bbox(bbox, *, start_date=None, end_date=None, order_by="changesets_in_bbox DESC", limit=1000, db_path=..., to_csv=None)`
Returns **users active within a bbox** using the `user_points` view (one point per changeset centroid).

**Returns columns:**  
`uid, username, changesets_in_bbox, first_seen, last_seen`

### `get_hashtags_in_bbox(bbox, *, start_date=None, end_date=None, order_by="n DESC", limit=1000, db_path=..., to_csv=None)`
Top **hashtags used inside a bbox** (via centroid), optionally within a date window.

**Returns columns:**  
`hashtag, n`

### `get_hashtags_for_users_in_bbox(*, usernames=None, uids=None, bbox, start_date=None, end_date=None, order_by="n DESC", limit=1000, db_path=..., to_csv=None)`
For selected users, returns **hashtags they used inside a bbox** (centroid) and within optional dates.

**Returns columns:**  
`hashtag, n`

### `get_users_for_hashtag_in_bbox(hashtag, bbox, *, start_date=None, end_date=None, order_by="n DESC", limit=1000, db_path=..., to_csv=None)` 
Convience wrapper: **users who used hashtag(s) inside a bbox** (delegates to `get_users_for_hashtag` + bbox).

### `get_user_points(*, usernames=None, uids=None, start_date=None, end_date=None, db_path=..., to_csv=None)`
Returns **point centroids (lat/lon)** for changesets by specified users over optional date ranges (from `user_points` view).

**Returns columns:**  
`uid, user, created, lat, lon`

### `get_hashtag_points(hashtag, *, start_date=None, end_date=None, db_path=..., to_csv=None)`
All **centroid points** for changesets that used the hashtag(s), optionally within a date window.

**Returns columns:**  
`hashtag, created, lat, lon`

### `count_hashtag(hashtag, *, start_date=None, end_date=None, db_path=...)`
Counts one or more **hashtags** (normalized), optionally filtered by date window.

**Returns columns:**  
`hashtag, n`

### `count_user_changes(*, uids=None, usernames=None, start_date=None, end_date=None, db_path=...)`
Counts **changesets per user** (by uid and/or username) in an optional date window.

**Returns columns:**  
`uid, user, changesets`

### `get_changesets_filtered(*, usernames=None, uids=None, hashtag=None, like=None, comment_like=None, start_date=None, end_date=None, bbox=None, order_by="created_at DESC", limit=None, db_path=..., to_csv=None)`
A **general changeset search** returning distinct changesets that match any combination of:
- users/uids
- exact hashtags (`hashtag`)
- LIKE patterns on hashtags (`like`, e.g. `"%women%"`)
- LIKE patterns on comments (`comment_like`, e.g. `"%mapathon%"`)
- date window and centroid bbox

**Returns columns:**  
`id, user, uid, created_at, comment, created_by, imagery_used, source, min_lat, min_lon, max_lat, max_lon, hashtags`

### `get_top_users(*, hashtag=None, like=None, start_date=None, end_date=None, bbox=None, order_by="n DESC", limit=50, db_path=..., to_csv=None)`
Returns **top N users by changeset count**, optionally restricted by hashtag(s), LIKE patterns, date window, and bbox.

**Returns columns:**  
`uid, user, n, first_seen, last_seen`

### `get_top_hashtags(*, usernames=None, uids=None, start_date=None, end_date=None, bbox=None, order_by="n DESC", limit=100, db_path=..., to_csv=None)`
Returns **top N hashtags**, globally or for selected users, with optional date/bbox filters.

**Returns columns:**  
`hashtag, n, first_seen, last_seen`

### `get_top_comments(*, hashtag=None, like=None, start_date=None, end_date=None, bbox=None, order_by="n DESC", limit=100, db_path=..., to_csv=None)`
Returns the **most frequent comment texts** on changesets, optionally filtered by hashtag(s)/LIKE/date/bbox.

**Returns columns:**  
`comment, n`

## Acknowledgements 

This project was inspired by and builds on examples of using DuckDB and Streamlit together, including:  

- [QuackCode: Streamlit + DuckDB](https://github.com/mehd-io/quackcode-streamlit-duckdb/blob/main/app.py) by [mehd-io](https://github.com/mehd-io)  
- [Streamlit Map Dashboard](https://github.com/zakariachowdhury/streamlit-map-dashboard/blob/main/streamlit_app.py) by [zakariachowdhury](https://github.com/zakariachowdhury) 

DuckDB blog examples:  
- [Closest train stations](https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/pages/closest_train_stations.py)  
- [DuckDB + Streamlit demo app](https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/app.py)   