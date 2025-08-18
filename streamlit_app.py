# streamlit_app.py
import streamlit as st
import duckdb, pandas as pd, numpy as np
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    HAVE_LANG = True
except Exception:
    HAVE_LANG = False

#Set the path to our database
DB_PATH = "osm_changesets.duckdb"

#Open trhe database connection and set it as a streamlit resource
@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH)

#Cache the first 5000 hashtags in streamlit (will not add dynamic loading as streamlit is just for temporary visualisation and testing)
@st.cache_data(show_spinner=False)
def get_hashtags(limit=5000):
    con = get_connection()
    return con.execute("""
        SELECT DISTINCT hashtag FROM changeset_hashtags
        WHERE hashtag IS NOT NULL
        ORDER BY hashtag
        LIMIT ?
    """, [limit]).df()["hashtag"].tolist()

#Cache the dates that each change in the dataset was created
@st.cache_data(show_spinner=False)
def get_date_bounds():
    con = get_connection()
    mn, mx = con.execute("SELECT MIN(created), MAX(created) FROM changeset_hashtags").fetchone()
    return pd.to_datetime(mn), pd.to_datetime(mx)

#Cache the spatial locations of the changeset data
@st.cache_data(show_spinner=False)
def get_points_for_tag(tag, start, end):
    con = get_connection()
    return con.execute("""
        SELECT h.hashtag, h.created,
               (c.min_lat + c.max_lat)/2.0 AS lat,
               (c.min_lon + c.max_lon)/2.0 AS lon
        FROM changeset_hashtags h
        JOIN changesets c USING (changeset_id)
        WHERE h.hashtag = ?
          AND h.created BETWEEN ? AND ?
          AND c.min_lat IS NOT NULL AND c.min_lon IS NOT NULL
    """, [tag, start, end]).df()

#Cache the times that changes were made ordered by month
@st.cache_data(show_spinner=False)
def get_monthly_trend(tag, start, end):
    con = get_connection()
    return con.execute("""
        SELECT strftime(created, '%Y-%m') AS month, COUNT(*) AS n
        FROM changeset_hashtags
        WHERE hashtag = ?
          AND created BETWEEN ? AND ?
        GROUP BY month
        ORDER BY month
    """, [tag, start, end]).df()

#Cache the top users per hashtag ordered by the number of their changes
@st.cache_data(show_spinner=False)
def get_top_users_for_tag(tag, start, end, limit=20):
    con = get_connection()
    return con.execute("""
        SELECT uid, user, COUNT(*) AS n,
               MIN(created) AS first_seen, MAX(created) AS last_seen
        FROM changeset_hashtags
        WHERE hashtag = ?
          AND created BETWEEN ? AND ?
        GROUP BY uid, user
        ORDER BY n DESC
        LIMIT ?
    """, [tag, start, end, limit]).df()

#Cache the changeset data per latitude/longitude grid square, binned by the latitude and longitude 
@st.cache_data(show_spinner=False)
def grid_counts(start, end, grid=0.5, min_n=1):
    #Here we use spatial binning and entropy binning
    con = get_connection()
    factor = int(1/grid)
    q = f"""
        WITH pts AS (
          SELECT h.hashtag, (c.min_lat + c.max_lat)/2.0 AS lat,
                 (c.min_lon + c.max_lon)/2.0 AS lon
          FROM changeset_hashtags h
          JOIN changesets c USING (changeset_id)
          WHERE h.created BETWEEN ? AND ?
            AND c.min_lat IS NOT NULL AND c.min_lon IS NOT NULL
        ),
        binned AS (
          SELECT ROUND(lat*{factor})/{factor} AS lat_bin,
                 ROUND(lon*{factor})/{factor} AS lon_bin,
                 hashtag, COUNT(*) AS n
          FROM pts
          GROUP BY 1,2,3
        )
        SELECT lat_bin, lon_bin, hashtag, n
        FROM binned
        WHERE n >= ?
    """
    return con.execute(q, [start, end, min_n]).df()

