# ------------------------------------------------------------
# Here are some usage examples:
# ------------------------------------------------------------

# 1) Users who used a given hashtag (or list of hashtags)
# from queries import get_users_for_hashtag
# df = get_users_for_hashtag(
#     hashtag=["#mapcork", "#missingmaps"],
#     start_date="2022-01-01",
#     end_date="2022-12-31",
#     order_by="n DESC",
#     limit=50,
#     to_csv="users_for_hashtag_2022.csv"
# )
# print(df.head())

# 2) Hashtags used by specific users (by username and/or UID)
# from queries import get_hashtags_for_users
# df = get_hashtags_for_users(
#     usernames=["alice123", "bob_mapper"],
#     uids=[12345],
#     start_date="2023-01-01",
#     end_date="2023-06-30",
#     order_by="n DESC",
#     limit=100
# )
# print(df.head())

# 3) List all users (materialized stats in `users` table)
# from queries import get_all_users
# df = get_all_users(order_by="changesets_count DESC", limit=100)
# print(df.head())

# 4) Global hashtag counts (optionally filtered by date & bbox)
# from queries import get_all_hashtags
# df = get_all_hashtags(
#     start_date="2021-01-01",
#     end_date="2021-12-31",
#     order_by="n DESC",
#     limit=200
# )
# print(df.head())

# 5) Hashtags between two dates (alias for #4 with only dates)
# from queries import get_hashtags_between_dates
# df = get_hashtags_between_dates(
#     "2020-01-01", "2020-12-31",
#     order_by="n DESC", limit=50
# )
# print(df.head())

# 6) Users active inside a geographic bbox (using user_points)
# from queries import get_users_in_bbox
# bbox = (51.2, -0.5, 51.8, 0.3)  # (min_lat, min_lon, max_lat, max_lon)
# df = get_users_in_bbox(
#     bbox=bbox,
#     start_date="2024-01-01",
#     end_date="2024-03-31",
#     order_by="changesets_in_bbox DESC",
#     limit=25
# )
# print(df.head())

# 7) Hashtags used inside a bbox (global top tags in region)
# from queries import get_hashtags_in_bbox
# bbox = (40.4, -74.2, 41.0, -73.6)  # NYC-ish
# df = get_hashtags_in_bbox(
#     bbox=bbox,
#     start_date="2023-01-01",
#     end_date="2023-12-31",
#     order_by="n DESC",
#     limit=50
# )
# print(df.head())

# 8) Hashtags used by specific users inside a bbox
# from queries import get_hashtags_for_users_in_bbox
# bbox = (48.7, 2.1, 49.1, 2.6)  # Paris-ish
# df = get_hashtags_for_users_in_bbox(
#     usernames=["paris_mapper"],
#     uids=None,
#     bbox=bbox,
#     start_date="2022-01-01",
#     end_date="2022-12-31",
#     order_by="n DESC",
#     limit=30
# )
# print(df.head())

# 9) Users for a given hashtag restricted to a bbox
# from queries import get_users_for_hashtag_in_bbox
# bbox = (34.0, -118.7, 34.4, -118.1)  # LA-ish
# df = get_users_for_hashtag_in_bbox(
#     hashtag="#missingmaps",
#     bbox=bbox,
#     start_date="2021-06-01",
#     end_date="2021-12-31",
#     order_by="n DESC",
#     limit=50
# )
# print(df.head())

# 10) All point centroids (user_points) for specific users
# from queries import get_user_points
# df = get_user_points(
#     usernames=["alice123"],
#     uids=[12345],
#     start_date="2023-05-01",
#     end_date="2023-06-01",
#     to_csv="alice_points_may_june_2023.csv"
# )
# print(df.head())

# 11) All point centroids for a hashtag or list of hashtags
# from queries import get_hashtag_points
# df = get_hashtag_points(
#     hashtag=["#mapcork", "#roads"],
#     start_date="2020-01-01",
#     end_date="2020-12-31"
# )
# print(df.head())

# 12) Count one or more hashtags (optional date range)
# from queries import count_hashtag
# df = count_hashtag(
#     hashtag=["#mapcork", "#buildings"],
#     start_date="2019-01-01",
#     end_date="2024-12-31"
# )
# print(df)

# 13) Count changesets per user (by uid and/or username)
# from queries import count_user_changes
# df = count_user_changes(
#     uids=[98765, 12345],
#     usernames=["alice123"],
#     start_date="2022-01-01",
#     end_date="2022-12-31"
# )
# print(df)
#