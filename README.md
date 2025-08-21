# OSM DATASET

Briefly Explain aims here. What is this that this project aims to do? How? Why?

## Acknowledgements

This is an output of the research project _["Can digital goods be neutral? Evaluating OpenStreetMap’s equity through participatory data visualisation"](https://warwick.ac.uk/fac/cross_fac/cim/research/digital-good-neutrality-osm)_ led by Carlos Cámara-Menoyo and Timothy Monteath and funded by the [ESRC Digital Good Network](https://digitalgood.net/) through their Digital Good Research Fund 2024-25. 

The `OSM DATASET` has been developed by Lilly Makkos.

### Citing

You are free to use and reuse this tool under the Licence conditions. If you use this dataset in your work, please cite it as below:

> Makkos, L., Cámara-Menoyo, C., Monteath, T. (2025). Nice title (Version 0.0.1) [Software]. https://github.com/WarwickCIM/OSM-hasthag-explorer


## Installation

E.g. 

```python
pip install <library_name>
```

## Usage

### Creating the database

### Updating the database

### Visualising the database

Add a screenshot here?

### Querying and exporting


## Acknowledgements

This project gets inspiration from others: POTENTIALLY, YOU COULD CREDIT ANY EXAMPLES, SUCH AS THE ONES YOU CITED HERE: https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/pages/closest_train_stations.py, https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/app.py, https://github.com/mehd-io/quackcode-streamlit-duckdb/blob/main/app.py OR https://github.com/zakariachowdhury/streamlit-map-dashboard/blob/main/streamlit_app.py

## Legacy README

Once you have the changeset data downloaded, run the make_database.py file to make the DuckDB database and load the changeset data into it.

For sanity checking, run the check_dataset.py file. It should show you the first ten rows of your dataset. This will allow you to check if 
the changeset data has been correctly loaded into the database.

Then run the extract_hashtags.py file. This will create a new hashtags table in your database and extract your desired information from the 
changeset data.

For sanity checking, run the check_hashtags.py file. It should show you the results of a number of queries on the hashtag table. 

If they are output as expected, run the get_users.py file to create the user table in the database.

Finally, run this line in your console: 

streamlit run streamlit_app.py then click the link provided by your console.

You can then visualise the query outputs of this codebase on the streamlit interface.


To edit the code, please find some useful resources: 

https://www.w3schools.com/sql/sql_quickref.asp

https://python-visualization.github.io/folium/latest/user_guide/plugins/heatmap.html

https://docs.streamlit.io/develop/tutorials/databases/mssql

https://duckdb.org/2025/03/28/using-duckdb-in-streamlit.html

https://www.datacamp.com/tutorial/python-trim

https://www.geeksforgeeks.org/python/re-compile-in-python/

https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data

https://docs.streamlit.io/develop/concepts/architecture/caching

https://www.statology.org/gini-coefficient-python/

https://gist.github.com/j4mie/557354

https://streamlit.io/gallery?category=data-visualization (I used quite a few streamlit examples from here)

Below are some GitHub examples of DuckDB being used with Streamlit that are similar to ours: 

https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/pages/closest_train_stations.py

https://github.com/duckdb/duckdb-blog-examples/blob/main/duckdb_streamlit/app.py

https://github.com/mehd-io/quackcode-streamlit-duckdb/blob/main/app.py

https://github.com/zakariachowdhury/streamlit-map-dashboard/blob/main/streamlit_app.py