#Cache the hashtags that often occur together in high frequencies
@st.cache_data(show_spinner=False)
def cooccurrence(min_pair_n=20, start=None, end=None, tag_filter=None):
    con = get_connection()
    params = []
    where = []
    if start is not None and end is not None:
        where.append("a.created BETWEEN ? AND ?")
        params += [start, end]
    if tag_filter:
        where.append("(a.hashtag = ? OR b.hashtag = ?)")
        params += [tag_filter, tag_filter]
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    q = f"""
        SELECT a.hashtag AS h1, b.hashtag AS h2, COUNT(*) AS n
        FROM changeset_hashtags a
        JOIN changeset_hashtags b
          ON a.changeset_id = b.changeset_id
         AND a.hashtag < b.hashtag
        {where_sql}
        GROUP BY 1,2
        HAVING n >= ?
        ORDER BY n DESC
        LIMIT 2000
    """
    return con.execute(q, params + [min_pair_n]).df()

#Cache the usernames of the users
@st.cache_data(show_spinner=False)
def list_users():
    con = get_connection()
    return con.execute("""
        SELECT uid, latest_username
        FROM users
        ORDER BY COALESCE(latest_username, CAST(uid AS VARCHAR))
        LIMIT 20000
    """).df()

#Cache the user behaviour between selected dates
@st.cache_data(show_spinner=False)
def user_summary(uid, start, end):
    con = get_connection()
    #Basic activity and span within selected date window
    summary = con.execute("""
        SELECT
          u.uid,
          u.latest_username AS username,
          u.first_seen,
          u.last_seen,
          u.changesets_count,
          u.hashtags_rows,
          u.distinct_hashtags,
          -- windowed stats
          (SELECT COUNT(*) FROM changesets c
             WHERE c.uid = u.uid AND c.created BETWEEN ? AND ?) AS changesets_in_window,
          (SELECT COUNT(*) FROM changeset_hashtags h
             WHERE h.uid = u.uid AND h.created BETWEEN ? AND ?) AS hashtag_rows_in_window
        FROM users u
        WHERE u.uid = ?
    """, [start, end, start, end, uid]).df()

    #Top hashtags for this user in window
    top_ht = con.execute("""
        SELECT hashtag, COUNT(*) AS n,
               MIN(created) AS first_seen, MAX(created) AS last_seen
        FROM changeset_hashtags
        WHERE uid = ? AND created BETWEEN ? AND ?
        GROUP BY hashtag
        ORDER BY n DESC
        LIMIT 50
    """, [uid, start, end]).df()

    #Monthly trend for this user
    trend = con.execute("""
        SELECT strftime(created, '%Y-%m') AS month, COUNT(*) AS n
        FROM changesets
        WHERE uid = ? AND created BETWEEN ? AND ?
        GROUP BY month
        ORDER BY month
    """, [uid, start, end]).df()

    return summary, top_ht, trend

#Cache users spatial points bewteen selected date window
@st.cache_data(show_spinner=False)
def user_points_in_window(uid, start, end):
    con = get_connection()
    return con.execute("""
        SELECT created, lat, lon
        FROM user_points
        WHERE uid = ? AND created BETWEEN ? AND ?
    """, [uid, start, end]).df()

#Cache the top user contributors by hashtags
@st.cache_data(show_spinner=False)
def top_contributors(start, end):
    con = get_connection()
    return con.execute("""
        SELECT
          u.uid,
          u.latest_username AS username,
          COUNT(c.changeset_id) AS changesets_count,
          COUNT(DISTINCT h.hashtag) AS distinct_hashtags,
          COUNT(h.hashtag) AS hashtags_rows
        FROM users u
        JOIN changesets c ON u.uid = c.uid
        LEFT JOIN changeset_hashtags h
          ON c.changeset_id = h.changeset_id
        WHERE c.created BETWEEN ? AND ?
        GROUP BY u.uid, username
        ORDER BY changesets_count DESC
        LIMIT 10
    """, [start, end]).df()

#Get the Gini index from the hashtag counts
def gini_from_counts(counts: np.ndarray) -> float:
    counts = counts.astype(float)
    if counts.size == 0:
        return np.nan
    counts.sort()
    n = counts.size
    return (np.sum((2*np.arange(1, n+1)-n-1)*counts) / (n*np.sum(counts)))

#Get entroyp from the hashtag counts
def entropy_from_counts(counts: np.ndarray) -> float:
    p = counts / counts.sum()
    p = p[p > 0]
    return float(-(p*np.log2(p)).sum()) if p.size else 0.0

