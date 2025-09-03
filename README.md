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

From the terminal, 
1. clone this repository and install requirements:
    ```bash
    git clone https://github.com/WarwickCIM/OSM-hashtag-explorer
    cd OSM-hashtag-explorer

    ```
2. Create a virtual environment (optional but recommended):

    ```bash
    python -m venv venv            # Create a virtual environment named 'venv'
    ```

3. Activate the virtual environment:

    ```bash
    source venv/bin/activate   
    ```

4. Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Examples of the output you should see in your terminal when running our 
files can be found in 'Documentation_ExamplesExecution.




### Creating the database from scratch: 

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

### Updating existing database with recent changeset data

When new OSM changesets are released: 

1. Download the new .osm.bz2 file 
2. Run the update pipeline to append new changesets, extract new hashtags and update the user table. 
Enter into the update_database.py file. Edit the first four variables for your infile, your database file, your batch size and optionally your max entry count.

Then run:

```bash
python update_database.py
```

![Alt text](/Documentation_ExecutionExamples/documentation_updatedatabaserunning.png)

### Running basic queries in the database:

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


### Finding changeset 'hotspots'

Changeset hotspots are defined in the code as bounding boxes were multiple changes have been made by multiple users, and comments of these changes include indications that the changes are controversial. 

Run the hostpots_finder.py, ensuring that the duckdb database is in the same directory. This will produce a .csv file in the the folder 'QueryResults' in the current directory.

To view of the hotspots, you can run plot_hotspots.py which will map the found hospots on a Cartopy map and save these maps in the 'Query Results' folder as .png files.

Currently, you can view the top 10,000 hotspots defined by the following criteria in the 'QueryResultsExamples' directory. The hotspots listed are defined by:
10 or more changes by 3 or more users, within a 0.01 x 0.01 degree area, scored by use of contentious comments including 'vandal', 'wrong', 'undo', 'dispute', 'revert'. Areas with more changes by more users containing more contentious comments are scored higher. The final list is ordered by score and the top 10,000 are taken.

## Acknowledgements 

This project was inspired by and builds on examples of using DuckDB and Streamlit together, including:  

- [QuackCode: Streamlit + DuckDB](https://github.com/mehd-io/quackcode-streamlit-duckdb/blob/main/app.py) by [mehd-io](https://github.com/mehd-io)  
- [Streamlit Map Dashboard](https://github.com/zakariachowdhury/streamlit-map-dashboard/blob/main/streamlit_app.py) by [zakariachowdhury](https://github.com/zakariachowdhury) 

DuckDB blog examples:  
- [Closest train stations](https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/pages/closest_train_stations.py)  
- [DuckDB + Streamlit demo app](https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/app.py)   
