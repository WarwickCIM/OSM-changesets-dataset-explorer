#reset_database_connection.py

import gc
import duckdb

#Reset your database connection to ensure there are no open read/write connections to the database before you start writing/reading
for obj in gc.get_objects():
    try:
        if isinstance(obj, duckdb.DuckDBPyConnection):
            obj.close()
    except:
        pass

try:
    duckdb.close()  #closes default connections
except:
    pass