# ---------------- UI ----------------
st.title("OSM Hashtag Explorer")

# Sidebar filters
min_date, max_date = get_date_bounds()
start, end = st.sidebar.date_input(
    "Date range",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(), max_value=max_date.date()
)
start = pd.to_datetime(start)
end   = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

hashtags = get_hashtags(limit=5000)
selected_tag = st.sidebar.selectbox("Hashtag", hashtags)
st.sidebar.caption("Tip: type to search")

#Page tabs
tab_overview, tab_spatial, tab_lang, tab_ineq, tab_sim, tab_user = st.tabs(
    ["Overview", "Spatial", "Language", "Inequality", "Similarity", "User"]
)

# ---------- OVERVIEW ----------
with tab_overview:
    st.subheader(f"#{selected_tag} overview")

    points = get_points_for_tag(selected_tag, start, end)
    st.write(f"Edits with #{selected_tag}: {len(points):,}")

    if not points.empty:
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
        HeatMap(points[['lat','lon']].values.tolist(), radius=6, blur=10).add_to(m)
        st_folium(m, width=800, height=520)

    trend = get_monthly_trend(selected_tag, start, end)
    if not trend.empty:
        trend["month"] = pd.to_datetime(trend["month"] + "-01")
        st.line_chart(trend.set_index("month"))

    users = get_top_users_for_tag(selected_tag, start, end, limit=20)
    st.markdown("**Top users**")
    st.dataframe(users)

    st.subheader("Top 10 Contributors")
    tc_df = top_contributors(start, end)
    st.dataframe(tc_df)

    st.markdown("**Notes:**")
    st.caption(
        "- `changesets_count` = number of changesets in selected period\n"
        "- `distinct_hashtags` = number of unique hashtags used\n"
        "- `hashtags_rows` = total number of hashtag entries (including repeats)"
    )

# ---------- SPATIAL ----------
with tab_spatial:
    st.subheader("Spatial disparities")
    grid_size = st.selectbox("Grid size (degrees)", [1.0, 0.5, 0.25], index=1)
    min_bin_n = st.slider("Minimum counts per cell", 1, 100, 5)

    grid = grid_counts(start, end, grid=grid_size, min_n=min_bin_n)
    if grid.empty:
        st.info("No binned data in this range.")
    else:
        # diversity per cell (Shannon entropy) + total counts
        agg = (grid.groupby(["lat_bin","lon_bin"])
                    .agg(total=("n","sum"),
                         entropy=("n", lambda x: entropy_from_counts(x.values)))
                    .reset_index())

        # HeatMap by total counts
        m = folium.Map(location=[20,0], zoom_start=2)
        HeatMap(agg[['lat_bin','lon_bin','total']].values.tolist(),
                radius=10, blur=12, max_zoom=6).add_to(m)
        st.markdown("**Counts by grid cell**")
        st_folium(m, width=800, height=520)

        st.markdown("**Top cells by diversity (entropy)**")
        st.dataframe(agg.sort_values("entropy", ascending=False).head(25))

# ---------- LANGUAGE ----------
with tab_lang:
    st.subheader("Language disparities")
    if not HAVE_LANG:
        st.warning("Language detection not installed. Run: `pip install langdetect`")
    else:
        con = get_connection()
        # Get frequent hashtags across the date range (to improve detection stability)
        tags_df = con.execute("""
            SELECT hashtag, COUNT(*) AS n
            FROM changeset_hashtags
            WHERE created BETWEEN ? AND ?
            GROUP BY 1
            HAVING n >= 10
            ORDER BY n DESC
            LIMIT 5000
        """, [start, end]).df()

        def detect_lang_safe(tag):
            try:
                return detect(tag)
            except Exception:
                return "unknown"

        if not tags_df.empty:
            tags_df["lang"] = tags_df["hashtag"].map(detect_lang_safe)
            lang_counts = (tags_df.groupby("lang")["n"].sum()
                                      .sort_values(ascending=False)
                                      .reset_index(name="count"))
            st.dataframe(lang_counts.head(25))
            st.caption("Weighted by hashtag frequency in the selected date range.")

# ---------- INEQUALITY ----------
with tab_ineq:
    st.subheader("Hashtag inequality")
    con = get_connection()

    # Global hashtag distribution in range
    ht = con.execute("""
        SELECT hashtag, COUNT(*) AS n
        FROM changeset_hashtags
        WHERE created BETWEEN ? AND ?
        GROUP BY 1
    """, [start, end]).df()
    if not ht.empty:
        g_global = gini_from_counts(ht["n"].to_numpy())
        st.write(f"**Global hashtag Gini (usage concentration):** {g_global:.3f}")

    # Inequality among users for selected tag
    users = get_top_users_for_tag(selected_tag, start, end, limit=10_000)
    if not users.empty:
        g_users = gini_from_counts(users["n"].to_numpy())
        st.write(f"**User contribution Gini for #{selected_tag}:** {g_users:.3f}")
        st.bar_chart(users.set_index("user")["n"].head(30))
        st.caption("Top 30 users by count for the selected hashtag.")

# ---------- SIMILARITY ----------
with tab_sim:
    st.subheader("Hashtag similarity (co-occurrence)")
    min_pair = st.slider("Min co-occurrence threshold", 5, 200, 20)
    only_with = st.text_input("Only pairs involving this hashtag (optional)", value="")

    co = cooccurrence(min_pair_n=min_pair, start=start, end=end,
                      tag_filter=only_with.strip() or None)
    if co.empty:
        st.info("No co-occurring pairs at this threshold.")
    else:
        st.dataframe(co.head(200))
        st.caption("Pairs of hashtags that appear in the same changeset. Higher n → stronger association.")

#------------ CONTENT OF THE USER TAB ---------------
with tab_user:
    st.subheader("User explorer")

    users_df = list_users()
    if users_df.empty:
        st.info("No users found. Did you run the user table build script?")
    else:
        # Search by name or uid
        q = st.text_input("Search username or UID", "")
        if q.strip():
            qlow = q.strip().lower()
            mask = (
                users_df["latest_username"].fillna("").str.lower().str.contains(qlow, na=False)
                | users_df["uid"].astype(str).str.contains(qlow, na=False)
            )
            filtered = users_df[mask]
        else:
            filtered = users_df

        if filtered.empty:
            st.warning("No matches. Showing a small sample:")
            filtered = users_df.head(100)

        # Build options as tuples in (uid, username)
        options = list(filtered[["uid", "latest_username"]].itertuples(index=False, name=None))

        choice = st.selectbox(
            "Select a user",
            options,
            format_func=lambda o: f"{(o[1] or '(no name)')}".strip() + f" — {o[0]}",
            index=0 if options else None
        )

        if options:
            sel_uid = choice[0]  
            summary, top_ht, utrend = user_summary(sel_uid, start, end)
            if summary.empty:
                st.info("No data for this user in the selected date range.")
            else:
                s = summary.iloc[0]
                col1, col2, col3 = st.columns(3)
                col1.metric("Username", s.get("username") or "(none)")
                col2.metric("UID", sel_uid)
                col3.metric("All-time changesets", int(s["changesets_count"]))
                col1.metric("All-time distinct hashtags", int(s["distinct_hashtags"]))
                col2.metric("Changesets (in range)", int(s["changesets_in_window"]))
                col3.metric("Hashtag rows (in range)", int(s["hashtag_rows_in_window"]))
                st.caption(
                    f"First seen: {pd.to_datetime(s['first_seen'])} • "
                    f"Last seen: {pd.to_datetime(s['last_seen'])}"
                )

                #Map of their activity in the selected window
                pts = user_points_in_window(sel_uid, start, end)
                if not pts.empty:
                    m = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
                    HeatMap(pts[['lat', 'lon']].values.tolist(), radius=6, blur=10).add_to(m)
                    st.markdown("**Edits heatmap (selected date range)**")
                    st_folium(m, width=800, height=520)
                else:
                    st.info("No geolocated edits in this date range.")

                #Monthly trend
                if not utrend.empty:
                    utrend["month"] = pd.to_datetime(utrend["month"] + "-01")
                    st.markdown("**Monthly edits**")
                    st.line_chart(utrend.set_index("month"))

                #Top hashtags for this user
                st.markdown("**Top hashtags**")
                st.dataframe(top_ht)
